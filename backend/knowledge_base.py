# ENGINE: IntelligenceEngine
"""
PRISM Knowledge Base — document ingestion, embeddings, vector search, and RAG.

Pipeline:
  Documents (.txt) in backend/knowledge/
    ↓
  Chunk (500 tokens, 50 token overlap)  ← document ingestion
    ↓
  Embedding (sentence-transformers multi-lingual) ← embeddings
    ↓
  SQLite storage (documents table)
    ↓
  Cosine similarity search  ← vector search
    ↓
  Top-k results → ContextManager → LLM  ← RAG

Everything is designed to degrade gracefully. If sentence-transformers or
numpy is not installed, the KnowledgeBase falls back to a simple
keyword-based search so the system still works.
"""
import os
import re
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Config — environment-overridable
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
DEFAULT_CHUNK_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 50
DB_TABLE = "documents"


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class DocumentChunk:
    """One chunk of a document, ready for embedding / search."""
    chunk_id: str
    source: str            # e.g. "faq.txt", "refund_policy.txt"
    chunk_index: int
    text: str
    embedding: Optional[List[float]] = None   # None if embedding unavailable
    metadata: Dict[str, Any] = None           # source, created_at, chunk_index


# ──────────────────────────────────────────────────────────────────────
# Embedding wrapper — graceful fallback
# ──────────────────────────────────────────────────────────────────────

class EmbeddingProvider:
    """
    Generates embeddings using sentence-transformers.
    Falls back to None (no embeddings) if the library/model is unavailable.

    The system is still functional without embeddings — keyword search is used.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._available = None  # None = not checked yet

    def _ensure_model(self) -> bool:
        """Load the model lazily. Returns True if available."""
        if self._available is not None:
            return self._available

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._available = True
            logger.info(f"[KnowledgeBase] Embedding model loaded: {self.model_name}")
        except Exception as e:
            self._available = False
            self._model = None
            logger.warning(
                f"[KnowledgeBase] Embeddings unavailable: {e}. "
                "Falling back to keyword search. "
                "Install: pip install sentence-transformers torch"
            )
        return self._available

    @property
    def available(self) -> bool:
        return self._ensure_model()

    def embed(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed a list of text strings. Returns a list of the same length;
        each element is either a list of floats or None if embeddings unavailable.
        """
        if not self._ensure_model():
            return [None] * len(texts)

        try:
            # sentence-transformers returns numpy arrays
            import numpy as np
            vectors = self._model.encode(texts, convert_to_numpy=True)
            if isinstance(vectors, np.ndarray):
                return vectors.tolist()
            return [list(v) for v in vectors]
        except Exception as e:
            logger.warning(f"[KnowledgeBase] Embedding failed: {e}")
            return [None] * len(texts)

    def embed_one(self, text: str) -> Optional[List[float]]:
        """Embed a single string."""
        result = self.embed([text])
        return result[0] if result else None


# ──────────────────────────────────────────────────────────────────────
# Chunking utilities
# ──────────────────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """Very rough token estimate: ~4 chars per token for multi-lingual."""
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[str]:
    """
    Split text into overlapping chunks.

    Strategy:
      1. Split into paragraphs (double-newline)
      2. Merge paragraphs into chunks until max_tokens is reached
      3. Overlap by overlap_tokens worth of text at chunk boundaries
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [text.strip()] if text.strip() else []

    chunks: List[str] = []
    current_parts: List[str] = []
    current_tokens = 0
    overlap_buffer: List[str] = []
    overlap_tokens_current = 0

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_parts:
            # Close current chunk
            chunks.append("\n\n".join(current_parts))
            # Build overlap buffer from the tail of current_parts
            overlap_buffer = []
            overlap_tokens_current = 0
            for tail_part in reversed(current_parts):
                tail_tokens = _estimate_tokens(tail_part)
                if overlap_tokens_current + tail_tokens > overlap_tokens:
                    break
                overlap_buffer.insert(0, tail_part)
                overlap_tokens_current += tail_tokens
            current_parts = list(overlap_buffer)
            current_tokens = overlap_tokens_current

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return [c for c in chunks if c.strip()]


# ──────────────────────────────────────────────────────────────────────
# Cosine similarity
# ──────────────────────────────────────────────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    try:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    except Exception:
        return 0.0


# ──────────────────────────────────────────────────────────────────────
# Keyword fallback search (used when embeddings unavailable)
# ──────────────────────────────────────────────────────────────────────

def _keyword_score(query: str, doc_text: str) -> float:
    """
    Simple keyword overlap score.
    Breaks query into lowercase words, counts overlap with doc words.
    """
    q_words = set(re.findall(r"\w+", query.lower()))
    d_words = set(re.findall(r"\w+", doc_text.lower()))
    if not q_words:
        return 0.0
    overlap = q_words & d_words
    return len(overlap) / len(q_words)


# ──────────────────────────────────────────────────────────────────────
# KnowledgeBase — main class
# ──────────────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    PRISM Knowledge Base.

    Usage:
        kb = KnowledgeBase()
        kb.load_from_disk()               # index files in backend/knowledge/
        results = kb.semantic_search("What is the refund policy?", top_k=3)
        for text, score, source in results:
            ...
    """

    def __init__(self):
        self.embeddings = EmbeddingProvider()
        self._chunks: Dict[str, DocumentChunk] = {}   # chunk_id → chunk
        self._loaded = False
        self._ensure_db_table()

    # ── Database helpers ──────────────────────────────────────────────

    @staticmethod
    def _engine():
        from database import get_engine
        return get_engine()

    def _ensure_db_table(self) -> None:
        """Create the documents table if it doesn't exist."""
        engine = self._engine()
        if engine is None:
            return
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text(f"""
                    CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                        chunk_id     TEXT PRIMARY KEY,
                        source       TEXT NOT NULL,
                        chunk_index  INTEGER NOT NULL,
                        text         TEXT NOT NULL,
                        embedding    TEXT,           -- JSON serialized list[float] or NULL
                        created_at   TEXT NOT NULL,
                        UNIQUE(source, chunk_index)
                    )
                """))
                session.commit()
        except Exception as e:
            logger.warning(f"[KnowledgeBase] DB table ensure failed: {e}")

    def _persist_chunk(self, chunk: DocumentChunk) -> None:
        """Persist a chunk to the database."""
        engine = self._engine()
        if engine is None:
            return
        try:
            from sqlmodel import Session, text
            emb_json = json.dumps(chunk.embedding) if chunk.embedding else None
            with Session(engine) as session:
                session.exec(text(f"""
                    INSERT OR REPLACE INTO {DB_TABLE}
                    (chunk_id, source, chunk_index, text, embedding, created_at)
                    VALUES (:chunk_id, :source, :chunk_index, :text, :embedding, :created_at)
                """), {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "embedding": emb_json,
                    "created_at": datetime.utcnow().isoformat(),
                })
                session.commit()
        except Exception as e:
            logger.warning(f"[KnowledgeBase] Persist chunk failed: {e}")

    def _load_persisted_chunks(self) -> int:
        """Load chunks from database into memory. Returns count loaded."""
        engine = self._engine()
        if engine is None:
            return 0
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                rows = session.exec(text(f"""
                    SELECT chunk_id, source, chunk_index, text, embedding FROM {DB_TABLE}
                """)).fetchall()
            count = 0
            for chunk_id, source, chunk_index, text, emb_json in rows:
                embedding = json.loads(emb_json) if emb_json else None
                self._chunks[chunk_id] = DocumentChunk(
                    chunk_id=chunk_id,
                    source=source,
                    chunk_index=chunk_index,
                    text=text,
                    embedding=embedding,
                    metadata={"source": source, "chunk_index": chunk_index},
                )
                count += 1
            return count
        except Exception as e:
            logger.warning(f"[KnowledgeBase] Load persisted chunks failed: {e}")
            return 0

    # ── Disk / file loading ──────────────────────────────────────────

    def load_from_disk(self, kb_dir: str = KB_DIR, force_reindex: bool = False) -> int:
        """
        Load all .txt files from the knowledge directory, chunk them,
        embed (if available), persist to DB, and load into memory cache.

        Returns total chunks indexed.
        """
        # Always load DB-persisted chunks first for warm starts
        if not force_reindex:
            db_count = self._load_persisted_chunks()
            if db_count > 0:
                self._loaded = True
                logger.info(f"[KnowledgeBase] Loaded {db_count} chunks from DB")
                return db_count

        if not os.path.isdir(kb_dir):
            logger.warning(f"[KnowledgeBase] Knowledge directory not found: {kb_dir}")
            self._loaded = True
            return 0

        all_texts: List[Tuple[str, str]] = []   # (source_name, text_content)
        try:
            for fname in sorted(os.listdir(kb_dir)):
                if not fname.lower().endswith(".txt"):
                    continue
                fpath = os.path.join(kb_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read()
                    all_texts.append((fname, text))
                except Exception as e:
                    logger.warning(f"[KnowledgeBase] Failed to read {fname}: {e}")
        except Exception as e:
            logger.warning(f"[KnowledgeBase] List kb_dir failed: {e}")

        if not all_texts:
            self._loaded = True
            logger.info("[KnowledgeBase] No .txt files found")
            return 0

        # Chunk all files
        all_chunks: List[DocumentChunk] = []
        for source, text in all_texts:
            chunked_texts = chunk_text(text)
            for idx, chunk_text_content in enumerate(chunked_texts):
                cid = f"{source}#{idx}"
                all_chunks.append(DocumentChunk(
                    chunk_id=cid,
                    source=source,
                    chunk_index=idx,
                    text=chunk_text_content,
                    metadata={"source": source, "chunk_index": idx},
                ))

        # Embed in one batch if embeddings available
        if self.embeddings.available and all_chunks:
            chunk_texts = [c.text for c in all_chunks]
            vectors = self.embeddings.embed(chunk_texts)
            for chunk, vec in zip(all_chunks, vectors):
                chunk.embedding = vec

        # Persist and index in memory
        for chunk in all_chunks:
            self._persist_chunk(chunk)
            self._chunks[chunk.chunk_id] = chunk

        self._loaded = True
        logger.info(
            f"[KnowledgeBase] Loaded {len(all_chunks)} chunks from "
            f"{len(all_texts)} files (embeddings: {'on' if self.embeddings.available else 'off'})"
        )
        return len(all_chunks)

    def ensure_loaded(self) -> None:
        """Call before searches. Idempotent; loads on first call."""
        if not self._loaded:
            self.load_from_disk()

    # ── Search ────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        """
        General-purpose search. Uses semantic search if embeddings are
        available, falls back to keyword overlap otherwise.

        Returns list of (text, score, source_name).
        """
        self.ensure_loaded()
        if not self._chunks:
            return []

        query_vec = None
        if self.embeddings.available:
            query_vec = self.embeddings.embed_one(query)

        if query_vec is not None:
            return self.semantic_search_with_vector(query_vec, top_k=top_k)
        return self.keyword_search(query, top_k=top_k)

    def semantic_search(
        self, query_text: str, top_k: int = 3
    ) -> List[Tuple[str, float, str]]:
        """
        Semantic search using embeddings. Falls back to keyword search if
        embeddings are unavailable.

        Returns: [(chunk_text, similarity_score_0_to_1, source_filename), ...]
        sorted by highest score first.
        """
        self.ensure_loaded()
        if not self._chunks:
            return []

        if not self.embeddings.available:
            return self.keyword_search(query_text, top_k=top_k)

        query_vec = self.embeddings.embed_one(query_text)
        if query_vec is None:
            return self.keyword_search(query_text, top_k=top_k)

        return self.semantic_search_with_vector(query_vec, top_k=top_k)

    def semantic_search_with_vector(
        self, query_vec: List[float], top_k: int = 3
    ) -> List[Tuple[str, float, str]]:
        """Core cosine-similarity search given a pre-embedded query vector."""
        scored: List[Tuple[float, DocumentChunk]] = []
        for chunk in self._chunks.values():
            if chunk.embedding is None:
                continue
            score = _cosine_similarity(query_vec, chunk.embedding)
            scored.append((score, chunk))

        scored.sort(key=lambda t: t[0], reverse=True)
        results: List[Tuple[str, float, str]] = []
        for score, chunk in scored[:top_k]:
            results.append((chunk.text, float(score), chunk.source))
        return results

    def keyword_search(
        self, query: str, top_k: int = 3
    ) -> List[Tuple[str, float, str]]:
        """
        Keyword-overlap fallback search. Always works — no model required.
        """
        self.ensure_loaded()
        if not self._chunks:
            return []

        scored: List[Tuple[float, DocumentChunk]] = []
        for chunk in self._chunks.values():
            score = _keyword_score(query, chunk.text)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda t: t[0], reverse=True)
        results: List[Tuple[str, float, str]] = []
        for score, chunk in scored[:top_k]:
            results.append((chunk.text, float(score), chunk.source))
        return results

    # ── Ingestion API (for admin upload) ─────────────────────────────

    def ingest_document(
        self, source_name: str, text_content: str, reindex: bool = False
    ) -> int:
        """
        Programmatically ingest a single document into the knowledge base.

        Args:
            source_name:  Display name / filename for the source
            text_content: Raw text of the document
            reindex:      If True, remove old chunks for this source first

        Returns: number of chunks indexed.
        """
        if reindex:
            self._remove_source(source_name)

        chunked_texts = chunk_text(text_content)
        new_chunks: List[DocumentChunk] = []
        for idx, ct in enumerate(chunked_texts):
            cid = f"{source_name}#{idx}"
            new_chunks.append(DocumentChunk(
                chunk_id=cid, source=source_name, chunk_index=idx, text=ct,
                metadata={"source": source_name, "chunk_index": idx},
            ))

        if self.embeddings.available and new_chunks:
            vectors = self.embeddings.embed([c.text for c in new_chunks])
            for chunk, vec in zip(new_chunks, vectors):
                chunk.embedding = vec

        for chunk in new_chunks:
            self._persist_chunk(chunk)
            self._chunks[chunk.chunk_id] = chunk

        logger.info(
            f"[KnowledgeBase] Ingested {len(new_chunks)} chunks from '{source_name}'"
        )
        return len(new_chunks)

    def _remove_source(self, source_name: str) -> None:
        """Remove all chunks belonging to a source from memory and DB."""
        to_delete = [
            cid for cid, c in self._chunks.items() if c.source == source_name
        ]
        for cid in to_delete:
            del self._chunks[cid]

        engine = self._engine()
        if engine is None:
            return
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text(f"""
                    DELETE FROM {DB_TABLE} WHERE source = :source
                """), {"source": source_name})
                session.commit()
        except Exception as e:
            logger.warning(f"[KnowledgeBase] remove_source failed: {e}")

    # ── Diagnostics ───────────────────────────────────────────────────

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    @property
    def sources(self) -> List[str]:
        return sorted({c.source for c in self._chunks.values()})

    def status(self) -> Dict[str, Any]:
        """Return status info for /health / /knowledge/search diagnostics."""
        return {
            "loaded": self._loaded,
            "total_chunks": self.total_chunks,
            "sources": self.sources,
            "embeddings_available": self.embeddings.available,
            "embedding_model": self.embeddings.model_name if self.embeddings.available else None,
        }


# ──────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────

_knowledge_base = KnowledgeBase()


def get_knowledge_base() -> KnowledgeBase:
    """Return the shared KnowledgeBase singleton."""
    return _knowledge_base
