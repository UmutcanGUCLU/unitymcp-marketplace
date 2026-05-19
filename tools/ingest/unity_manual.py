"""
Unity Manual + ScriptReference indirici.

Kullanım:
    python -m tools.ingest.unity_manual --version 6000.0 --out knowledge/unity-manual

docs.unity3d.com'dan resmi belgeleri çeker, markdown'a çevirir, knowledge/ altına yazar.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm.asyncio import tqdm_asyncio

DEFAULT_BASE = "https://docs.unity3d.com/{version}/Documentation"
# Bölümler — Manual ve ScriptReference ayrı dizinlerde
SECTIONS = ["Manual", "ScriptReference"]

# Rate-limit + nezaket
CONCURRENT_REQUESTS = 4
REQUEST_TIMEOUT = 30
RETRY_COUNT = 3
USER_AGENT = "unitymcp-knowledge-ingestor/0.2 (+https://github.com/GarroshCan/unitymcp-marketplace)"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unity docs ingestor")
    p.add_argument("--version", default="6000.0", help="Unity major version, e.g. 6000.0")
    p.add_argument("--out", default="knowledge/unity-manual", help="Output directory")
    p.add_argument("--section", choices=SECTIONS + ["all"], default="all")
    p.add_argument("--limit", type=int, default=0, help="Max pages (0 = unlimited)")
    p.add_argument("--resume", action="store_true", help="Var olan dosyaları atla")
    return p.parse_args()


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    """HTTP GET with retries."""
    for attempt in range(RETRY_COUNT):
        try:
            r = await client.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt == RETRY_COUNT - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
                return None
        await asyncio.sleep(1.5 ** attempt)
    return None


def html_to_markdown(html: str, source_url: str) -> tuple[str, str]:
    """HTML sayfasını markdown'a çevirir, başlığı da çıkarır."""
    soup = BeautifulSoup(html, "lxml")

    # Unity docs'ta ana içerik genelde #content_wrap veya .content içinde
    main = soup.find("div", id="content_wrap") or soup.find("div", class_="content") or soup.body
    if main is None:
        return "", ""

    # Başlık
    title = "Untitled"
    h1 = main.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Navigation/footer/sidebar temizlikle (kalan içerik temiz markdown olsun)
    for tag in main.select(".breadcrumbs, .otherversionscontent, .signature-CS, .footer"):
        tag.decompose()

    body_md = md(str(main), heading_style="ATX", bullets="-")
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()

    # YAML frontmatter ekle
    frontmatter = f"""---
title: "{title.replace('"', "'")}"
source: "{source_url}"
section: "{urlparse(source_url).path.split('/')[3] if len(urlparse(source_url).path.split('/')) > 3 else 'Manual'}"
---

"""
    return title, frontmatter + body_md


async def get_page_list(client: httpx.AsyncClient, base_url: str, section: str) -> list[str]:
    """Bir bölümün tüm sayfalarını listele. Önce TOC'tan, olmazsa index'ten."""
    # Try docdata/toc.json (Unity'nin yeni docs site format'ı)
    toc_url = f"{base_url}/{section}/docdata/toc.json"
    try:
        r = await client.get(toc_url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            pages = []
            def walk(node):
                if isinstance(node, dict):
                    if "link" in node:
                        pages.append(node["link"])
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)
            walk(data)
            return [f"{base_url}/{section}/{p}" for p in pages if p.endswith(".html")]
    except Exception:
        pass

    # Fallback: index.html'i çek, link'leri scrape et
    index_url = f"{base_url}/{section}/index.html"
    html = await fetch(client, index_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".html") and not href.startswith(("http://", "https://", "mailto:")):
            full = urljoin(index_url, href)
            if section in full:
                links.add(full)
    return sorted(links)


def safe_filename(url: str) -> str:
    """URL'den güvenli dosya adı üret."""
    name = url.rsplit("/", 1)[-1]
    name = name.replace(".html", "")
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return f"{name}.md"


async def process_page(
    client: httpx.AsyncClient,
    url: str,
    section_dir: Path,
    resume: bool,
    sem: asyncio.Semaphore,
) -> bool:
    """Bir sayfayı işle: fetch + convert + write."""
    filename = safe_filename(url)
    out_path = section_dir / filename

    if resume and out_path.exists():
        return False

    async with sem:
        html = await fetch(client, url)
        if not html:
            return False
        title, content = html_to_markdown(html, url)
        if not content.strip():
            return False
        out_path.write_text(content, encoding="utf-8")
    return True


async def main_async(args: argparse.Namespace) -> None:
    base_url = DEFAULT_BASE.format(version=args.version)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sections_to_fetch = SECTIONS if args.section == "all" else [args.section]

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for section in sections_to_fetch:
            print(f"\n=== Bölüm: {section} ===")
            section_dir = out_dir / section
            section_dir.mkdir(exist_ok=True)

            pages = await get_page_list(client, base_url, section)
            print(f"  {len(pages)} sayfa bulundu")

            if args.limit > 0:
                pages = pages[: args.limit]
                print(f"  Limit uygulandı: {len(pages)}")

            sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
            tasks = [process_page(client, url, section_dir, args.resume, sem) for url in pages]
            results = await tqdm_asyncio.gather(*tasks, desc=f"  {section}")
            written = sum(1 for r in results if r)
            skipped = len(results) - written
            print(f"  ✓ {written} yazıldı, {skipped} atlandı/başarısız")

    print(f"\nTamamlandı. Çıktı: {out_dir.resolve()}")


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
