from dataclasses import dataclass

from core.models import RetrievalPlan, RouterDecision
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


def plan_query_facets(decision: RouterDecision) -> QueryPlan:
    entities = _query_entities(decision)
    facets = [
        QueryFacet(
            intent=intent,
            query=_facet_query(intent, entities),
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


def _facet_query(intent: str, entities: list[str]) -> str:
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
        [accent_fold(e) for e in entities]
        + expansion
    ))
    return " ".join(parts).strip()
