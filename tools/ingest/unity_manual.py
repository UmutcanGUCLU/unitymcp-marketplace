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

# Rate-limit + nezaket (Unity Cloudflare cok agresif)
CONCURRENT_REQUESTS = 2
REQUEST_TIMEOUT = 30
RETRY_COUNT = 5
DELAY_BETWEEN_REQUESTS = 0.4  # her request arasi minimum bekleme
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unity docs ingestor")
    p.add_argument("--version", default="6000.0", help="Unity major version, e.g. 6000.0")
    p.add_argument("--out", default="knowledge/unity-manual", help="Output directory")
    p.add_argument("--section", choices=SECTIONS + ["all"], default="all")
    p.add_argument("--limit", type=int, default=0, help="Max pages (0 = unlimited)")
    p.add_argument("--resume", action="store_true", help="Var olan dosyaları atla")
    p.add_argument(
        "--filter",
        choices=["all", "classes", "classes-methods"],
        default="all",
        help="ScriptReference filtre - 'classes' = sadece class sayfalari (no -, no method .), "
             "'classes-methods' = class + method (no -), 'all' = her sey",
    )
    return p.parse_args()


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    """HTTP GET with rate-limit-aware retries."""
    last_status = None
    for attempt in range(RETRY_COUNT):
        try:
            r = await client.get(url, timeout=REQUEST_TIMEOUT)
            last_status = r.status_code
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                # Kalici yok — retry yapma
                return None
            if r.status_code == 429:
                # Rate limited — Retry-After header'i varsa onu kullan
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = 10
                else:
                    wait = min(60, 2 ** (attempt + 3))  # 8, 16, 32, 60, 60
                await asyncio.sleep(wait)
                continue
            # Diger gecici hatalar (502/503) icin exponential backoff
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt == RETRY_COUNT - 1:
                print(f"  ! Network error: {url.split('/')[-1]}: {e}", file=sys.stderr)
                return None
        await asyncio.sleep(2 ** attempt)
    if last_status and last_status != 404:
        print(f"  ! HTTP {last_status} (after {RETRY_COUNT} retries): {url.split('/')[-1]}", file=sys.stderr)
    return None


def html_to_markdown(html: str, source_url: str) -> tuple[str, str]:
    """HTML sayfasını markdown'a çevirir. Unity docs spesifik: #content-wrap > .section."""
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)
        title = re.sub(r"^(Unity\s*-\s*Manual:\s*|Unity\s*-\s*Scripting\s*API:\s*)", "", title)

    # Unity docs'ta asil icerik #content-wrap > .content-block > .content > .section
    # En spesifikten en genele fallback
    container = (
        soup.select_one("#content-wrap .section") or
        soup.select_one("#content-wrap .content") or
        soup.select_one("#content-wrap") or
        soup.select_one(".content-block .section") or
        soup.find("article") or
        soup.find("main") or
        soup.body
    )

    if container is None:
        return title, ""

    # Container icindeki chrome'u temizle
    chrome_selectors = [
        "script", "style", "noscript",
        ".breadcrumbs", ".breadcrumb", ".nextprev", ".pulldown",
        ".otherversionscontent", ".otherversions", ".otherversionslink",
        ".feedbackbox", ".lang-switcher", ".lang-list", ".language-picker",
        ".version-picker", ".version-number", ".search-form", ".sbox",
        "#_leavefeedback", ".mb20",
        # Image-comp wrapper'ları gerek yok ama tutalim, icerigi geriye kalir
    ]
    for sel in chrome_selectors:
        for tag in container.select(sel):
            tag.decompose()

    # Markdownify
    body_md = md(
        str(container),
        heading_style="ATX",
        bullets="-",
        strip=["link", "meta"],  # link ve meta tag'lerini at, ama anchor'leri (a) tut
    )
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()

    # YAML frontmatter
    section = urlparse(source_url).path.split("/")
    section_name = section[3] if len(section) > 3 else "Manual"
    frontmatter = f"""---
title: "{title.replace('"', "'")}"
source: "{source_url}"
section: "{section_name}"
---

"""
    return title, frontmatter + body_md


async def get_page_list(
    client: httpx.AsyncClient,
    base_url: str,
    section: str,
    section_dir: Path | None = None,
) -> list[str]:
    """
    Bir bölümün tüm sayfalarını listele.
    Eger section_dir verilirse, BFS sirasinda HTML'leri diske ayni anda yaz.
    Strategy:
      1. Try docdata/toc.json (Unity'nin internal TOC format'ı, varsa hızlı)
      2. BFS crawl from known entry points
    """
    # Strategy 1: docdata/index.json — Unity'nin internal full TOC
    # Format: {"pages": [["slug", "displayName"], ...]}
    index_url = f"{base_url}/{section}/docdata/index.json"
    try:
        r = await client.get(index_url, timeout=60)
        print(f"  docdata/index.json deneme: HTTP {r.status_code}, {len(r.content)} bytes", file=sys.stderr)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "pages" in data:
                result = []
                for entry in data["pages"]:
                    if isinstance(entry, list) and len(entry) >= 1:
                        slug = entry[0]
                        result.append(f"{base_url}/{section}/{slug}.html")
                if result:
                    print(f"  docdata/index.json kullanildi: {len(result)} sayfa")
                    return result
            else:
                print(f"  docdata/index.json beklenmedik format (keys: {list(data.keys()) if isinstance(data, dict) else type(data)})", file=sys.stderr)
    except Exception as e:
        print(f"  docdata/index.json hata: {type(e).__name__}: {e}", file=sys.stderr)

    # Strategy 1b: docdata/toc.json (eski format, varsa)
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
            result = [f"{base_url}/{section}/{p}" for p in pages if p.endswith(".html")]
            if result:
                print(f"  TOC JSON kullanildi: {len(result)} sayfa")
                return result
    except Exception:
        pass

    # Strategy 2: Sade discovery — sadece entry sayfasinin link'lerinden cikar
    # 16 paralel istek yerine entry-only fetch, ondan tum linkleri al.
    # Asil indirme process_page'de tek tek + nezaketli yapilir.
    if section == "Manual":
        entry_candidates = ["UnityManual.html", "index.html"]
    else:
        entry_candidates = ["index.html", "UnityEngine.html"]

    section_path = f"/{section}/"
    discovered: set[str] = set()
    entry_html = None
    entry_url = None

    for candidate in entry_candidates:
        url = f"{base_url}/{section}/{candidate}"
        html = await fetch(client, url)
        if html:
            entry_url = url
            entry_html = html
            discovered.add(url)
            print(f"  Entry bulundu: {candidate}")
            break
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

    if not entry_html:
        print(f"  ! Hicbir entry point yanit vermedi (denenen: {entry_candidates})")
        return []

    # Entry sayfasini diske kaydet
    if section_dir is not None:
        try:
            title, content = html_to_markdown(entry_html, entry_url)
            if content.strip():
                (section_dir / safe_filename(entry_url)).write_text(content, encoding="utf-8")
        except Exception:
            pass

    # Entry HTML'inden tum linkleri cikar
    level1_pages: set[str] = set()

    def collect_links(html: str, base: str) -> set[str]:
        s = BeautifulSoup(html, "lxml")
        found = set()
        for a in s.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("http://", "https://", "mailto:", "javascript:", "#")):
                continue
            if not href.endswith(".html"):
                continue
            full = urljoin(base, href.split("#")[0])
            if section_path not in full or base_url not in full:
                continue
            found.add(full)
        return found

    level1_pages = collect_links(entry_html, entry_url)
    discovered.update(level1_pages)
    print(f"  Level 1: entry'den {len(level1_pages)} landing sayfa")

    # Level 2: Her landing sayfasini sirasiyla fetch et, onun linklerini al
    # Rate-limit dostu — sirasi gore, delay'li.
    print(f"  Level 2: landing sayfalardan child link'ler toplaniyor...")
    level2_new = 0
    for i, page_url in enumerate(sorted(level1_pages)):
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
        html = await fetch(client, page_url)
        if not html:
            continue
        # Discovery sirasinda sayfayi da kaydet (cift fetch'i onler)
        if section_dir is not None:
            try:
                title, content = html_to_markdown(html, page_url)
                if content.strip():
                    out_path = section_dir / safe_filename(page_url)
                    if not out_path.exists():
                        out_path.write_text(content, encoding="utf-8")
            except Exception:
                pass
        new_links = collect_links(html, page_url) - discovered
        discovered.update(new_links)
        level2_new += len(new_links)
        if (i + 1) % 10 == 0:
            print(f"    {i + 1}/{len(level1_pages)} landing islendi, toplam {len(discovered)} sayfa")

    print(f"  Level 2: {level2_new} yeni child sayfa kesfedildi")
    print(f"  Toplam: {len(discovered)} sayfa")
    return sorted(discovered)


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

    if out_path.exists() and resume:
        return False
    if out_path.exists() and out_path.stat().st_size > 200:
        # Onceden BFS'de yazildi, atla
        return False

    async with sem:
        try:
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            html = await fetch(client, url)
            if not html:
                return False
            title, content = html_to_markdown(html, url)
            if not content.strip():
                return False
            out_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"  ! Exception {url.split('/')[-1]}: {type(e).__name__}: {e}", file=sys.stderr)
            return False


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

            pages = await get_page_list(client, base_url, section, section_dir=section_dir)

            # Filtre uygula (ScriptReference icin)
            if section == "ScriptReference" and args.filter != "all":
                def keep(url: str) -> bool:
                    slug = url.rsplit("/", 1)[-1].replace(".html", "")
                    has_dash = "-" in slug  # property/event marker
                    if args.filter == "classes-methods":
                        return not has_dash
                    if args.filter == "classes":
                        # Class: no dash, ve son . sonrasi method degil (kucuk harf baslar -> method)
                        if has_dash:
                            return False
                        # Son segmente bak
                        parts = slug.split(".")
                        if len(parts) >= 2 and parts[-1] and parts[-1][0].islower():
                            return False  # method (e.g. UnityEngine.Object.Destroy)
                        return True
                    return True

                before = len(pages)
                pages = [u for u in pages if keep(u)]
                print(f"  Filtre '{args.filter}' uygulandi: {before} -> {len(pages)} sayfa")
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
