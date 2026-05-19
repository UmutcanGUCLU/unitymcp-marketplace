"""
Unity package documentation indirici.

URP, HDRP, Input System, Cinemachine, vb. paketlerin docs.unity3d.com'daki
sürüm-spesifik dokümantasyonunu çeker.

Kullanım:
    python -m tools.ingest.package_docs --out knowledge/packages
    python -m tools.ingest.package_docs --packages com.unity.render-pipelines.universal --out knowledge/packages
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm.asyncio import tqdm_asyncio

# Unity 6 LTS için tipik paket sürümleri (kullanıcı override edebilir)
DEFAULT_PACKAGES = {
    "com.unity.render-pipelines.universal": "17.0",
    "com.unity.render-pipelines.high-definition": "17.0",
    "com.unity.inputsystem": "1.11",
    "com.unity.cinemachine": "3.1",
    "com.unity.addressables": "2.2",
    "com.unity.localization": "1.5",
    "com.unity.animation.rigging": "1.3",
    "com.unity.ai.navigation": "2.0",
    "com.unity.entities": "1.3",  # DOTS
    "com.unity.netcode.gameobjects": "2.0",
}

USER_AGENT = "unitymcp-knowledge-ingestor/0.2"
CONCURRENT = 4
TIMEOUT = 30


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url, timeout=TIMEOUT)
        return r.text if r.status_code == 200 else None
    except httpx.RequestError as e:
        print(f"  ! {url}: {e}", file=sys.stderr)
        return None


def html_to_md(html: str, source: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("article") or soup.find("div", id="content_wrap") or soup.body
    if main is None:
        return ""
    # Cleanup
    for tag in main.select("nav, .breadcrumbs, .footer, .search"):
        tag.decompose()
    title = "Untitled"
    h1 = main.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    body = md(str(main), heading_style="ATX", bullets="-")
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return f"""---
title: "{title.replace('"', "'")}"
source: "{source}"
---

{body}
"""


async def get_package_pages(client: httpx.AsyncClient, base: str) -> list[str]:
    """Paket TOC'unu bul ve tüm sayfaları listele."""
    # Unity package docs format: docs.unity3d.com/Packages/<pkg>@<version>/manual/<page>.html
    index_url = f"{base}/manual/index.html"
    html = await fetch(client, index_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    pages = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".html") and not href.startswith(("http://", "https://")):
            pages.add(urljoin(index_url, href))
    return sorted(pages)


def safe_filename(url: str) -> str:
    name = url.rsplit("/", 1)[-1].replace(".html", "")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name) + ".md"


async def process_package(client, pkg: str, version: str, out_root: Path) -> None:
    base = f"https://docs.unity3d.com/Packages/{pkg}@{version}"
    print(f"\n=== {pkg}@{version} ===")
    pages = await get_package_pages(client, base)
    if not pages:
        print(f"  ! {pkg}: sayfa bulunamadı, URL/sürüm kontrol et: {base}")
        return
    print(f"  {len(pages)} sayfa")

    pkg_dir = out_root / pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(CONCURRENT)

    async def fetch_one(url: str) -> bool:
        async with sem:
            html = await fetch(client, url)
            if not html:
                return False
            content = html_to_md(html, url)
            if not content.strip():
                return False
            (pkg_dir / safe_filename(url)).write_text(content, encoding="utf-8")
            return True

    results = await tqdm_asyncio.gather(*[fetch_one(u) for u in pages], desc=f"  {pkg}")
    print(f"  ✓ {sum(results)} yazıldı")


async def main_async(args):
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if args.packages:
        # Custom liste; sürümleri default'tan al, yoksa "latest"
        pkgs = {p: DEFAULT_PACKAGES.get(p, "latest") for p in args.packages}
    else:
        pkgs = DEFAULT_PACKAGES

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for pkg, version in pkgs.items():
            await process_package(client, pkg, version, out_root)

    print(f"\nTamamlandı. Çıktı: {out_root.resolve()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="knowledge/packages")
    parser.add_argument("--packages", nargs="*", help="Spesifik paketler (default: tüm liste)")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
