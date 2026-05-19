# v0.2 Kurulum Rehberi — Adım Adım (PowerShell)

Yepyeni bir PC'de sıfırdan kurulum. Tahmini süre: 30-60 dakika (knowledge ingest dahil).

## Gereksinimler

- Windows 10/11 (Linux/macOS adımları benzerdir, path'leri ayarla)
- PowerShell 5.1+ veya PowerShell 7
- Python 3.10+ ([python.org](https://python.org)/Microsoft Store)
- Git ([git-scm.com](https://git-scm.com))
- Claude Code CLI ([docs.claude.com](https://docs.claude.com/en/docs/claude-code/setup))
- (opsiyonel — Seviye 3) Docker Desktop

## Adım 1 — Repo'yu Clone Et

```powershell
cd $env:USERPROFILE\ClaudePlugins
git clone https://github.com/GarroshCan/unitymcp-marketplace.git
cd unitymcp-marketplace
```

Yoksa ZIP indir ve extract et. Sonuç şu olmalı:
```
C:\Users\umutc\ClaudePlugins\unitymcp-marketplace\
  ├── .claude-plugin/
  ├── unitymcp/
  ├── tools/
  ├── mcp-server/
  └── ...
```

## Adım 2 — Seviye 1: Plugin Core (zorunlu)

```powershell
claude
```

Claude oturumunda:
```
/plugin marketplace add C:\Users\umutc\ClaudePlugins\unitymcp-marketplace
/plugin install unitymcp@unitymcp-marketplace
/reload-plugins
```

Test:
```
/plugin
```
`unitymcp v0.2.0` listede ve `enabled` olmalı.

```
/unity-explain ScriptableObject event channel
```
Test cevap geldiyse Seviye 1 hazır.

## Adım 3 — Seviye 2: Knowledge Base (BM25 Search)

### 3.1. Python venv kur

```powershell
cd C:\Users\umutc\ClaudePlugins\unitymcp-marketplace
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Eğer execution policy hatası:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install --upgrade pip
pip install -r tools/requirements.txt
pip install -e mcp-server/
```

### 3.2. Knowledge ingest

Unity Manual + ScriptReference (~10 dakika):
```powershell
python -m tools.ingest.unity_manual --version 6000.0 --out knowledge/unity-manual
```

Paket dokümanları (URP, HDRP, Input, Cinemachine, vb. — ~5 dakika):
```powershell
python -m tools.ingest.package_docs --out knowledge/packages
```

Steamworks public docs (~3 dakika):
```powershell
python -m tools.ingest.steamworks --out knowledge/steamworks
```

### 3.3. BM25 index oluştur

```powershell
python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
```

Çıktıda "{N} chunk indexlendi" görmelisin.

### 3.4. MCP server config'ini doğrula

`unitymcp/.mcp.json` zaten doğru env path'leri var. Claude Code'u yeniden başlat:
```powershell
exit  # Claude oturumundan
claude
```

Test:
```
/mcp
```
`unity-docs` listede ve `connected` olmalı.

```
"knowledge_status tool'unu çağır"
```
Çıktı: total_md_files, sections, bm25_ready: true.

```
"NavMeshAgent SetDestination performance konusunda Unity docs'ta arama yap"
```
Claude search_unity_docs ile resmi docs sayfasını getirip cevap vermeli.

## Adım 4 — Seviye 3: Vector Search (opsiyonel, gelişmiş)

### 4.1. Docker Desktop çalışıyor mu kontrol et

```powershell
docker --version
docker ps
```

### 4.2. Qdrant başlat

```powershell
cd C:\Users\umutc\ClaudePlugins\unitymcp-marketplace
docker compose -f docker/docker-compose.yml up -d
```

Kontrol:
```powershell
curl http://localhost:6333
```

### 4.3. Tüm knowledge'i embed et (5-15 dakika, CPU)

```powershell
.\.venv\Scripts\Activate.ps1
python -m tools.index.embed_docs --knowledge knowledge --collection unity-knowledge
```

İlk çalıştırmada bge-small-en (~130MB) indirilir. Sonra her chunk embed edilir, Qdrant'a upsert edilir.

### 4.4. Doğrula

Claude oturumunda:
```
"knowledge_status — vector backend aktif mi?"
```
`vector_backend_active: true` olmalı.

```
"shadow bias artifacting nedir? Unity docs'tan hybrid search ile bul"
```
Hybrid sonuçlar gelir (BM25 + vector).

## Adım 5 — Unity Editor MCP (opsiyonel)

Sadece Unity Editor'a doğrudan komut gönderme istersen:

```powershell
pip install uv
```

Sonra Unity 6 projende:
1. Window > Package Manager
2. + → Add package from git URL
3. `https://github.com/CoplayDev/unity-mcp.git?path=/UnityMcpBridge`
4. Window > Unity MCP > Auto-configure Claude Code

## Adım 6 — Her Unity Projende CLAUDE.md

```powershell
Copy-Item C:\Users\umutc\ClaudePlugins\unitymcp-marketplace\unitymcp\templates\CLAUDE.md.template `
  D:\GameDev\MyProject\CLAUDE.md
notepad D:\GameDev\MyProject\CLAUDE.md
```

Proje-spesifik kuralları doldur.

## Düzenli Bakım

### Unity yeni sürüm çıktı
```powershell
.\.venv\Scripts\Activate.ps1
python -m tools.ingest.unity_manual --version 6000.1 --resume
python -m tools.index.build_bm25
python -m tools.index.embed_docs  # vector kullanıyorsan
```

### Yeni article eklemek
1. `articles.txt` oluştur, satır satır URL yaz
2. `python -m tools.ingest.articles --url-list articles.txt --out knowledge/articles`
3. `python -m tools.index.build_bm25`
4. `python -m tools.index.embed_docs`

### Qdrant'ı kapatmak (RAM tasarrufu)
```powershell
docker compose -f docker/docker-compose.yml down
```
Yeniden açmak: `docker compose -f docker/docker-compose.yml up -d`

## Sorun Giderme

**"search_unity_docs çalışmıyor"**
- `/mcp` ile `unity-docs` connected mi kontrol et
- Connected değilse Claude'u restart et
- BM25 index var mı: `Test-Path .index\bm25.json`
- Yoksa: `python -m tools.index.build_bm25`

**"Qdrant connection refused"**
- Docker çalışıyor mu: `docker ps`
- Container ayakta mı: `docker ps | findstr qdrant`
- Yeniden başlat: `docker compose -f docker/docker-compose.yml restart`

**"ImportError: No module named ..."**
- venv aktif mi: prompt'ta `(.venv)` görmeli
- Yeniden install: `pip install -r tools/requirements.txt`

**"403 Forbidden"** (ingest sırasında)
- Rate limit'e takıldın, biraz bekle, `--resume` ile devam et
- User-Agent değişimi gerekebilir (tools/ingest/*.py'de)

## Disk Kullanımı

| Bileşen | Boyut |
|---|---|
| Plugin core | ~150 KB |
| Knowledge (Manual+ScriptReference+packages+Steamworks) | ~400-700 MB |
| .index/bm25.json | ~50-100 MB |
| Qdrant storage | ~200-400 MB |
| Python venv + fastembed model | ~500 MB |
| **Toplam** | **~1.5-2 GB** |

## Performans Beklentileri

- BM25 arama: <100ms
- Vector arama: <200ms (CPU)
- Hybrid (BM25 + Vector + RRF): <300ms
- Ingest: 10-20 dakika tamamı (one-time)
- BM25 rebuild: <30 saniye
- Vector embed (~5000 chunk): 5-10 dakika
