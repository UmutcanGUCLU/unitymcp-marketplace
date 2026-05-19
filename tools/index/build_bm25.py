"""
BM25 index oluştur.

Tüm knowledge/ altındaki .md dosyalarını okur, BM25 index oluşturur,
.index/bm25.json olarak kaydeder.

Kullanım:
    python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import frontmatter
from rank_bm25 import BM25Okapi
from tqdm import tqdm


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def chunk_text(text: str, max_words: int = 400, overlap: int = 50) -> list[str]:
    """Markdown'ı paragraf bazlı parçala, paragraf büyükse word-bazlı kes."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        words = para.split()
        if current_len + len(words) > max_words and current:
            chunks.append(" ".join(current))
            # Overlap için son birkaç kelimeyi koru
            current = current[-overlap:] if overlap else []
            current_len = len(current)
        current.extend(words)
        current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    return chunks


def tokenize(text: str) -> list[str]:
    """Basit ama Unity API'lerine uygun tokenizer.
    CamelCase'i de bölüyor (Rigidbody.AddForce -> rigidbody, add, force)."""
    # CamelCase split
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    # Tokenize
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]{1,}", text.lower())
    return tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge", default="knowledge", help="Knowledge root")
    parser.add_argument("--out", default=".index/bm25.json")
    parser.add_argument("--chunk-size", type=int, default=400)
    args = parser.parse_args()

    knowledge_root = Path(args.knowledge)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Knowledge root: {knowledge_root.resolve()}")

    documents = []   # her chunk için doc info
    corpus_tokens = []  # tokenize edilmiş chunk'lar

    files = list(iter_markdown_files(knowledge_root))
    print(f"{len(files)} markdown dosyası bulundu")

    for path in tqdm(files, desc="Index"):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        title = post.metadata.get("title", path.stem)
        source = post.metadata.get("source", "")
        section = post.metadata.get("section", str(path.relative_to(knowledge_root).parts[0]))

        chunks = chunk_text(post.content, max_words=args.chunk_size)
        for i, chunk in enumerate(chunks):
            documents.append({
                "path": str(path.relative_to(knowledge_root)),
                "title": title,
                "source": source,
                "section": section,
                "chunk_index": i,
                "text": chunk,
            })
            corpus_tokens.append(tokenize(chunk))

    if not corpus_tokens:
        print("Hiç doc bulunamadı, ingest scriptlerini önce çalıştır")
        return

    print(f"\n{len(documents)} chunk indexlendi")
    print("BM25 ağırlıkları hesaplanıyor...")

    # BM25 ağırlıkları zaten lazy hesaplanır; serialize için tokens ve corpus'u kaydet
    output = {
        "version": "bm25-1.0",
        "chunk_size": args.chunk_size,
        "documents": documents,
        "corpus_tokens": corpus_tokens,
    }

    out_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ Index yazıldı: {out_path.resolve()}")
    print(f"  Boyut: {out_path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
