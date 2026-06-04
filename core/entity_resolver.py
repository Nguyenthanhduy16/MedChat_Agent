"""Dynamic Entity Resolver."""

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import logging
from pathlib import Path
import re

from core.models import ResolvedEntity
from core.text import accent_fold, normalize_text

logger = logging.getLogger(__name__)


ENTITY_CATEGORIES = ("drugs", "products", "drug_classes", "conditions", "symptoms")
FUZZY_MATCH_THRESHOLD = 0.82
MIN_SCAN_ALIAS_LENGTH = 6
GENERIC_ALIAS_TOKENS = {
    "benh",
    "bo",
    "chai",
    "dich",
    "dieu",
    "dung",
    "hop",
    "mat",
    "nho",
    "thuoc",
    "tri",
    "vien",
}
PRODUCT_NAME_STOP_MARKERS = (
    " dieu tri ",
    " ho tro ",
    " bo sung ",
    " giup ",
    " phong ",
    " giam ",
    " sat trung ",
    " lam diu ",
    " diu ",
    " tang ",
    " cai thien ",
    " ngan ngua ",
)


@dataclass(frozen=True)
class EntityAliasEntry:
    type: str
    canonical: str
    aliases: tuple[str, ...]


class EntityAliasIndex:
    def __init__(self, entries: list[EntityAliasEntry]) -> None:
        self.entries = entries
        self._lookup: dict[str, EntityAliasEntry] = {}
        for entry in entries:
            for value in (entry.canonical, *entry.aliases):
                folded = accent_fold(value)
                if folded and folded not in self._lookup:
                    self._lookup[folded] = entry

    @classmethod
    def from_entries(cls, entries: list[tuple[str, str, list[str]]]) -> "EntityAliasIndex":
        return cls(
            [
                EntityAliasEntry(
                    type=entity_type,
                    canonical=accent_fold(canonical),
                    aliases=tuple(alias for alias in aliases if alias.strip()),
                )
                for entity_type, canonical, aliases in entries
            ]
        )

    @classmethod
    def from_chunks(cls, chunks) -> "EntityAliasIndex":
        entries: list[tuple[str, str, list[str]]] = []
        for chunk in chunks:
            entities = getattr(chunk, "entities", {}) or {}
            for category, entity_type in (
                ("drugs", "drug"),
                ("products", "product"),
                ("drug_classes", "drug_class"),
                ("conditions", "condition"),
                ("symptoms", "symptom"),
            ):
                for value in entities.get(category, []):
                    if isinstance(value, str) and value.strip():
                        entries.append((entity_type, value, []))
            metadata = getattr(chunk, "metadata", {}) or {}
            entries.extend(_metadata_entries(metadata))
        return cls.from_entries(entries)

    @classmethod
    def from_chunk_files(cls, root: Path) -> "EntityAliasIndex":
        entries: list[tuple[str, str, list[str]]] = []
        if not root.exists():
            return cls.from_entries(entries)

        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                metadata = item.get("metadata")
                if isinstance(metadata, dict):
                    entries.extend(_metadata_entries(metadata))
        return cls.from_entries(entries)

    def resolve(self, text: str, category: str) -> ResolvedEntity:
        normalized = normalize_text(text)
        folded = accent_fold(normalized)
        entry = self._lookup.get(folded)
        if entry is not None:
            return ResolvedEntity(
                text=normalized,
                canonical=entry.canonical,
                type=entry.type,
                confidence=0.95,
                source="corpus_exact" if folded == entry.canonical else "corpus_alias",
            )

        fuzzy_entry, ratio = self._best_fuzzy_match(folded)
        if fuzzy_entry is not None and ratio >= FUZZY_MATCH_THRESHOLD:
            return ResolvedEntity(
                text=normalized,
                canonical=fuzzy_entry.canonical,
                type=fuzzy_entry.type,
                confidence=0.65,
                source="corpus_fuzzy",
            )

        # Only drugs and products are required entities that should trigger web search.
        # Symptoms, conditions, drug_classes are contextual qualifiers — keep them low
        # so the Evidence Gate does not block on their absence.
        candidate_confidence = 0.85 if category in {"drugs", "products"} else 0.3
        return ResolvedEntity(
            text=normalized,
            canonical=folded,
            type=category,
            confidence=candidate_confidence,
            source="candidate",
        )

    def scan_message(self, message: str) -> list[ResolvedEntity]:
        folded_message = accent_fold(message)
        matches: list[ResolvedEntity] = []
        occupied_spans: list[tuple[int, int]] = []
        for alias in sorted(self._lookup, key=len, reverse=True):
            if not _is_scannable_alias(alias):
                continue
            pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
            for match in re.finditer(pattern, folded_message):
                span = match.span()
                if any(_spans_overlap(span, occupied) for occupied in occupied_spans):
                    continue
                entry = self._lookup[alias]
                matches.append(
                    ResolvedEntity(
                        text=alias,
                        canonical=entry.canonical,
                        type=entry.type,
                        confidence=0.95,
                        source="corpus_message",
                    )
                )
                occupied_spans.append(span)
                break
        return matches

    def _best_fuzzy_match(self, folded: str) -> tuple[EntityAliasEntry | None, float]:
        best_entry: EntityAliasEntry | None = None
        best_ratio = 0.0
        for key, entry in self._lookup.items():
            ratio = SequenceMatcher(None, folded, key).ratio()
            if ratio > best_ratio:
                best_entry = entry
                best_ratio = ratio
        return best_entry, best_ratio


@lru_cache
def default_alias_index() -> EntityAliasIndex:
    static_entries = [
        ("drug", "abacavir", ["ziagen"]),
        ("drug", "paracetamol", ["acetaminophen", "efferalgan", "hapacol"]),
        ("drug", "amoxicillin", ["amoxycillin"]),
        ("drug", "warfarin", []),
        ("drug", "ibuprofen", []),
        ("condition", "suy than", ["renal impairment", "kidney impairment"]),
        ("condition", "mang thai", ["pregnancy", "pregnant"]),
        ("condition", "cho con bu", ["lactation", "breastfeeding"]),
        ("condition", "hiv", []),
        ("drug_class", "thuoc chong tram cam", ["antidepressant", "antidepressants"]),
    ]
    corpus_index = EntityAliasIndex.from_chunk_files(Path("data/chunked"))
    return EntityAliasIndex.from_entries(
        static_entries
        + [
            (entry.type, entry.canonical, list(entry.aliases))
            for entry in corpus_index.entries
        ]
    )


async def resolve_entities(
    raw_entities: dict[str, list[str]],
    message: str | None = None,
    alias_index: EntityAliasIndex | None = None,
) -> list[ResolvedEntity]:
    index = alias_index or default_alias_index()
    resolved: list[ResolvedEntity] = []

    if message:
        resolved.extend(index.scan_message(message))

    for qualifier in raw_entities.get("clinical_qualifiers", []):
        resolved.append(
            ResolvedEntity(
                text=normalize_text(qualifier),
                canonical=accent_fold(qualifier),
                type="clinical_qualifier",
                confidence=0.85,
                source="pattern",
            )
        )

    for category in ENTITY_CATEGORIES:
        for entity in raw_entities.get(category, []):
            resolved.append(index.resolve(entity, category))

    return _dedupe_resolved(resolved)


def _metadata_entries(metadata: dict) -> list[tuple[str, str, list[str]]]:
    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        return []

    entity_type = _metadata_entity_type(metadata)
    aliases = _metadata_aliases(metadata, entity_type)
    canonical = _metadata_canonical_name(name, entity_type)
    return [(entity_type, canonical, aliases)]


def _metadata_entity_type(metadata: dict) -> str:
    context = accent_fold(
        " ".join(
            str(metadata.get(key, ""))
            for key in ("type", "category", "source_family", "source")
        )
    )
    if any(term in context for term in ("benh", "disease", "condition")):
        return "condition"
    if any(term in context for term in ("duoc chat", "ingredient", "active substance")):
        return "drug"
    return "product"


def _metadata_aliases(metadata: dict, entity_type: str) -> list[str]:
    aliases: list[str] = []
    name = metadata.get("name")
    if isinstance(name, str):
        aliases.extend(_name_aliases(name, entity_type))
    id_value = metadata.get("id")
    if isinstance(id_value, str):
        aliases.append(id_value.replace("-", " "))
    return _unique_aliases(aliases)


def _metadata_canonical_name(name: str, entity_type: str) -> str:
    if entity_type != "product":
        return name
    return _product_prefix(accent_fold(name))


def _name_aliases(name: str, entity_type: str) -> list[str]:
    folded = accent_fold(name)
    aliases = [folded]
    product_prefix = _product_prefix(folded)
    if product_prefix and product_prefix != folded:
        aliases.append(product_prefix)
    if entity_type == "product":
        aliases.extend(_brand_token_aliases(name))
    return aliases


def _product_prefix(folded_name: str) -> str:
    padded = f" {folded_name} "
    stop_positions = [
        padded.find(marker)
        for marker in PRODUCT_NAME_STOP_MARKERS
        if padded.find(marker) != -1
    ]
    if not stop_positions:
        return folded_name
    return padded[: min(stop_positions)].strip()


def _brand_token_aliases(name: str) -> list[str]:
    prefix = _original_product_prefix(name)
    aliases: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]*", prefix):
        folded = accent_fold(token)
        if _is_distinctive_token(folded) and any(char.isupper() for char in token):
            aliases.append(folded)
    return aliases


def _original_product_prefix(name: str) -> str:
    folded_name = accent_fold(name)
    folded_prefix = _product_prefix(folded_name)
    if folded_prefix == folded_name:
        return name

    prefix_word_count = len(folded_prefix.split())
    words = re.findall(r"\S+", name)
    return " ".join(words[:prefix_word_count])


def _is_distinctive_token(token: str) -> bool:
    return (
        len(token) >= MIN_SCAN_ALIAS_LENGTH
        and token not in GENERIC_ALIAS_TOKENS
        and not token.isdigit()
    )


def _is_scannable_alias(alias: str) -> bool:
    if len(alias) < MIN_SCAN_ALIAS_LENGTH:
        return False
    tokens = alias.split()
    if len(tokens) == 1:
        return _is_distinctive_token(tokens[0])
    return any(_is_distinctive_token(token) for token in tokens)


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _unique_aliases(aliases: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for alias in aliases:
        folded = accent_fold(alias)
        if folded and folded not in seen and _is_scannable_alias(folded):
            seen.add(folded)
            result.append(folded)
    return result


def _dedupe_resolved(entities: list[ResolvedEntity]) -> list[ResolvedEntity]:
    result: list[ResolvedEntity] = []
    seen: set[tuple[str, str]] = set()
    for entity in sorted(entities, key=lambda item: item.confidence, reverse=True):
        key = (entity.type, entity.canonical)
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return result
