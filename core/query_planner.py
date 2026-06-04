from dataclasses import dataclass

from core.models import NormalizedInput, RetrievalPlan, RouterDecision
from core.text import accent_fold


@dataclass(frozen=True)
class QueryFacet:
    intent: str
    query: str
    required_entities: list[str]
    preferred_fields: list[str]


@dataclass(frozen=True)
class QueryPlan:
    facets: list[QueryFacet]

    @property
    def combined_query(self) -> str:
        return " ".join(facet.query for facet in self.facets if facet.query).strip()


INTENT_FIELDS = {
    "interaction": ["interaction", "warning"],
    "contraindication": ["contraindication", "warning", "careful"],
    "dosage": ["dosage"],
    "pregnancy_lactation": ["pregnancy_lactation", "warning", "careful"],
    "symptom_triage": ["symptom_triage", "general_health", "overview", "describe", "symptoms"],
    "disease_context": ["disease_context", "overview", "describe", "careful", "warning"],
    "pediatric_elderly": ["pediatric_elderly", "dosage", "careful", "warning"],
    "indication": ["indication", "describe"],
    "drug_identity": [],
    "general_health": ["general_health", "overview", "describe"],
}

# Expansion terms giúp sparse vector bắt được medical synonyms mà corpus dùng.
# Dense vector đã semantic nên ít cần; sparse (BM25-style) benefit nhiều nhất.
# Ví dụ: user viết "Clcr" nhưng corpus ingest dùng "GFR" hoặc "creatinine clearance".
INTENT_EXPANSIONS: dict[str, list[str]] = {
    "dosage": [
        "lieu dung", "cach dung", "lieu luong",
        "dose", "dosing", "dose adjustment",
        "renal dose", "GFR", "creatinine clearance",
        "dieu chinh lieu",
    ],
    "contraindication": [
        "chong chi dinh", "than trong", "khong dung",
        "contraindication", "avoid", "prohibited",
        "canh bao", "warning",
    ],
    "interaction": [
        "tuong tac", "dung chung", "uong chung",
        "drug interaction", "combination", "co-administration",
    ],
    "pregnancy_lactation": [
        "mang thai", "cho con bu", "phu nu co thai",
        "pregnancy", "lactation", "breastfeeding",
        "thai ky", "an toan thai",
    ],
    "disease_context": [
        "benh", "tinh trang", "suy giam chuc nang",
        "than trong", "overview", "impairment",
    ],
    "pediatric_elderly": [
        "tre em", "nguoi gia", "tre nho",
        "pediatric", "elderly", "geriatric",
        "tre so sinh", "infant",
    ],
    "indication": [
        "cong dung", "chi dinh", "dung de lam gi",
        "indication", "use for", "prescribed for",
    ],
    "symptom_triage": [
        "trieu chung", "bieu hien", "nguyen nhan",
        "symptom", "cause", "diagnosis",
    ],
}


INTENT_PART_MARKERS: dict[str, tuple[str, ...]] = {
    "interaction": ("tuong tac", "dung chung", "uong chung", "ket hop", "phoi hop"),
    "contraindication": ("chong chi dinh", "khong nen", "khong dung", "co the dung", "ai khong nen"),
    "dosage": ("lieu", "lieu dung", "lieu luong", "dieu chinh", "cach dung", "uong nhu the nao", "dose"),
    "pregnancy_lactation": ("mang thai", "cho con bu", "thai", "breastfeeding", "pregnancy"),
    "disease_context": ("benh", "suy than", "suy gan", "clcr", "gfr", "tinh trang"),
    "symptom_triage": ("trieu chung", "bieu hien", "bi dau", "sung", "nguyen nhan"),
    "pediatric_elderly": ("tre em", "tre nho", "thang tuoi", "nguoi gia", "elderly", "pediatric"),
    "indication": ("dung de lam gi", "cong dung", "chi dinh", "dieu tri"),
    "drug_identity": ("thuoc gi", "hoat chat", "thong tin ve", "la gi"),
    "general_health": ("nen lam gi", "suc khoe", "phong ngua"),
}


def plan_query_facets(decision: RouterDecision, normalized: NormalizedInput | None = None) -> QueryPlan:
    facets = [
        QueryFacet(
            intent=intent,
            query=_facet_query(
                intent,
                _entities_for_facet(intent, decision, normalized),
                _question_parts_for_intent(intent, normalized),
            ),
            required_entities=_required_entities_for_intent(intent, decision),
            preferred_fields=INTENT_FIELDS.get(intent, []),
        )
        for intent in decision.intents
        if intent != "unsupported"
    ]
    return QueryPlan(facets=facets)


def retrieval_plan_for_facet(facet: QueryFacet, decision: RouterDecision) -> RetrievalPlan:
    metadata_filters = {
        "trust_tier": ["regulatory", "clinical_reference", "local_curated"],
    }
    if facet.preferred_fields:
        metadata_filters["field"] = list(dict.fromkeys(facet.preferred_fields))
    return RetrievalPlan(
        intents=[facet.intent],
        risk_level=decision.risk_level,
        queries=[facet.query],
        entities=decision.entities,
        metadata_filters=metadata_filters,
    )


def combined_retrieval_plan(query_plan: QueryPlan, decision: RouterDecision) -> RetrievalPlan:
    fields: list[str] = []
    for facet in query_plan.facets:
        fields.extend(facet.preferred_fields)
    metadata_filters = {
        "trust_tier": ["regulatory", "clinical_reference", "local_curated"],
    }
    if fields:
        metadata_filters["field"] = list(dict.fromkeys(fields))
    return RetrievalPlan(
        intents=decision.intents,
        risk_level=decision.risk_level,
        queries=[query_plan.combined_query],
        entities=decision.entities,
        metadata_filters=metadata_filters,
    )


def _query_entities(decision: RouterDecision) -> list[str]:
    entities = decision.entities
    return list(
        dict.fromkeys(
            entities.get("drugs", [])
            + entities.get("products", [])
            + entities.get("drug_classes", [])
            + entities.get("conditions", [])
            + entities.get("clinical_qualifiers", [])
            + entities.get("symptoms", [])
            + entities.get("body_parts", [])
        )
    )


def _required_entities_for_intent(intent: str, decision: RouterDecision) -> list[str]:
    entities = decision.entities
    medication_entities = (
        entities.get("drugs", [])
        + entities.get("products", [])
        + entities.get("drug_classes", [])
    )
    clinical_entities = entities.get("conditions", []) + entities.get("clinical_qualifiers", [])
    if intent in {"dosage", "interaction", "contraindication", "pregnancy_lactation"}:
        return list(dict.fromkeys(medication_entities + clinical_entities))
    if intent in {"disease_context", "symptom_triage", "pediatric_elderly"}:
        return list(dict.fromkeys(clinical_entities + entities.get("symptoms", []) + entities.get("body_parts", [])))
    return list(dict.fromkeys(medication_entities + clinical_entities))


def _question_parts_for_intent(intent: str, normalized: NormalizedInput | None) -> list[str]:
    if normalized is None:
        return []

    matched = [
        part
        for part in normalized.question_parts
        if _part_matches_intent(part, intent)
    ]
    if matched:
        return matched
    return normalized.question_parts


def _entities_for_facet(
    intent: str,
    decision: RouterDecision,
    normalized: NormalizedInput | None,
) -> list[str]:
    entities = decision.entities
    medications = list(
        dict.fromkeys(
            entities.get("drugs", [])
            + entities.get("products", [])
            + entities.get("drug_classes", [])
        )
    )
    contextual_medications = _contextual_medications(medications, normalized)
    clinical = entities.get("conditions", []) + entities.get("clinical_qualifiers", [])

    if intent == "interaction":
        return list(dict.fromkeys(medications))
    if intent in {"dosage", "contraindication", "pregnancy_lactation"}:
        return list(dict.fromkeys(contextual_medications + clinical))
    if intent in {"disease_context", "symptom_triage", "pediatric_elderly"}:
        return list(
            dict.fromkeys(
                contextual_medications
                + clinical
                + entities.get("symptoms", [])
                + entities.get("body_parts", [])
            )
        )
    return _query_entities(decision)


def _contextual_medications(medications: list[str], normalized: NormalizedInput | None) -> list[str]:
    if normalized is None:
        return medications

    result: list[str] = []
    for medication in medications:
        containing_parts = [
            part
            for part in normalized.question_parts
            if _contains_entity(part, medication)
        ]
        if containing_parts and all(_part_matches_intent(part, "interaction") for part in containing_parts):
            continue
        result.append(medication)
    return result or medications


def _part_matches_intent(part: str, intent: str) -> bool:
    folded = accent_fold(part)
    return any(marker in folded for marker in INTENT_PART_MARKERS.get(intent, ()))


def _contains_entity(part: str, entity: str) -> bool:
    folded_part = accent_fold(part)
    folded_entity = accent_fold(entity)
    return bool(folded_entity and folded_entity in folded_part)


def _facet_query(intent: str, entities: list[str], question_parts: list[str] | None = None) -> str:
    """Build query string for one retrieval facet.

    Strategy:
    - Dense vector: câu hỏi gốc đã được embed, semantic match OK.
    - Sparse vector (BM25): benefit lớn từ synonym expansion.
      Ví dụ: user viết "Clcr" → corpus có "creatinine clearance" hoặc "GFR".
      Nếu không expand → sparse miss → RRF score thấp → chunk đúng không vào pool.
    - Reranker sau đó xử lý precision, nhưng chỉ với những gì đã vào pool.
    """
    expansion = INTENT_EXPANSIONS.get(intent, [])
    parts = list(dict.fromkeys(
        [accent_fold(part) for part in (question_parts or [])]
        + [accent_fold(e) for e in entities]
        + expansion
    ))
    return " ".join(parts).strip()
