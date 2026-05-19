"""
MCP server: Unity knowledge doc-search.

Claude'a iki tool sunar:
- search_unity_docs(query, top_k, mode) — hibrit arama
- read_doc(path) — tam dosya içeriğini geri ver (chunk değil)

Kullanım (manuel test):
    python -m mcp_server.doc_search.server

Claude Code config (.mcp.json):
    {
      "mcpServers": {
        "unity-docs": {
          "command": "python",
          "args": ["-m", "mcp_server.doc_search.server"],
          "env": {
            "UNITYMCP_KNOWLEDGE": "C:/Users/umutc/ClaudePlugins/unitymcp-marketplace/knowledge",
            "UNITYMCP_INDEX": "C:/Users/umutc/ClaudePlugins/unitymcp-marketplace/.index/bm25.json",
            "UNITYMCP_QDRANT": "http://localhost:6333"
          }
        }
      }
    }
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .search import HybridSearcher

# Environment'tan path'ler
KNOWLEDGE_DIR = Path(os.environ.get("UNITYMCP_KNOWLEDGE", "knowledge"))
INDEX_PATH = Path(os.environ.get("UNITYMCP_INDEX", ".index/bm25.json"))
QDRANT_URL = os.environ.get("UNITYMCP_QDRANT", "")  # Boş ise vector backend devre dışı
COLLECTION = os.environ.get("UNITYMCP_COLLECTION", "unity-knowledge")

server = Server("unity-docs")

# Lazy init — ilk tool çağrısında
_searcher: HybridSearcher | None = None


def get_searcher() -> HybridSearcher:
    global _searcher
    if _searcher is None:
        qdrant = QDRANT_URL if QDRANT_URL else None
        _searcher = HybridSearcher(INDEX_PATH, qdrant_url=qdrant, collection=COLLECTION)
    return _searcher


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_unity_docs",
            description=(
                "Unity 6 LTS dokümantasyonu, URP/HDRP/Input System/Cinemachine/Addressables paket docs, "
                "Steamworks SDK ve curated articles içinde arama yapar. Hybrid search (BM25 + vector) kullanır. "
                "API ismi, kavram, hata mesajı, performans pattern'i, shader feature, vb. sorgular için kullan. "
                "Sonuç: ilgili dokümantasyon chunk'ları (her biri title, source URL, içerik). "
                "Yanıt sentezi için Claude'un bu chunk'ları okuyup soruyu yanıtlaması gerekir."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Arama sorgusu. Spesifik ol — 'NavMeshAgent SetDestination performance' iyi, 'unity' kötü."
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Kaç sonuç döndürülsün (default 8, max 20)",
                        "default": 8,
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "bm25", "vector", "hybrid"],
                        "description": "Arama modu (auto=hybrid varsa hybrid, yoksa bm25)",
                        "default": "auto",
                    },
                    "section_filter": {
                        "type": "string",
                        "description": "İsteğe bağlı section filtresi (örn. 'unity-manual/ScriptReference', 'packages/com.unity.render-pipelines.universal')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="read_doc",
            description=(
                "Bir doc'un tam içeriğini oku (search sonucundaki 'path' field'ı verilince). "
                "search_unity_docs sonucundaki chunk yerine tam sayfayı görmek istediğinde kullan."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Knowledge root'a göre relative path (search sonucundan al)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="knowledge_status",
            description="Knowledge base'in durumunu raporla — kaç dosya, hangi section'lar, vector backend aktif mi.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "search_unity_docs":
            query = arguments.get("query", "")
            top_k = min(int(arguments.get("top_k", 8)), 20)
            mode = arguments.get("mode", "auto")
            section_filter = arguments.get("section_filter", "")

            searcher = get_searcher()
            results = searcher.search(query, top_k=top_k, mode=mode)

            if section_filter:
                results = [r for r in results if section_filter in r.section or section_filter in r.path]

            payload = {
                "query": query,
                "mode": mode,
                "total": len(results),
                "results": [r.to_dict() for r in results],
            }
            return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]

        elif name == "read_doc":
            rel_path = arguments.get("path", "")
            full_path = KNOWLEDGE_DIR / rel_path
            if not full_path.exists():
                return [TextContent(type="text", text=f"Doc bulunamadı: {rel_path}")]
            content = full_path.read_text(encoding="utf-8")
            return [TextContent(type="text", text=content)]

        elif name == "knowledge_status":
            md_files = list(KNOWLEDGE_DIR.rglob("*.md")) if KNOWLEDGE_DIR.exists() else []
            sections: dict[str, int] = {}
            for f in md_files:
                section = str(f.relative_to(KNOWLEDGE_DIR).parts[0]) if f.relative_to(KNOWLEDGE_DIR).parts else "root"
                sections[section] = sections.get(section, 0) + 1

            vector_ok = False
            try:
                searcher = get_searcher()
                vector_ok = searcher.vector is not None
            except Exception:
                pass

            status = {
                "knowledge_dir": str(KNOWLEDGE_DIR.resolve()),
                "index_path": str(INDEX_PATH.resolve()),
                "total_md_files": len(md_files),
                "sections": sections,
                "bm25_ready": INDEX_PATH.exists(),
                "vector_backend_active": vector_ok,
                "qdrant_url": QDRANT_URL or "(not configured)",
            }
            return [TextContent(type="text", text=json.dumps(status, ensure_ascii=False, indent=2))]

        else:
            return [TextContent(type="text", text=f"Bilinmeyen tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Hata: {type(e).__name__}: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
