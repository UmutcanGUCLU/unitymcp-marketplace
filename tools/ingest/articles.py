"""
Kullanıcı-curated article ingestor.

Sen bir URL listesi verirsin (örn. articles.txt), bu script hepsini fetch eder,
markdown'a çevirir, knowledge/articles/ altına yazar.

Kullanım:
    python -m tools.ingest.articles --url-list my-articles.txt --out knowledge/articles

articles.txt format:
    https://blog.unity.com/games/unity-tips-and-tricks
    https://catlikecoding.com/unity/tutorials/...
    # yorum satırları # ile başlar

NOT: Sadece sana ait veya CC-license'lı içeriği indir. Telif hakkı saygıdır.
Unity blog, Microsoft Learn, GitHub README'leri public; özel siteler için izin al.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm.asyncio import tqdm_asyncio

USER_AGENT = "unitymcp-knowledge-ingestor/0.2 (personal-use article curator)"
TIMEOUT = 30
CONCURRENT = 3  # site başına nezaket
RETRY = 2


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    for attempt in range(RETRY + 1):
        try:
            r = await client.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
            if r.status_code in (401, 403, 404):
                return None
        except httpx.RequestError:
            pass
        if attempt < RETRY:
            await asyncio.sleep(2 ** attempt)
    return None


def extract_article(html: str, url: str) -> tuple[str, str]:
    """HTML'den ana article içeriğini çıkar ve markdown'a çevir."""
    soup = BeautifulSoup(html, "lxml")

    # Genel olarak <article>, ana içerik
    candidates = (
        soup.find("article"),
        soup.find("main"),
        soup.find("div", attrs={"role": "main"}),
        soup.find("div", class_=re.compile("post|article|content|entry")),
    )
    main = next((c for c in candidates if c is not None), soup.body)
    if main is None:
        return "", ""

    # Gereksiz elementleri temizle
    for selector in ["nav", "header", "footer", "aside", ".sidebar", ".comments",
                     ".advertisement", ".social", ".share", "script", "style"]:
        for tag in main.select(selector):
            tag.decompose()

    # Title
    title = "Untitled"
    h1 = main.find("h1") or soup.find("h1") or soup.find("title")
    if h1:
        title = h1.get_text(strip=True)

    body_md = md(str(main), heading_style="ATX", bullets="-")
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    return title, body_md


def safe_filename(url: str, title: str) -> str:
    """URL veya title'dan güvenli dosya adı."""
    base = title if title and title != "Untitled" else urlparse(url).path
    base = re.sub(r"[^a-zA-Z0-9-_]+", "_", base)[:80].strip("_") or "article"
    domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    return f"{domain}__{base}.md"


def parse_url_list(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


async def main_async(args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = parse_url_list(Path(args.url_list))
    print(f"{len(urls)} URL işlenecek")

    sem = asyncio.Semaphore(CONCURRENT)

    async def process(url: str) -> bool:
        async with sem:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                html = await fetch(client, url)
                if not html:
                    return False
                title, body = extract_article(html, url)
                if not body.strip():
                    return False
                content = f"""---
title: "{title.replace('"', "'")}"
source: "{url}"
---

{body}
"""
                filename = safe_filename(url, title)
                (out_dir / filename).write_text(content, encoding="utf-8")
                return True

    results = await tqdm_asyncio.gather(*[process(u) for u in urls], desc="Articles")
    print(f"\n✓ {sum(results)} article indirildi, {len(results) - sum(results)} başarısız")
    print(f"Çıktı: {out_dir.resolve()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url-list", required=True, help="URL listesi (her satır bir URL)")
    parser.add_argument("--out", default="knowledge/articles")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
