"""RAGAS-style retrieval metrics, computed lexically and without a judge model.

The real RAGAS library scores most of its metrics by asking an LLM. That is the
right tool in a lab and the wrong one in a regression suite a class runs forty
times a day: it needs a key, it costs money, it is slow, and — the part that
matters for testing — **it is not deterministic**, so a failing score cannot be
reproduced and a passing one proves less than it looks like it does.

These are lexical proxies with the same names and the same directions. They are
honest about what they are:

  * they agree with the LLM-judged versions on obvious cases (a fabricated
    answer scores low on faithfulness; an off-topic answer scores low on answer
    relevancy)
  * they disagree on paraphrase — an answer that is correct in different words
    scores lower here than a judge would give it

That disagreement is deliberately left in rather than tuned away. Finding a case
where the metric is wrong, and being able to say *why*, is the point of the
RAGAS lab: a metric you cannot explain is a number you cannot defend in a
release meeting.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9][a-z0-9.%-]*")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were", "be",
    "for", "on", "with", "as", "by", "that", "this", "it", "its", "at", "from", "but",
    "not", "can", "will", "would", "should", "may", "if", "than", "then", "there",
    "these", "those", "which", "when", "what", "how", "why", "who", "you", "your",
}
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


def _set(text: str) -> set[str]:
    return set(_tokens(text))


def _overlap(a: str, b: str) -> float:
    """Fraction of a's content words that appear in b."""
    ta = _set(a)
    if not ta:
        return 1.0
    return len(ta & _set(b)) / len(ta)


def _cosine(a: str, b: str) -> float:
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ca or not cb:
        return 0.0
    shared = set(ca) & set(cb)
    num = sum(ca[t] * cb[t] for t in shared)
    den = math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values()))
    return num / den if den else 0.0


# ---------------------------------------------------------------------------
# Generation metrics
# ---------------------------------------------------------------------------
def faithfulness(answer: str, contexts: list[str]) -> float:
    """Share of the answer's claims that the retrieved context supports.

    A claim here is a sentence; support is measured by content-word overlap with
    the joined context. Disclaimers and refusals are excluded — they are the
    system speaking about itself, not claims about the world.
    """
    joined = "\n".join(contexts)
    sentences = [s.strip() for s in _SENTENCE.split(answer or "") if len(_tokens(s)) >= 4]
    claims = [s for s in sentences if not _is_meta(s)]
    if not claims:
        return 1.0
    supported = sum(1 for s in claims if _overlap(s, joined) >= 0.6)
    return supported / len(claims)


def _is_meta(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in (
        "not investment advice", "educational", "consult a", "registered investment adviser",
        "i could not find", "i cannot", "i am not going to", "verify against",
    ))


def answer_relevancy(answer: str, question: str) -> float:
    """How much of the question's substance the answer actually engages with."""
    if not (answer or "").strip():
        return 0.0
    return max(_overlap(question, answer), _cosine(question, answer))


def answer_correctness(answer: str, ground_truth: str) -> float:
    """F1 over content words against a reference answer."""
    ta, tb = _set(answer), _set(ground_truth)
    if not ta or not tb:
        return 0.0
    shared = len(ta & tb)
    if not shared:
        return 0.0
    precision, recall = shared / len(ta), shared / len(tb)
    return 2 * precision * recall / (precision + recall)


def answer_semantic_similarity(answer: str, ground_truth: str) -> float:
    """Cosine over term frequencies — the bag-of-words stand-in for an embedding."""
    return _cosine(answer, ground_truth)


def coherence(answer: str) -> float:
    """Do consecutive sentences share vocabulary, and is the answer structured?

    Crude by design: it catches the genuinely incoherent output a broken prompt
    produces (disconnected fragments, repeated boilerplate), not subtle rhetoric.
    """
    sentences = [s for s in _SENTENCE.split(answer or "") if len(_tokens(s)) >= 3]
    if len(sentences) < 2:
        return 1.0 if sentences else 0.0
    links = [_cosine(sentences[i], sentences[i + 1]) for i in range(len(sentences) - 1)]
    connected = sum(1 for link in links if link > 0.05) / len(links)
    repeated = 1.0 - (len({s.strip().lower() for s in sentences}) / len(sentences))
    return max(0.0, connected - repeated)


def conciseness(answer: str, contexts: list[str]) -> float:
    """1.0 for an answer near the length of the evidence it needed, falling as it pads."""
    words = len(_tokens(answer))
    if words == 0:
        return 0.0
    context_words = max(1, sum(len(_tokens(c)) for c in contexts))
    ratio = words / context_words
    if ratio <= 0.5:
        return 1.0
    return max(0.0, 1.0 - (ratio - 0.5))


def harmfulness(answer: str) -> float:
    """0.0 is clean. Rises when the answer carries the language compliance forbids."""
    lowered = (answer or "").lower()
    markers = (
        "guaranteed return", "guaranteed profit", "risk-free", "risk free",
        "you should buy", "you should sell", "will definitely", "sure shot",
        "cannot lose", "assured returns",
    )
    hits = sum(1 for m in markers if m in lowered)
    return min(1.0, hits / 2.0)


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------
def context_precision(contexts: list[str], ground_truth: str) -> float:
    """Share of retrieved passages that are actually relevant, rank-weighted."""
    if not contexts:
        return 0.0
    relevant = [1 if _overlap(ground_truth, c) >= 0.25 else 0 for c in contexts]
    if not any(relevant):
        return 0.0
    running, hits = 0.0, 0
    for i, rel in enumerate(relevant, start=1):
        if rel:
            hits += 1
            running += hits / i
    return running / sum(relevant)


def context_recall(contexts: list[str], ground_truth: str) -> float:
    """Share of the reference answer's content that the retrieved passages cover."""
    return _overlap(ground_truth, "\n".join(contexts))


def context_entity_recall(contexts: list[str], entities: list[str]) -> float:
    """Share of the named entities the answer needs that made it into the context."""
    if not entities:
        return 1.0
    joined = "\n".join(contexts).lower()
    return sum(1 for e in entities if e.lower() in joined) / len(entities)


def context_relevancy(contexts: list[str], question: str) -> float:
    """Mean question overlap across retrieved passages — the noise check."""
    if not contexts:
        return 0.0
    return sum(_overlap(question, c) for c in contexts) / len(contexts)


def noise_sensitivity(clean_answer: str, noisy_answer: str) -> float:
    """0.0 when irrelevant padding in the question changed nothing about the answer."""
    return 1.0 - _cosine(clean_answer, noisy_answer)


METRIC_DIRECTION = {
    "Faithfulness": "higher",
    "Answer Relevancy": "higher",
    "Context Precision": "higher",
    "Context Recall": "higher",
    "Context Entity Recall": "higher",
    "Answer Semantic Similarity": "higher",
    "Answer Correctness": "higher",
    "Harmfulness": "lower",
    "Coherence": "higher",
    "Conciseness": "higher",
    "Noise Sensitivity": "lower",
    "Context Relevancy": "higher",
}
