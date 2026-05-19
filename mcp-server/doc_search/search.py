"""
Hibrit arama: BM25 + Qdrant vector search.

BM25 her zaman çalışır (knowledge/ + .index/bm25.json gerekli).
Vector search opsiyonel — Qdrant erişilebilirse otomatik kullanılır.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """Aynı build_bm25.py'daki tokenizer."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return re.findall(r"[a-zA-Z][a-zA-Z0-9]{1,}", text.lower())


@dataclass
class SearchResult:
    title: str
    path: str
    source: str
    section: str
    text: str
    score: float
    backend: str  # "bm25", "vector", "hybrid"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "path": self.path,
            "source": self.source,
            "section": self.section,
            "text": self.text[:600] + ("..." if len(self.text) > 600 else ""),
            "score": round(self.score, 4),
            "backend": self.backend,
        }


class BM25Backend:
    """JSON-serialized BM25 index'i yükle ve sorgula."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        if not index_path.exists():
            raise FileNotFoundError(f"BM25 index yok: {index_path}. Önce build_bm25.py çalıştır.")

        data = json.loads(index_path.read_text(encoding="utf-8"))
        self.documents = data["documents"]
        self.corpus_tokens = data["corpus_tokens"]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        if not query.strip():
            return []
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        # Top-k indexler
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            d = self.documents[i]
            results.append(SearchResult(
                title=d["title"],
                path=d["path"],
                source=d["source"],
                section=d["section"],
                text=d["text"],
                score=float(scores[i]),
                backend="bm25",
            ))
        return results


class VectorBackend:
    """Qdrant + fastembed vector search."""

    def __init__(self, qdrant_url: str = "http://localhost:6333",
                 collection: str = "unity-knowledge",
                 model: str = "BAAI/bge-small-en-v1.5"):
        try:
            from fastembed import TextEmbedding
            from qdrant_client import QdrantClient
        except ImportError as e:
            raise RuntimeError(
                f"Vector backend için fastembed + qdrant-client gerekli: {e}"
            )

        self.client = QdrantClient(url=qdrant_url, timeout=5)
        self.collection = collection
        self.model = TextEmbedding(model_name=model)

        # Bağlantı test
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if collection not in collections:
                raise RuntimeError(f"Qdrant collection '{collection}' bulunamadı. Önce embed_docs.py çalıştır.")
        except Exception as e:
            raise RuntimeError(f"Qdrant'a bağlanamadı ({qdrant_url}): {e}")

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        if not query.strip():
            return []
        query_vec = list(self.model.embed([query]))[0].tolist()
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=query_vec,
            limit=top_k,
        )
        return [
            SearchResult(
                title=hit.payload.get("title", "?"),
                path=hit.payload.get("path", ""),
                source=hit.payload.get("source", ""),
                section=hit.payload.get("section", ""),
                text=hit.payload.get("text", ""),
                score=float(hit.score),
                backend="vector",
            )
            for hit in hits
        ]


class HybridSearcher:
    """
    BM25 + Vector hibrit. Sonuçları reciprocal rank fusion ile birleştir.
    Vector backend yoksa BM25-only fallback.
    """

    def __init__(self, index_path: Path, qdrant_url: str | None = None, collection: str = "unity-knowledge"):
        self.bm25 = BM25Backend(index_path)
        self.vector: VectorBackend | None = None
        if qdrant_url:
            try:
                self.vector = VectorBackend(qdrant_url=qdrant_url, collection=collection)
            except Exception as e:
                print(f"[doc-search] Vector backend devre dışı: {e}")
                self.vector = None

    def search(self, query: str, top_k: int = 10, mode: str = "auto") -> list[SearchResult]:
        """
        mode: "auto" (hybrid varsa, yoksa bm25), "bm25", "vector", "hybrid"
        """
        if mode == "bm25" or (mode == "auto" and self.vector is None):
            return self.bm25.search(query, top_k=top_k)

        if mode == "vector":
            if not self.vector:
                raise RuntimeError("Vector backend mevcut değil")
            return self.vector.search(query, top_k=top_k)

        # Hybrid: RRF
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        vec_results = self.vector.search(query, top_k=top_k * 2) if self.vector else []

        # Reciprocal Rank Fusion (k=60 standart)
        rrf_scores: dict[str, tuple[float, SearchResult]] = {}
        for rank, r in enumerate(bm25_results):
            key = f"{r.path}#{r.text[:50]}"
            rrf_scores[key] = (rrf_scores.get(key, (0.0, r))[0] + 1.0 / (60 + rank + 1), r)
        for rank, r in enumerate(vec_results):
            key = f"{r.path}#{r.text[:50]}"
            existing = rrf_scores.get(key, (0.0, r))
            rrf_scores[key] = (existing[0] + 1.0 / (60 + rank + 1), existing[1])

        # Skor güncelle, hybrid olarak işaretle
        merged = []
        for score, r in rrf_scores.values():
            r.score = score
            r.backend = "hybrid" if self.vector else "bm25"
            merged.append(r)
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]
