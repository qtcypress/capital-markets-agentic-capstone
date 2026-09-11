"""Chunking and a hybrid (BM25 + TF-IDF cosine) retrieval index.

Deliberately dependency-light: numpy only. A trainee can read every line of the
retrieval maths, which matters when they later have to explain *why* a
retrieval test failed rather than just that it did.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..config import KNOWLEDGE_BASE

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were", "be", "been",
    "for", "on", "with", "as", "by", "that", "this", "it", "its", "at", "from", "but", "not",
    "can", "will", "would", "should", "may", "if", "than", "then", "there", "these", "those",
    "which", "when", "what", "how", "why", "who", "whom", "into", "about", "over", "under",
}

# Domain synonym expansion — capital-market vocabulary is full of aliases and a
# retriever that does not know them fails on perfectly reasonable questions.
SYNONYMS: dict[str, list[str]] = {
    "ce": ["call", "option"],
    "pe": ["put", "option"],
    "fno": ["futures", "options", "derivatives"],
    "f&o": ["futures", "options", "derivatives"],
    "oi": ["open", "interest"],
    "pcr": ["put", "call", "ratio"],
    "iv": ["implied", "volatility"],
    "ltp": ["last", "traded", "price"],
    "atm": ["at", "the", "money", "strike"],
    "otm": ["out", "of", "the", "money"],
    "itm": ["in", "the", "money"],
    "mtm": ["mark", "to", "market"],
    "span": ["margin"],
    "stt": ["securities", "transaction", "tax"],
    "banknifty": ["bank", "nifty", "index"],
    "finnifty": ["financial", "services", "nifty", "index"],
    "lotsize": ["lot", "size", "contract"],
    "expiry": ["expiration", "settlement"],
    "premium": ["option", "price"],
    "writer": ["seller", "short"],
    "physical": ["delivery", "settlement"],
    "greeks": ["delta", "gamma", "theta", "vega", "rho"],
}


def tokenize(text: str, expand: bool = False) -> list[str]:
    tokens = [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS and len(t) > 1]
    if not expand:
        return tokens
    out = list(tokens)
    for t in tokens:
        out.extend(SYNONYMS.get(t, []))
    return out


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    section: str
    category: str
    authority: str
    text: str
    position: int
    word_count: int = 0
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def citation(self) -> str:
        return f"{self.doc_id}#{self.section}"


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    meta: dict[str, str] = {}
    for line in raw[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, raw[end + 4 :].lstrip("\n")


def chunk_document(path: Path) -> list[Chunk]:
    """Split a markdown doc on `##` headings; each section becomes one chunk."""
    return chunk_markdown(path.read_text(encoding="utf-8"), source=path.name, stem=path.stem)


def chunk_markdown(
    raw: str,
    *,
    source: str,
    stem: str,
    doc_id: str | None = None,
    category: str | None = None,
    authority: str | None = None,
    min_preamble_words: int = 25,
    min_section_words: int = 12,
) -> list[Chunk]:
    """Chunk markdown text that may have come from a file or from an upload.

    The curated corpus and a document a trainee adds at runtime go through
    exactly this function, so a retrieval failure on an uploaded document is the
    same class of failure as one on a shipped document — which is the point of
    letting them upload at all.
    """
    meta, body = _parse_frontmatter(raw)
    doc_id = doc_id or meta.get("doc_id") or stem.upper()
    title = meta.get("title") or stem.replace("-", " ").replace("_", " ").strip().title()
    category = category or meta.get("category", "general")
    authority = authority or meta.get("authority", "educational")

    parts = re.split(r"^##\s+(.+)$", body, flags=re.MULTILINE)
    chunks: list[Chunk] = []
    preamble = parts[0].strip()
    preamble = re.sub(r"^#\s+.*$", "", preamble, flags=re.MULTILINE).strip()
    if len(preamble.split()) > min_preamble_words:
        chunks.append(_mk_chunk(doc_id, source, title, "Overview", category, authority, preamble, 0))
    for i in range(1, len(parts), 2):
        section, text = parts[i].strip(), parts[i + 1].strip()
        if len(text.split()) < min_section_words:
            continue
        chunks.append(_mk_chunk(doc_id, source, title, section, category, authority, text, len(chunks)))
    return chunks


def _mk_chunk(doc_id, source, title, section, category, authority, text, position) -> Chunk:
    slug = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")[:48]
    return Chunk(
        chunk_id=f"{doc_id}--{position:02d}--{slug}",
        doc_id=doc_id,
        source=source,
        title=title,
        section=section,
        category=category,
        authority=authority,
        text=text,
        position=position,
        word_count=len(text.split()),
        checksum=hashlib.sha256(text.encode("utf-8")).hexdigest()[:12],
    )


class VectorStore:
    """Hybrid retriever: BM25 lexical score fused with TF-IDF cosine similarity.

    Fusion weight is configurable so trainees can run an A/B retrieval
    experiment as one of the lab exercises.
    """

    def __init__(self, chunks: list[Chunk], bm25_weight: float = 0.5, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.bm25_weight = bm25_weight
        self.k1, self.b = k1, b
        self._build()

    def _build(self) -> None:
        self.doc_tokens = [tokenize(f"{c.title} {c.section} {c.text}", expand=True) for c in self.chunks]
        self.doc_lens = np.array([len(t) or 1 for t in self.doc_tokens], dtype=float)
        self.avg_len = float(self.doc_lens.mean()) if len(self.doc_lens) else 1.0

        vocab: dict[str, int] = {}
        for toks in self.doc_tokens:
            for t in set(toks):
                vocab.setdefault(t, len(vocab))
        self.vocab = vocab
        n_docs, n_terms = len(self.chunks), len(vocab)

        self.tf = np.zeros((n_docs, n_terms), dtype=np.float32)
        for i, toks in enumerate(self.doc_tokens):
            for term, count in Counter(toks).items():
                self.tf[i, vocab[term]] = count

        df = (self.tf > 0).sum(axis=0)
        self.idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0).astype(np.float32)
        tfidf = np.log1p(self.tf) * self.idf
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.tfidf_unit = tfidf / norms

    # -- scoring -------------------------------------------------------
    def _bm25(self, q_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(len(self.chunks), dtype=np.float32)
        for term in q_tokens:
            j = self.vocab.get(term)
            if j is None:
                continue
            f = self.tf[:, j]
            denom = f + self.k1 * (1 - self.b + self.b * self.doc_lens / self.avg_len)
            scores += self.idf[j] * (f * (self.k1 + 1)) / np.where(denom == 0, 1, denom)
        return scores

    def _cosine(self, q_tokens: list[str]) -> np.ndarray:
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for term, count in Counter(q_tokens).items():
            j = self.vocab.get(term)
            if j is not None:
                vec[j] = math.log1p(count) * self.idf[j]
        n = np.linalg.norm(vec)
        if n == 0:
            return np.zeros(len(self.chunks), dtype=np.float32)
        return self.tfidf_unit @ (vec / n)

    @staticmethod
    def _normalise(a: np.ndarray) -> np.ndarray:
        if a.size == 0:
            return a
        hi = float(a.max())
        return a / hi if hi > 0 else a

    def search(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.0,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        q_tokens = tokenize(query, expand=True)
        if not q_tokens or not self.chunks:
            return []
        fused = (
            self.bm25_weight * self._normalise(self._bm25(q_tokens))
            + (1 - self.bm25_weight) * self._normalise(self._cosine(q_tokens))
        )
        order = np.argsort(-fused)
        results: list[dict[str, Any]] = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            score = float(fused[int(idx)])
            if score < min_score:
                break
            if category and chunk.category != category:
                continue
            results.append({"chunk": chunk, "score": round(score, 5), "rank": len(results) + 1})
            if len(results) >= top_k:
                break
        return results

    # -- introspection used by the test suite --------------------------
    def stats(self) -> dict[str, Any]:
        return {
            "chunks": len(self.chunks),
            "documents": len({c.doc_id for c in self.chunks}),
            "vocabulary": len(self.vocab),
            "avg_chunk_words": round(float(np.mean([c.word_count for c in self.chunks])), 1) if self.chunks else 0,
            "categories": sorted({c.category for c in self.chunks}),
            "bm25_weight": self.bm25_weight,
        }


_STORE: VectorStore | None = None


def load_chunks(directory: Path | None = None) -> list[Chunk]:
    directory = directory or KNOWLEDGE_BASE
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        chunks.extend(chunk_document(path))
    return chunks


def get_store(refresh: bool = False, directory: Path | None = None) -> VectorStore:
    global _STORE
    if _STORE is None or refresh:
        _STORE = VectorStore(load_chunks(directory))
    return _STORE
