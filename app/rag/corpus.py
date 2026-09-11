"""Documents a trainee adds to the RAG corpus at runtime.

Why this is not simply "write the file into knowledge_base/"
------------------------------------------------------------
One hosted URL serves a whole class. If an upload landed in the shared corpus,
the first trainee to add a poisoned document would be answering everybody
else's questions with it, and the shipped 206-case blue-team suite would start
failing for reasons nobody could reproduce locally. So an upload belongs to the
browser that made it:

  * the browser generates an opaque corpus id and sends it as X-QTCAP-Corpus
  * documents live in memory under that id, never on disk
  * a query without the header sees exactly the 15 curated documents

That is also the more honest teaching model. "Whose data is in the index?" is
the first question to ask about any multi-tenant RAG system, and here the
answer is enforced in code and asserted in the suite rather than promised in a
README.

What an upload is allowed to be
-------------------------------
Text. Markdown, plain text, CSV, JSON and HTML are accepted; a PDF or a DOCX is
refused with a message saying so rather than being silently indexed as binary
noise. Caps are per corpus and deliberately small — this is a training corpus,
not a document store.

Every uploaded document is scanned by the IN-07 document guard on the way in
and the findings are returned to the caller. Nothing is blocked: the red-team
labs need to load a poisoned document and watch what the pipeline does with it.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ..guardrails import check_document
from .store import Chunk, VectorStore, chunk_markdown, load_chunks

# Caps. Small on purpose: a class of forty browsers shares one free-tier
# container with 512MB of RAM.
MAX_DOCS_PER_CORPUS = 10
MAX_BYTES_PER_DOC = 200_000
MAX_BYTES_PER_CORPUS = 500_000
MAX_CHUNKS_PER_DOC = 60
MAX_CORPORA = 60
CORPUS_TTL_S = 6 * 3600

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".csv", ".tsv", ".json", ".html", ".htm", ".rst"}
BINARY_SUFFIXES = {
    ".pdf": "PDF", ".docx": "Word document", ".doc": "Word document",
    ".xlsx": "Excel workbook", ".xls": "Excel workbook", ".pptx": "PowerPoint deck",
    ".zip": "archive", ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
}


class DocumentError(ValueError):
    """A document was refused. The message is safe to show the caller."""


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(r"<[^>]+>")


def _suffix(filename: str) -> str:
    name = (filename or "").strip().lower()
    return name[name.rfind("."):] if "." in name else ""


def extract_text(filename: str, raw: str) -> str:
    """Turn an uploaded file into markdown-ish text the chunker understands."""
    suffix = _suffix(filename)

    if suffix in BINARY_SUFFIXES:
        raise DocumentError(
            f"{BINARY_SUFFIXES[suffix]} files are not supported. "
            "Save it as .md, .txt or .csv and upload that — the corpus is text."
        )
    if "\x00" in raw:
        raise DocumentError("That file looks binary, not text. Upload .md, .txt, .csv, .json or .html.")
    if suffix and suffix not in TEXT_SUFFIXES:
        raise DocumentError(
            f"'{suffix}' files are not supported. Accepted: "
            + ", ".join(sorted(TEXT_SUFFIXES))
        )

    if suffix in {".html", ".htm"}:
        body = _TAG_RE.sub(" ", raw)
        body = re.sub(r"<h([1-6])\b[^>]*>(.*?)</h\1>", r"\n\n## \2\n", body, flags=re.IGNORECASE | re.DOTALL)
        body = re.sub(r"</(p|div|li|tr|br)>", "\n", body, flags=re.IGNORECASE)
        body = _ANY_TAG_RE.sub(" ", body)
        return re.sub(r"\n{3,}", "\n\n", html.unescape(body))

    if suffix == ".json":
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"That is not valid JSON ({exc.msg} at line {exc.lineno}).") from exc
        return _json_to_markdown(parsed)

    if suffix in {".csv", ".tsv"}:
        return _table_to_markdown(raw, "\t" if suffix == ".tsv" else ",")

    return raw


def _json_to_markdown(value: Any, depth: int = 0) -> str:
    """Flatten JSON into headed sections so the heading chunker has something to cut on."""
    if depth > 4:
        return json.dumps(value)[:2000]
    if isinstance(value, dict):
        out = []
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                out.append(f"\n## {key}\n{_json_to_markdown(val, depth + 1)}")
            else:
                out.append(f"- **{key}**: {val}")
        return "\n".join(out)
    if isinstance(value, list):
        return "\n".join(
            _json_to_markdown(v, depth + 1) if isinstance(v, (dict, list)) else f"- {v}"
            for v in value[:200]
        )
    return str(value)


def _table_to_markdown(raw: str, delimiter: str) -> str:
    import csv as _csv
    from io import StringIO

    rows = list(_csv.reader(StringIO(raw), delimiter=delimiter))
    if not rows:
        raise DocumentError("That file has no rows.")
    header, body = rows[0], rows[1:]
    lines = [
        "## " + " / ".join(h.strip() for h in header if h.strip())[:80],
        "",
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    for row in body[:500]:
        cells = (row + [""] * len(header))[: len(header)]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    if len(body) > 500:
        lines.append(f"\n_{len(body) - 500} further rows were not indexed._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Documents and corpora
# ---------------------------------------------------------------------------
@dataclass
class UploadedDoc:
    doc_id: str
    filename: str
    title: str
    bytes: int
    words: int
    chunks: list[Chunk]
    findings: list[dict[str, Any]]
    checksum: str
    added_at: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "title": self.title,
            "bytes": self.bytes,
            "words": self.words,
            "chunks": len(self.chunks),
            "sections": [c.section for c in self.chunks],
            "checksum": self.checksum,
            "added_at": round(self.added_at, 3),
            "findings": self.findings,
            "flagged": bool(self.findings),
        }


@dataclass
class Corpus:
    corpus_id: str
    docs: dict[str, UploadedDoc] = field(default_factory=dict)
    revision: int = 0
    last_used: float = field(default_factory=time.time)

    @property
    def total_bytes(self) -> int:
        return sum(d.bytes for d in self.docs.values())


class CorpusRegistry:
    """In-memory, per-browser document overlays on top of the curated corpus."""

    def __init__(self):
        self._lock = threading.Lock()
        self._corpora: dict[str, Corpus] = {}
        self._base: list[Chunk] | None = None
        self._stores: dict[str, tuple[int, VectorStore]] = {}

    # -- base corpus ---------------------------------------------------
    def base_chunks(self) -> list[Chunk]:
        if self._base is None:
            self._base = load_chunks()
        return self._base

    # -- housekeeping --------------------------------------------------
    def _evict(self) -> None:
        now = time.time()
        stale = [cid for cid, c in self._corpora.items() if now - c.last_used > CORPUS_TTL_S]
        for cid in stale:
            self._corpora.pop(cid, None)
            self._stores.pop(cid, None)
        if len(self._corpora) > MAX_CORPORA:
            oldest = sorted(self._corpora.items(), key=lambda kv: kv[1].last_used)
            for cid, _ in oldest[: len(self._corpora) - MAX_CORPORA]:
                self._corpora.pop(cid, None)
                self._stores.pop(cid, None)

    @staticmethod
    def _clean_id(corpus_id: str | None) -> str | None:
        """Corpus ids come from a header, so they are untrusted input."""
        if not corpus_id:
            return None
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "", corpus_id)[:64]
        return cleaned or None

    # -- reads ---------------------------------------------------------
    def documents(self, corpus_id: str | None) -> list[dict[str, Any]]:
        cid = self._clean_id(corpus_id)
        with self._lock:
            corpus = self._corpora.get(cid) if cid else None
            if not corpus:
                return []
            corpus.last_used = time.time()
            return [d.summary() for d in sorted(corpus.docs.values(), key=lambda d: d.added_at)]

    def stats(self, corpus_id: str | None) -> dict[str, Any]:
        docs = self.documents(corpus_id)
        return {
            "documents": len(docs),
            "chunks": sum(d["chunks"] for d in docs),
            "bytes": sum(d["bytes"] for d in docs),
            "flagged": sum(1 for d in docs if d["flagged"]),
            "limits": {
                "max_documents": MAX_DOCS_PER_CORPUS,
                "max_bytes_per_document": MAX_BYTES_PER_DOC,
                "max_bytes_total": MAX_BYTES_PER_CORPUS,
            },
        }

    def store_for(self, corpus_id: str | None) -> VectorStore:
        """The retriever this caller should see: curated corpus plus their own docs."""
        cid = self._clean_id(corpus_id)
        with self._lock:
            corpus = self._corpora.get(cid) if cid else None
            if not corpus or not corpus.docs:
                from .store import get_store

                return get_store()
            corpus.last_used = time.time()
            cached = self._stores.get(cid)
            if cached and cached[0] == corpus.revision:
                return cached[1]
            extra: list[Chunk] = []
            for doc in sorted(corpus.docs.values(), key=lambda d: d.added_at):
                extra.extend(doc.chunks)
            store = VectorStore(self.base_chunks() + extra)
            self._stores[cid] = (corpus.revision, store)
            return store

    # -- writes --------------------------------------------------------
    def add(self, corpus_id: str | None, filename: str, content: str) -> dict[str, Any]:
        cid = self._clean_id(corpus_id)
        if not cid:
            raise DocumentError(
                "This request carried no corpus id, so there is nowhere private to put the "
                "document. Reload the console — it generates one per browser."
            )
        # The filename is displayed, put in a citation and used as the document
        # title. It is never used as a path — documents live in memory — but it
        # arrives from a browser, so it is reduced to a leaf name with no
        # traversal left in it before it goes anywhere near either.
        filename = (filename or "document.md").strip()[:120]
        leaf = re.split(r"[\\/]", filename)[-1]
        leaf = re.sub(r"\.{2,}", ".", leaf).lstrip(". ")
        safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", leaf).strip() or "document.md"

        text = extract_text(safe_name, content)
        size = len(text.encode("utf-8"))
        if size == 0 or not text.strip():
            raise DocumentError("That file is empty.")
        if size > MAX_BYTES_PER_DOC:
            raise DocumentError(
                f"That document is {size // 1024}KB. The per-document limit is "
                f"{MAX_BYTES_PER_DOC // 1024}KB — split it, or trim it to the sections you want to test."
            )

        with self._lock:
            self._evict()
            corpus = self._corpora.setdefault(cid, Corpus(corpus_id=cid))
            if len(corpus.docs) >= MAX_DOCS_PER_CORPUS:
                raise DocumentError(
                    f"You already have {MAX_DOCS_PER_CORPUS} documents in this corpus. "
                    "Remove one before adding another."
                )
            if corpus.total_bytes + size > MAX_BYTES_PER_CORPUS:
                raise DocumentError(
                    f"That would take this corpus past {MAX_BYTES_PER_CORPUS // 1024}KB. "
                    "Remove a document first."
                )

            checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            for existing in corpus.docs.values():
                if existing.checksum == checksum:
                    raise DocumentError(
                        f"That is the same content as '{existing.filename}' "
                        f"({existing.doc_id}), which is already loaded."
                    )

            seq = len(corpus.docs) + 1
            while f"UP-{seq:02d}" in corpus.docs:
                seq += 1
            doc_id = f"UP-{seq:02d}"

            stem = safe_name.rsplit(".", 1)[0]
            chunks = chunk_markdown(
                text,
                source=safe_name,
                stem=stem,
                doc_id=doc_id,
                category="uploaded",
                # 'authority' is what the citation renderer and the groundedness
                # report key off. An uploaded document is not the curated corpus
                # and must never be presented as though it were.
                authority="user-upload",
                min_preamble_words=8,
                min_section_words=6,
            )
            if not chunks:
                # A short note with no '##' headings still deserves to be indexed.
                chunks = chunk_markdown(
                    "## " + stem[:60] + "\n\n" + text,
                    source=safe_name, stem=stem, doc_id=doc_id,
                    category="uploaded", authority="user-upload",
                    min_preamble_words=10_000, min_section_words=1,
                )
            if not chunks:
                raise DocumentError("Nothing in that file could be indexed — it has no readable text.")
            chunks = chunks[:MAX_CHUNKS_PER_DOC]

            findings = [
                {"control": f.control, "name": f.name, "severity": f.severity, "evidence": f.evidence}
                for f in check_document(text, safe_name)
            ]

            doc = UploadedDoc(
                doc_id=doc_id,
                filename=safe_name,
                title=chunks[0].title,
                bytes=size,
                words=sum(c.word_count for c in chunks),
                chunks=chunks,
                findings=findings,
                checksum=checksum,
            )
            corpus.docs[doc_id] = doc
            corpus.revision += 1
            corpus.last_used = time.time()
            self._stores.pop(cid, None)
            return doc.summary()

    def remove(self, corpus_id: str | None, doc_id: str) -> bool:
        cid = self._clean_id(corpus_id)
        with self._lock:
            corpus = self._corpora.get(cid) if cid else None
            if not corpus or doc_id not in corpus.docs:
                return False
            corpus.docs.pop(doc_id)
            corpus.revision += 1
            corpus.last_used = time.time()
            self._stores.pop(cid, None)
            return True

    def clear(self, corpus_id: str | None) -> int:
        cid = self._clean_id(corpus_id)
        with self._lock:
            corpus = self._corpora.pop(cid, None) if cid else None
            self._stores.pop(cid, None)
            return len(corpus.docs) if corpus else 0

    def reset(self) -> None:
        """Test hook: forget every corpus."""
        with self._lock:
            self._corpora.clear()
            self._stores.clear()


REGISTRY = CorpusRegistry()
