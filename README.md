# unitymcp-marketplace

**Full-stack Unity 6 (URP) Claude Code plugin + knowledge base.**

Claude'u Unity konusunda production-grade bir geliştirme partneri yapar. Plugin'in içinde 8 domain skill, 3 sub-agent, 4 slash command, Unity Editor MCP entegrasyonu, ve self-extending knowledge base (Unity Manual, ScriptReference, paket dokümanları, Steamworks, curated articles üzerinde hybrid search) bulunur.

## Hızlı Kurulum

### 1. Clone

```powershell
git clone https://github.com/GarroshCan/unitymcp-marketplace.git
cd unitymcp-marketplace
```

### 2. Claude Code'a marketplace ekle

```
claude
```

Claude oturumunda:
```
/plugin marketplace add .
/plugin install unitymcp@unitymcp-marketplace
/reload-plugins
```

Bu kadarıyla **Seviye 1 aktif** — 8 skill + agents + commands kullanılabilir.

### 3. Knowledge base aktive etmek (Seviye 2 — opsiyonel ama önerilen)

Python 3.10+ kurulu olsun. Sonra:

```powershell
# Bağımlılıklar
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r tools/requirements.txt
pip install -e mcp-server/

# Knowledge ingest (15-30 dakika sürer, internet hızına bağlı)
python -m tools.ingest.unity_manual --version 6000.0 --out knowledge/unity-manual
python -m tools.ingest.package_docs --out knowledge/packages
python -m tools.ingest.steamworks --out knowledge/steamworks

# BM25 index
python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
```

Claude Code'u yeniden başlat. Artık `search_unity_docs` MCP tool'u çalışır — Claude doğrudan resmi Unity docs'tan arama yapabilir.

### 4. Vector search (Seviye 3 — gelişmiş)

Docker Desktop kurulu olsun. Sonra:

```powershell
# Qdrant başlat
docker compose -f docker/docker-compose.yml up -d

# Tüm knowledge'i embed et (bge-small-en, yerel, ücretsiz; ~5-10 dakika)
python -m tools.index.embed_docs --knowledge knowledge --collection unity-knowledge
```

Hybrid search aktive olur: BM25 + semantic vector.

## Mimari

```
unitymcp-marketplace/
├── .claude-plugin/
│   └── marketplace.json              <- Marketplace manifest
├── unitymcp/                         <- Plugin'in kendisi
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json                     <- unity-editor + unity-docs MCP'leri
│   ├── skills/                       <- 9 skill (8 domain + knowledge-curator)
│   ├── agents/                       <- 3 sub-agent
│   ├── commands/                     <- 4 slash command
│   └── templates/                    <- CLAUDE.md.template
├── tools/                            <- İngest + index scriptleri
│   ├── ingest/
│   │   ├── unity_manual.py
│   │   ├── package_docs.py
│   │   ├── steamworks.py
│   │   └── articles.py
│   ├── index/
│   │   ├── build_bm25.py
│   │   └── embed_docs.py
│   └── requirements.txt
├── mcp-server/                       <- Doc-search MCP server
│   ├── doc_search/
│   │   ├── server.py
│   │   └── search.py
│   └── pyproject.toml
├── docker/
│   └── docker-compose.yml            <- Qdrant
├── knowledge/                        <- (gitignored) İndirilen docs
├── .index/                           <- (gitignored) BM25 index
└── docs/                             <- Detaylı kurulum + kullanım rehberleri
```

## Üç Seviye

| Seviye | İçerik | Setup | Etki |
|---|---|---|---|
| **1 — Plugin core** | 9 skill, 3 agent, 4 command | `/plugin install ...` | Claude Unity hakkında ezbere bildiği şeyler + projedeki kodu okuma + skill referansları |
| **2 — BM25 search** | + 2000 sayfa Unity Manual/ScriptReference + paket docs + Steamworks docs | Python venv + ingest + bm25 build | Claude resmi docs'tan keyword arama yapabilir, halüsinasyon azalır |
| **3 — Vector + hybrid** | + semantik arama | + Docker Qdrant + embed | Claude "X'e benzer pattern" gibi anlamsal sorgulara cevap verir |

## Kullanım Örnekleri

```
"NavMeshAgent SetDestination performance — ne yapmamalıyım?"
→ Claude search_unity_docs ile resmi docs'tan ilgili sayfayı çeker
→ Kod örneği + production tuzakları ile cevap verir
```

```
"Steam Cloud Auto-Save nasıl ayarlanır?"
→ search_unity_docs Steamworks sectionından ilgili rehberi çeker
→ Adım adım kurulum
```

```
/unity-shader-from-spec dissolve effect with orange edge glow
→ Önce knowledge'den ilgili shader pattern'lerini çekebilir
→ URP-uyumlu, SRP Batcher-friendly shader üretir
```

## Knowledge Güncelleme

Yeni Unity sürümü çıktığında:

```powershell
python -m tools.ingest.unity_manual --version 6000.1 --resume
python -m tools.index.build_bm25
python -m tools.index.embed_docs  # vector kullanıyorsan
```

`--resume` flag'i sadece yeni sayfaları çeker.

Kendi article koleksiyonun için `articles.txt` yaz, ingest et:

```powershell
python -m tools.ingest.articles --url-list articles.txt --out knowledge/articles
python -m tools.index.build_bm25
```

Detaylı bilgi: `docs/SETUP.md`, `docs/INGEST.md`, `docs/MCP-SETUP.md`.

## Plugin'in İçeriği (Seviye 1)

### 9 Skill

`unity-csharp-architecture`, `unity-gameplay-systems`, `unity-data-saving`, `unity-rendering-urp`, `unity-performance`, `unity-ui`, `unity-editor-tooling`, `unity-workflow`, `unity-knowledge-curator`

### 3 Sub-Agent

`shader-reviewer`, `perf-auditor`, `editor-tool-builder`

### 4 Slash Command

`/unity-new-system`, `/unity-shader-from-spec`, `/unity-review-mono`, `/unity-explain`

## Lisans

MIT. Plugin kodu ve örneklerin tümü MIT. **Knowledge base** içeriği orijinal kaynaklarının lisansına tâbi (Unity docs Unity'ye ait, Steam docs Valve'a ait, articles yazarlarına ait). Knowledge tarafı gitignore'da — bu repo'da redistribute edilmez, her PC'de kullanıcı kendi ingest'ini çalıştırır.

## Katkı

Skill ekleme, ingest tool genişletme, bug fix PR'ları memnuniyetle.

## Bağımlılıklar

- Python 3.10+
- Claude Code CLI
- (opsiyonel Seviye 3) Docker Desktop, ~2GB disk
- (opsiyonel) Unity 6 LTS + CoplayDev/unity-mcp Editor package

---

GarroshCan tarafından kişisel kullanım için yapıldı, MIT olarak paylaşılıyor. İyi geliştirmeler.
