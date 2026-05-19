"""
Tüm knowledge/ chunk'larını embed et ve Qdrant'a yükle.

Default: bge-small-en (yerel, ücretsiz, ~130MB model)
Alternative: fastembed başka model destekler

Kullanım:
    # Önce Docker'da Qdrant'ı başlat: docker compose -f docker/docker-compose.yml up -d
    python -m tools.index.embed_docs --knowledge knowledge --collection unity-knowledge
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

import frontmatter
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm


def chunk_text(text: str, max_words: int = 400, overlap: int = 50) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks, current, current_len = [], [], 0
    for para in paragraphs:
        words = para.split()
        if current_len + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current = current[-overlap:] if overlap else []
            current_len = len(current)
        current.extend(words)
        current_len += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge", default="knowledge")
    parser.add_argument("--collection", default="unity-knowledge")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--reset", action="store_true", help="Collection'u sil ve yeniden oluştur")
    args = parser.parse_args()

    knowledge_root = Path(args.knowledge)
    if not knowledge_root.exists():
        print(f"Knowledge klasörü yok: {knowledge_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Embedding model yükleniyor: {args.model}")
    embed_model = TextEmbedding(model_name=args.model)

    # Vector boyutunu öğren
    sample = list(embed_model.embed(["test"]))
    vector_size = len(sample[0])
    print(f"Vector boyutu: {vector_size}")

    print(f"Qdrant: {args.qdrant_url}")
    client = QdrantClient(url=args.qdrant_url)

    # Collection setup
    existing = [c.name for c in client.get_collections().collections]
    if args.reset and args.collection in existing:
        print(f"Mevcut '{args.collection}' siliniyor...")
        client.delete_collection(args.collection)
        existing.remove(args.collection)

    if args.collection not in existing:
        print(f"Collection yaratılıyor: {args.collection}")
        client.create_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Chunks'ı topla
    print("Knowledge dosyaları taranıyor...")
    all_chunks = []
    for path in knowledge_root.rglob("*.md"):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        chunks = chunk_text(post.content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "payload": {
                    "path": str(path.relative_to(knowledge_root)),
                    "title": post.metadata.get("title", path.stem),
                    "source": post.metadata.get("source", ""),
                    "section": post.metadata.get("section", str(path.relative_to(knowledge_root).parts[0])),
                    "chunk_index": i,
                    "text": chunk,
                },
            })

    print(f"{len(all_chunks)} chunk embed edilecek")

    # Batch embedding + upsert
    for i in tqdm(range(0, len(all_chunks), args.batch_size), desc="Embed+Upsert"):
        batch = all_chunks[i : i + args.batch_size]
        texts = [c["text"] for c in batch]
        embeddings = list(embed_model.embed(texts))

        points = [
            PointStruct(
                id=batch[j]["id"],
                vector=embeddings[j].tolist(),
                payload=batch[j]["payload"],
            )
            for j in range(len(batch))
        ]
        client.upsert(collection_name=args.collection, points=points)

    info = client.get_collection(args.collection)
    print(f"\n✓ Tamamlandı. Collection '{args.collection}' içinde {info.points_count} point var")


if __name__ == "__main__":
    main()
