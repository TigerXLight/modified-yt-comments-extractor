"""Internal staged matcher/canonicalization layer for Profile/Media review.

The layer is intentionally stdlib-first.  It absorbs the useful project-safe
ideas from the local matcher reference repositories without vendoring their
source: exact matching, Aho-Corasick-style multi-pattern scans, fuzzy ranking,
token TF-IDF/cosine grouping, LCS, subsequence ranking, readable rule patterns,
model comparison, and optional wrappers for heavy local installs.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Protocol


@dataclass(frozen=True)
class MatchResult:
    choice: str
    score: float
    backend_name: str
    match_type: str
    explanation: str
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: dict[str, Any] | None = None


class MatcherBackend(Protocol):
    name: str

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        ...


def normalize_match_text(value: object) -> str:
    text = str(value or "").casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\b(?:rev(?:erend)?|revd|canon|father|pastor|dr|mr|mrs|ms|sir)\.?\b", " ", text)
    return " ".join(re.sub(r"[^a-z0-9']+", " ", text).split())


def _word_tokens(value: object) -> list[str]:
    return [token for token in normalize_match_text(value).split() if token]


def canonical_person_key(name: object) -> str:
    normalised = normalize_match_text(name)
    aliases = {
        "revd canon brett murphy": "brett murphy",
        "rev canon brett murphy": "brett murphy",
        "father brett murphy": "brett murphy",
        "pastor doug wilson": "doug wilson",
    }
    return aliases.get(normalised, normalised)


class ExactMatcher:
    name = "exact_normalized_substring"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        q = normalize_match_text(query)
        output: list[MatchResult] = []
        if not q:
            return output
        for choice in choices:
            c = normalize_match_text(choice)
            if not c:
                continue
            if q == c:
                output.append(MatchResult(choice, 100.0, self.name, "exact", "normalized exact match"))
            elif q in c or c in q:
                output.append(MatchResult(choice, 95.0, self.name, "substring", "normalized substring match"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class PhraseTriggerMatcher:
    name = "phrase_trigger_index"

    def __init__(self, triggers: Iterable[str] = ()) -> None:
        self.triggers = tuple(normalize_match_text(item) for item in triggers if normalize_match_text(item))

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        triggers = tuple(normalize_match_text(item) for item in (context or {}).get("triggers", ()) if normalize_match_text(item)) or self.triggers
        if not triggers:
            return []
        q = normalize_match_text(query)
        output: list[MatchResult] = []
        for choice in choices:
            c = normalize_match_text(choice)
            hits = [trigger for trigger in triggers if trigger in q and trigger in c]
            if hits:
                output.append(MatchResult(choice, 90.0 + min(9, len(hits)), self.name, "rule-based", f"shared trigger(s): {', '.join(hits[:3])}"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class AhoCorasickPatternMatcher:
    """Small trie-based multi-pattern trigger matcher.

    This is a clean-room, casefolded implementation for the review UI's modest
    phrase sets.  It mirrors the useful control-flow shape of Aho-Corasick
    references (build a trie, then scan once) without importing or copying them.
    """

    name = "aho_corasick_style_multipattern"

    def __init__(self, patterns: Iterable[str] = ()) -> None:
        self.patterns = tuple(dict.fromkeys(normalize_match_text(item) for item in patterns if normalize_match_text(item)))
        self._trie: dict[str, Any] = {}
        for pattern in self.patterns:
            node = self._trie
            for char in pattern:
                node = node.setdefault(char, {})
            node.setdefault("_emit", []).append(pattern)

    def _hits(self, text: str) -> list[tuple[str, int, int]]:
        normalised = normalize_match_text(text)
        output: list[tuple[str, int, int]] = []
        for start in range(len(normalised)):
            node = self._trie
            idx = start
            while idx < len(normalised) and normalised[idx] in node:
                node = node[normalised[idx]]
                idx += 1
                for pattern in node.get("_emit", ()):
                    output.append((pattern, start, idx))
        return output

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        patterns = tuple(dict.fromkeys(normalize_match_text(item) for item in (context or {}).get("patterns", ()) if normalize_match_text(item))) or self.patterns
        if patterns != self.patterns:
            return AhoCorasickPatternMatcher(patterns).match(query, choices, context=context)
        if not patterns:
            return []
        query_hits = self._hits(query)
        query_hit_names = {hit[0] for hit in query_hits}
        output: list[MatchResult] = []
        for choice in choices:
            choice_hits = self._hits(choice)
            shared = sorted(query_hit_names.intersection(hit[0] for hit in choice_hits))
            if shared:
                first = next((hit for hit in choice_hits if hit[0] in shared), None)
                output.append(MatchResult(
                    choice,
                    94.0 + min(5, len(shared)),
                    self.name,
                    "multipattern",
                    f"Aho-Corasick-style shared pattern(s): {', '.join(shared[:4])}",
                    first[1] if first else None,
                    first[2] if first else None,
                    {"patterns": shared},
                ))
        return sorted(output, key=lambda item: item.score, reverse=True)


def _lcs_length(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for ch_left in left:
        current = [0]
        for idx, ch_right in enumerate(right, start=1):
            current.append(previous[idx - 1] + 1 if ch_left == ch_right else max(previous[idx], current[-1]))
        previous = current
    return previous[-1]


class LcsMatcher:
    name = "lcs_alignment"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        q = normalize_match_text(query)
        output: list[MatchResult] = []
        for choice in choices:
            c = normalize_match_text(choice)
            if not q or not c:
                continue
            score = 200.0 * _lcs_length(q, c) / max(1, len(q) + len(c))
            if score >= float((context or {}).get("minimum_score", 72.0)):
                output.append(MatchResult(choice, score, self.name, "lcs", "longest-common-subsequence fallback"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class FuzzySubsequenceMatcher:
    name = "fuzzy_subsequence"

    def _score(self, query: str, choice: str) -> tuple[float, int | None, int | None]:
        q = normalize_match_text(query)
        c = normalize_match_text(choice)
        if not q or not c:
            return 0.0, None, None
        positions: list[int] = []
        cursor = 0
        for char in q:
            found = c.find(char, cursor)
            if found < 0:
                continue
            positions.append(found)
            cursor = found + 1
        if not positions:
            return 0.0, None, None
        coverage = len(positions) / max(1, len(q))
        span = positions[-1] - positions[0] + 1
        compactness = len(positions) / max(1, span)
        return (coverage * 72.0) + (compactness * 28.0), positions[0], positions[-1] + 1

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        minimum = float((context or {}).get("minimum_score", 70.0))
        output: list[MatchResult] = []
        for choice in choices:
            score, start, end = self._score(query, choice)
            if score >= minimum:
                output.append(MatchResult(choice, score, self.name, "subsequence", "ordered fuzzy subsequence with compactness reward", start, end))
        return sorted(output, key=lambda item: item.score, reverse=True)


def _char_ngrams(text: str, n: int = 3) -> Counter[str]:
    padded = f"  {normalize_match_text(text)}  "
    return Counter(padded[i : i + n] for i in range(max(0, len(padded) - n + 1)))


def cosine_similarity(left: object, right: object) -> float:
    a = _char_ngrams(str(left or ""))
    b = _char_ngrams(str(right or ""))
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / max(1e-9, norm_a * norm_b)


class CosineNgramMatcher:
    name = "char_ngram_cosine"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        minimum = float((context or {}).get("minimum_score", 0.72))
        output: list[MatchResult] = []
        for choice in choices:
            score = cosine_similarity(query, choice)
            if score >= minimum:
                output.append(MatchResult(choice, score * 100.0, self.name, "tfidf/cosine", "character n-gram cosine fallback"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class TokenTfidfCosineMatcher:
    name = "token_tfidf_cosine"

    def _vectors(self, values: list[str]) -> tuple[list[Counter[str]], dict[str, float]]:
        docs = [Counter(_word_tokens(value)) for value in values]
        document_count = len(docs)
        df: Counter[str] = Counter()
        for doc in docs:
            df.update(doc.keys())
        idf = {term: math.log((1 + document_count) / (1 + count)) + 1.0 for term, count in df.items()}
        return docs, idf

    def _weighted(self, doc: Counter[str], idf: dict[str, float]) -> dict[str, float]:
        total = max(1, sum(doc.values()))
        return {term: (count / total) * idf.get(term, 1.0) for term, count in doc.items()}

    @staticmethod
    def _cos(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(value * right.get(term, 0.0) for term, value in left.items())
        norm_left = math.sqrt(sum(value * value for value in left.values()))
        norm_right = math.sqrt(sum(value * value for value in right.values()))
        return dot / max(1e-9, norm_left * norm_right)

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        minimum = float((context or {}).get("minimum_score", 0.35))
        docs, idf = self._vectors([query, *choices])
        query_vector = self._weighted(docs[0], idf)
        output: list[MatchResult] = []
        for choice, doc in zip(choices, docs[1:]):
            score = self._cos(query_vector, self._weighted(doc, idf))
            if score >= minimum:
                output.append(MatchResult(choice, score * 100.0, self.name, "tfidf/cosine", "token TF-IDF cosine grouping score"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class RapidFuzzMatcher:
    name = "rapidfuzz_optional"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        try:
            from rapidfuzz import fuzz, process  # type: ignore
        except Exception:
            return []
        minimum = float((context or {}).get("minimum_score", 82.0))
        output: list[MatchResult] = []
        for choice, score, _index in process.extract(query, choices, scorer=fuzz.token_set_ratio, limit=None):
            if float(score) >= minimum:
                output.append(MatchResult(choice, float(score), self.name, "fuzzy", "RapidFuzz token_set_ratio"))
        return output


@dataclass(frozen=True)
class ReadableRulePattern:
    rule_id: str
    template: str
    role_hint: str = ""
    explanation: str = ""


class ReadableRulePatternMatcher:
    name = "readable_rule_patterns"

    _token_pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

    def __init__(self, rules: Iterable[ReadableRulePattern] = ()) -> None:
        self.rules = tuple(rules)

    @classmethod
    def _compile_template(cls, template: str) -> re.Pattern[str]:
        pieces: list[str] = []
        cursor = 0
        matches = list(cls._token_pattern.finditer(template))
        for index, match in enumerate(matches):
            pieces.append(re.escape(template[cursor:match.start()]))
            suffix = template[match.end():matches[index + 1].start()] if index + 1 < len(matches) else template[match.end():]
            quantifier = r".{1,220}" if not suffix else r".{1,220}?"
            pieces.append(r"(?P<" + match.group(1) + r">" + quantifier + r")")
            cursor = match.end()
        pieces.append(re.escape(template[cursor:]))
        pattern = "".join(pieces).replace(r"\ ", r"\s+")
        return re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        rules = tuple((context or {}).get("rules", ())) or self.rules
        normal_rules = tuple(rule if isinstance(rule, ReadableRulePattern) else ReadableRulePattern(str(rule), str(rule)) for rule in rules)
        output: list[MatchResult] = []
        for rule in normal_rules:
            regex = self._compile_template(rule.template)
            for choice in choices:
                found = regex.search(choice)
                if found:
                    output.append(MatchResult(
                        choice,
                        92.0,
                        self.name,
                        "readable-rule",
                        rule.explanation or f"readable rule matched: {rule.rule_id}",
                        found.start(),
                        found.end(),
                        {"rule_id": rule.rule_id, "captures": found.groupdict(), "role_hint": rule.role_hint},
                    ))
        return sorted(output, key=lambda item: item.score, reverse=True)


class SentenceTransformersMatcher:
    name = "sentence_transformers_optional"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        context = context or {}
        if not context.get("enable_semantic"):
            return []
        model = context.get("sentence_transformer_model")
        if model is None:
            return []
        try:
            vectors = model.encode([query, *choices])
        except Exception:
            return []
        minimum = float(context.get("minimum_score", 0.55))

        def cos_vec(left: Any, right: Any) -> float:
            pairs = list(zip(left, right))
            dot = sum(float(a) * float(b) for a, b in pairs)
            norm_a = math.sqrt(sum(float(a) * float(a) for a in left))
            norm_b = math.sqrt(sum(float(b) * float(b) for b in right))
            return dot / max(1e-9, norm_a * norm_b)

        output: list[MatchResult] = []
        query_vector = vectors[0]
        for choice, vector in zip(choices, vectors[1:]):
            score = cos_vec(query_vector, vector)
            if score >= minimum:
                output.append(MatchResult(choice, score * 100.0, self.name, "semantic", "caller-supplied sentence-transformers embedding cosine"))
        return sorted(output, key=lambda item: item.score, reverse=True)


class OptionalSpacyQuoteMatcher:
    name = "spacy_sayswho_optional_quote"

    def match(self, query: str, choices: list[str], *, context: dict[str, Any] | None = None) -> list[MatchResult]:
        context = context or {}
        if not context.get("enable_spacy_quote"):
            return []
        try:
            import spacy  # type: ignore  # noqa: F401
        except Exception:
            return []
        quote_re = re.compile(r"[\"'‘“](.{8,220}?)[\"'’”]\s*,?\s*(?:said|told|wrote|claimed|added)\s+([A-Z][A-Za-z .'-]{2,80})", re.IGNORECASE)
        output: list[MatchResult] = []
        for choice in choices:
            found = quote_re.search(choice)
            if found:
                output.append(MatchResult(choice, 88.0, self.name, "quote-attribution", "spaCy installed; regex attribution fallback used for review-safe quote span", found.start(), found.end(), {"speaker": found.group(2).strip(), "quote": found.group(1).strip()}))
        return output


class MatcherRegistry:
    def __init__(self) -> None:
        self._backends: list[tuple[int, str, MatcherBackend, bool]] = []

    def register(self, name: str, backend: MatcherBackend, *, priority: int = 100, enabled: bool = True) -> None:
        self._backends.append((priority, name, backend, enabled))
        self._backends.sort(key=lambda item: item[0])

    def match(self, query: str, choices: Iterable[str], *, policy: str = "default", context: dict[str, Any] | None = None) -> list[MatchResult]:
        choice_list = list(choices)
        merged_context = dict(context or {})
        merged_context.setdefault("policy", policy)
        results: list[MatchResult] = []
        seen: set[tuple[str, str]] = set()
        for _priority, _name, backend, enabled in self._backends:
            if not enabled:
                continue
            for result in backend.match(query, choice_list, context=merged_context):
                key = (result.choice, result.backend_name)
                if key not in seen:
                    seen.add(key)
                    results.append(result)
        return sorted(results, key=lambda item: item.score, reverse=True)

    def evaluate_models(self, query: str, choices: Iterable[str], *, context: dict[str, Any] | None = None) -> dict[str, list[MatchResult]]:
        choice_list = list(choices)
        output: dict[str, list[MatchResult]] = {}
        for _priority, name, backend, enabled in self._backends:
            if not enabled:
                continue
            matches = backend.match(query, choice_list, context=context or {})
            output[name] = matches[:5]
        return output


def default_matcher_registry() -> MatcherRegistry:
    registry = MatcherRegistry()
    registry.register(ExactMatcher.name, ExactMatcher(), priority=10)
    registry.register(AhoCorasickPatternMatcher.name, AhoCorasickPatternMatcher(), priority=15)
    registry.register(PhraseTriggerMatcher.name, PhraseTriggerMatcher(), priority=20)
    registry.register(RapidFuzzMatcher.name, RapidFuzzMatcher(), priority=30)
    registry.register(TokenTfidfCosineMatcher.name, TokenTfidfCosineMatcher(), priority=35)
    registry.register(CosineNgramMatcher.name, CosineNgramMatcher(), priority=40)
    registry.register(LcsMatcher.name, LcsMatcher(), priority=50)
    registry.register(FuzzySubsequenceMatcher.name, FuzzySubsequenceMatcher(), priority=60)
    registry.register(ReadableRulePatternMatcher.name, ReadableRulePatternMatcher(), priority=70)
    registry.register(SentenceTransformersMatcher.name, SentenceTransformersMatcher(), priority=80)
    registry.register(OptionalSpacyQuoteMatcher.name, OptionalSpacyQuoteMatcher(), priority=90)
    return registry


def compare_matcher_models(query: str, choices: Iterable[str], *, context: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """PolyFuzz-style comparison table for deterministic test/report use."""
    registry = default_matcher_registry()
    compared = registry.evaluate_models(query, choices, context=context or {})
    return {
        name: [
            {
                "choice": result.choice,
                "score": round(result.score, 3),
                "match_type": result.match_type,
                "explanation": result.explanation,
                "metadata": result.metadata or {},
            }
            for result in results
        ]
        for name, results in compared.items()
    }
