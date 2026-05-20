"""
Unity package documentation indirici.

URP, HDRP, Input System, Cinemachine, vb. paketlerin docs.unity3d.com'daki
dokümantasyonunu çeker.

Strateji:
1. Once docdata/index.json (Unity'nin internal TOC) dene
2. Sonra index.html link scraping fallback
3. Rate-limit dostu: 2 concurrent, 0.4s delay, 429 retry-after

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

# "latest" daha guvenli - Unity son surume yonlendirir
DEFAULT_PACKAGES = {
    "com.unity.render-pipelines.universal": "latest",
    "com.unity.render-pipelines.high-definition": "latest",
    "com.unity.inputsystem": "latest",
    "com.unity.cinemachine": "latest",
    "com.unity.addressables": "latest",
    "com.unity.localization": "latest",
    "com.unity.animation.rigging": "latest",
    "com.unity.ai.navigation": "latest",
    "com.unity.entities": "latest",
    "com.unity.netcode.gameobjects": "latest",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
CONCURRENT = 2
TIMEOUT = 30
RETRY_COUNT = 5
DELAY = 0.4


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    last_status = None
    for attempt in range(RETRY_COUNT):
        try:
            r = await client.get(url, timeout=TIMEOUT)
            last_status = r.status_code
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** (attempt + 3))
                await asyncio.sleep(wait)
                continue
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt == RETRY_COUNT - 1:
                print(f"  ! Network: {url.split('/')[-1]}: {e}", file=sys.stderr)
                return None
        await asyncio.sleep(2 ** attempt)
    if last_status and last_status != 404:
        print(f"  ! HTTP {last_status}: {url.split('/')[-1]}", file=sys.stderr)
    return None


def html_to_md(html: str, source: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)

    container = (
        soup.select_one("article") or
        soup.select_one("main") or
        soup.select_one("#content-wrap .section") or
        soup.select_one("#content-wrap") or
        soup.select_one(".content") or
        soup.body
    )
    if container is None:
        return title, ""

    for sel in ["nav", "header", "footer", "aside", ".sidebar", ".breadcrumbs",
                "script", "style", "noscript", ".search", ".version-picker",
                ".language-picker", ".lang-list"]:
        for tag in container.select(sel):
            tag.decompose()

    body_md = md(str(container), heading_style="ATX", bullets="-", strip=["link", "meta"])
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    return title, body_md


async def get_pages_for_package(client: httpx.AsyncClient, base: str) -> list[str]:
    # Strategy 1: docdata/index.json
    index_url = f"{base}/manual/docdata/index.json"
    try:
        r = await client.get(index_url, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "pages" in data:
                pages = []
                for entry in data["pages"]:
                    if isinstance(entry, list) and len(entry) >= 1:
                        slug = entry[0]
                        pages.append(f"{base}/manual/{slug}.html")
                if pages:
                    return pages
    except Exception:
        pass

    # Strategy 2: index.html link scraping fallback
    html = await fetch(client, f"{base}/manual/index.html")
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    pages = set()
    pages.add(f"{base}/manual/index.html")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".html") and not href.startswith(("http://", "https://", "mailto:", "#")):
            full = urljoin(f"{base}/manual/index.html", href.split("#")[0])
            if base in full:
                pages.add(full)
    return sorted(pages)


def safe_filename(url: str) -> str:
    name = url.rsplit("/", 1)[-1].replace(".html", "")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name) + ".md"


async def process_package(client, pkg: str, version: str, out_root: Path, resume: bool) -> None:
    base = f"https://docs.unity3d.com/Packages/{pkg}@{version}"
    print(f"\n=== {pkg}@{version} ===")
    pages = await get_pages_for_package(client, base)
    if not pages:
        print(f"  ! sayfa bulunamadi: {base}")
        return
    print(f"  {len(pages)} sayfa")

    pkg_dir = out_root / pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(CONCURRENT)

    async def fetch_one(url: str) -> bool:
        filename = safe_filename(url)
        out_path = pkg_dir / filename
        if resume and out_path.exists() and out_path.stat().st_size > 200:
            return False
        async with sem:
            await asyncio.sleep(DELAY)
            html = await fetch(client, url)
            if not html:
                return False
            title, body_md = html_to_md(html, url)
            if not body_md.strip():
                return False
            content = f"""---
title: "{title.replace('"', "'")}"
source: "{url}"
section: "packages/{pkg}"
---

{body_md}
"""
            out_path.write_text(content, encoding="utf-8")
            return True

    results = await tqdm_asyncio.gather(*[fetch_one(u) for u in pages], desc=f"  {pkg}")
    written = sum(1 for r in results if r)
    print(f"  v {written} yazildi")


async def main_async(args):
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    if args.packages:
        pkgs = {p: DEFAULT_PACKAGES.get(p, "latest") for p in args.packages}
    else:
        pkgs = DEFAULT_PACKAGES

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for pkg, version in pkgs.items():
            await process_package(client, pkg, version, out_root, resume=args.resume)

    print(f"\nTamamlandi. Cikti: {out_root.resolve()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="knowledge/packages")
    parser.add_argument("--packages", nargs="*", help="Spesifik paketler (default: tum liste)")
    parser.add_argument("--resume", action="store_true", help="Var olan dosyalari atla")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
