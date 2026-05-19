"""
Steamworks public docs ingestor.

Steam'in partner.steamgames.com/doc altındaki PUBLIC dokümantasyonu çeker.
(Login gerektiren özel API'ler değil — public reference materyali)

Kullanım:
    python -m tools.ingest.steamworks --out knowledge/steamworks
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm.asyncio import tqdm_asyncio

BASE = "https://partner.steamgames.com/doc"
USER_AGENT = "unitymcp-knowledge-ingestor/0.2"
TIMEOUT = 30
CONCURRENT = 3

# Gezinilecek public sections (Steam'in dokümantasyon hiyerarşisi)
SECTIONS = [
    "features",
    "store",
    "sdk",
    "webapi",
    "marketing",
    "gettingstarted",
]


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and "login" not in r.url.path.lower():
            return r.text
        return None
    except httpx.RequestError:
        return None


def is_steam_doc_link(href: str) -> bool:
    """partner.steamgames.com/doc içindeki link mi kontrol et."""
    return ("/doc/" in href) and ("partner.steamgames.com" in href or href.startswith("/doc/"))


async def crawl_section(client: httpx.AsyncClient, section: str, visited: set, out_root: Path) -> int:
    """Bir section'ı BFS ile gez."""
    queue = [f"{BASE}/{section}"]
    written = 0

    while queue:
        batch = queue[:CONCURRENT]
        queue = queue[CONCURRENT:]
        batch = [u for u in batch if u not in visited]
        visited.update(batch)

        results = await asyncio.gather(*[fetch(client, u) for u in batch])

        for url, html in zip(batch, results):
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            # Login redirect detection
            if soup.find("input", {"name": "username"}):
                continue

            # Ana içerik
            main = soup.find("div", class_="documentation_bbcode") or soup.find("div", id="mainContents")
            if main:
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "Untitled"

                # Cleanup
                for t in main.select("script, style, .responsive_search"):
                    t.decompose()

                body = md(str(main), heading_style="ATX", bullets="-")
                body = re.sub(r"\n{3,}", "\n\n", body).strip()

                filename = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.rsplit("/", 1)[-1])[:80] + ".md"
                section_dir = out_root / section
                section_dir.mkdir(exist_ok=True)
                (section_dir / filename).write_text(
                    f"""---
title: "{title.replace('"', "'")}"
source: "{url}"
section: "steamworks/{section}"
---

{body}
""",
                    encoding="utf-8",
                )
                written += 1

            # Discover more links within section
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if is_steam_doc_link(href):
                    full = urljoin(url, href)
                    if section in full and full not in visited:
                        queue.append(full)

        # Rate limit
        await asyncio.sleep(0.5)

    return written


async def main_async(args):
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    visited: set[str] = set()

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for section in SECTIONS:
            print(f"\n=== Steamworks/{section} ===")
            count = await crawl_section(client, section, visited, out_root)
            print(f"  ✓ {count} sayfa yazıldı")

    print(f"\nTamamlandı. Çıktı: {out_root.resolve()}")
    print("Not: Steam'in bazı belgeleri partner login gerektirir; sadece public erişilebilir olanlar indirildi.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="knowledge/steamworks")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
