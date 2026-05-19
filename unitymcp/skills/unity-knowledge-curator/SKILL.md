---
name: unity-knowledge-curator
description: Knowledge base'i (Unity Manual, ScriptReference, paket docs, Steamworks docs, curated articles) yönetmek için kullan. Triggerlar - "knowledge base güncelle", "yeni article ekle", "unity 6.1 docs çek", "doc search çalışmıyor", "vector db rebuild", "ingest yeniden çalıştır", "bm25 index güncelle", "qdrant durumu", "embed re-run", "kaç doc var", "knowledge status". Plugin'in self-extending knowledge layer'ını yönetir.
---

# Unity Knowledge Curator

Sen plugin'in knowledge base'ini yöneten uzmansın. Kullanıcı yeni kaynak eklemek, mevcut'u güncellemek, veya index/vector DB ile ilgili bir şey istediğinde bu skill devreye girer.

## Knowledge Mimarisi

```
knowledge/                       <- Tüm bilgi tabanı (.gitignore'da, lokal/PC başı)
├── unity-manual/
│   ├── Manual/                  <- docs.unity3d.com Manual section
│   └── ScriptReference/         <- ScriptReference section
├── packages/
│   ├── com.unity.render-pipelines.universal/
│   ├── com.unity.inputsystem/
│   └── ...
├── steamworks/
│   ├── features/
│   ├── sdk/
│   └── webapi/
└── articles/                    <- Kullanıcı curate ettiği makaleler
    ├── blog_unity_com__...md
    └── catlikecoding_com__...md

.index/
└── bm25.json                    <- BM25 index (knowledge'den derive)

# Qdrant: docker container, /qdrant/storage'da persist
```

## Workflow — Yeni Kaynak Ekleme

### Senaryo 1: Unity yeni sürüm çıktı (örn. 6.1)

```powershell
cd $env:USERPROFILE\ClaudePlugins\unitymcp-marketplace
python -m tools.ingest.unity_manual --version 6000.1 --out knowledge/unity-manual --resume
python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
python -m tools.index.embed_docs --knowledge knowledge --collection unity-knowledge
```

3 adım: ingest → BM25 rebuild → vector re-embed. `--resume` ile sadece yeni dosyalar çekilir.

### Senaryo 2: Yeni paket dokümantasyonu eklemek

```powershell
python -m tools.ingest.package_docs --packages com.unity.netcode.gameobjects --out knowledge/packages
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

### Senaryo 3: Article eklemek (kullanıcı bir URL listesi verir)

`articles.txt` oluştur:
```
https://blog.unity.com/games/...
https://catlikecoding.com/unity/tutorials/...
# yorum satırı
```

Sonra:
```powershell
python -m tools.ingest.articles --url-list articles.txt --out knowledge/articles
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

### Senaryo 4: Steamworks docs güncelle

```powershell
python -m tools.ingest.steamworks --out knowledge/steamworks
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

## Workflow — Sorun Giderme

### "doc search çalışmıyor" sorusu geldiğinde

1. **MCP server bağlı mı kontrol et**:
   ```
   Claude oturumunda: /mcp
   "unity-docs" listede ve "connected" olmalı
   ```

2. **knowledge_status tool'unu çağır**:
   ```
   Söyle: "knowledge_status tool'unu çağır"
   ```
   Çıktı şuna benzer:
   ```json
   {
     "total_md_files": 1847,
     "sections": { "unity-manual": 1234, "packages": 412, ... },
     "bm25_ready": true,
     "vector_backend_active": true
   }
   ```

3. **Qdrant ayakta mı kontrol et**:
   ```powershell
   docker ps | findstr qdrant
   curl http://localhost:6333/collections
   ```
   Değilse:
   ```powershell
   cd $env:USERPROFILE\ClaudePlugins\unitymcp-marketplace
   docker compose -f docker/docker-compose.yml up -d
   ```

### "BM25 index yok" hatası

```powershell
python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
```

### "Qdrant collection yok" hatası

```powershell
python -m tools.index.embed_docs --reset --knowledge knowledge --collection unity-knowledge
```

`--reset` collection'u sıfırdan oluşturur.

## Knowledge Base'in Sınırları

Kullanıcı sana "her şeyi öğrendin mi?" diye sorduğunda:

- **Çekilen kaynaklar**: Unity Manual + ScriptReference (1500-2000 sayfa), URP/HDRP/Input/Cinemachine/Addressables/Localization/Animation Rigging/Netcode (~500 sayfa), Steamworks public (~200 sayfa), kullanıcının eklediği articles
- **Çekilmeyenler**: Login gerektiren Steam partner docs, Unity Asset Store sayfaları, video transkriptler (manuel ekleme gerek), kapalı kaynaklı paket docs
- **Update frequency**: Manuel — kullanıcı periyodik olarak ingest komutlarını çalıştırmalı
- **Disk kullanımı**: ~500MB knowledge/, ~100MB .index/bm25.json, ~300MB Qdrant storage (toplam ~1GB)

## Performans İpuçları

- **BM25 rebuild** ~10 saniye / 1000 doc
- **Embedding (bge-small-en)** ~30 saniye / 1000 chunk (CPU)
- **Qdrant arama** <50ms / sorgu
- **Vector model** bge-small-en (~130MB) varsayılan; daha iyisi için `BAAI/bge-base-en-v1.5` (~440MB)

## Vector Backend Devre Dışı Olduğunda

Kullanıcı sadece BM25 ile çalışmak isteyebilir (Docker kurmayı atlamak için):

`unitymcp/.mcp.json` içinde `UNITYMCP_QDRANT` env var'ını sil veya boş bırak. Server otomatik BM25-only fallback'e geçer.

## Workflow — Düzenli Bakım

Aylık öneri (kullanıcıya hatırlat):
1. Yeni Unity sürüm çıktıysa Manual+ScriptReference re-ingest
2. Paket sürümleri arttıysa `package_docs.py --packages <pkg>` re-run
3. Yeni okuduğun makaleleri articles.txt'e ekle, ingest et
4. BM25 + Vector index'leri rebuild

## Kullanıcı Sorusuna Cevap Pattern'i

Kullanıcı: "Knowledge base nasıl?"
Sen:
1. `knowledge_status` tool'unu çağır
2. Çıktıyı parse et
3. Türkçe özet ver:
   - "X dosya knowledge'de var, Y section'a dağılmış. BM25 hazır, vector backend [aktif/pasif]"
4. Eksik bir şey varsa öneri sun (örn. "Localization paketi yok, ingest edelim mi?")
