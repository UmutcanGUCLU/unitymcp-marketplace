# Knowledge Ingest Rehberi

Bu rehber knowledge base'i nasıl genişletip güncel tutacağını anlatır.

## İlk Ingest (Tek Seferlik)

```powershell
.\.venv\Scripts\Activate.ps1

# 1. Unity Manual + ScriptReference
python -m tools.ingest.unity_manual --version 6000.0 --out knowledge/unity-manual

# 2. Önemli paketler
python -m tools.ingest.package_docs --out knowledge/packages

# 3. Steamworks public docs
python -m tools.ingest.steamworks --out knowledge/steamworks

# 4. Index oluştur
python -m tools.index.build_bm25 --knowledge knowledge --out .index/bm25.json
python -m tools.index.embed_docs --knowledge knowledge --collection unity-knowledge  # opsiyonel
```

## Spesifik Paket Eklemek

Yeni paketle çalışıyorsun (örn. ECS / DOTS):

```powershell
python -m tools.ingest.package_docs --packages com.unity.entities --out knowledge/packages
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

Birden fazla paket aynı anda:
```powershell
python -m tools.ingest.package_docs --packages com.unity.entities com.unity.physics com.unity.netcode --out knowledge/packages
```

Desteklenen default paketler (`tools/ingest/package_docs.py` içinde `DEFAULT_PACKAGES`):
- com.unity.render-pipelines.universal (URP)
- com.unity.render-pipelines.high-definition (HDRP)
- com.unity.inputsystem
- com.unity.cinemachine
- com.unity.addressables
- com.unity.localization
- com.unity.animation.rigging
- com.unity.ai.navigation
- com.unity.entities
- com.unity.netcode.gameobjects

Yeni paket eklemek için `DEFAULT_PACKAGES` dict'ine ekle veya `--packages` ile geç.

## Article Curation

### URL Listesi Hazırla

`articles.txt` adlı dosya oluştur:

```
# Unity Blog
https://blog.unity.com/games/unity-tips-and-tricks
https://blog.unity.com/engine-platform/unity-6-rendering-improvements

# Catlike Coding (URP shaders, mathematics)
https://catlikecoding.com/unity/tutorials/custom-srp/
https://catlikecoding.com/unity/tutorials/jasper-flick/...

# Microsoft Learn (C#)
https://learn.microsoft.com/en-us/dotnet/csharp/...

# GitHub README'ler
https://github.com/Cysharp/UniTask/blob/master/README.md
https://github.com/dbrizov/NaughtyAttributes/blob/master/README.md

# Yorum satırları # ile başlar
```

### Ingest Et

```powershell
python -m tools.ingest.articles --url-list articles.txt --out knowledge/articles
```

### Re-index

```powershell
python -m tools.index.build_bm25
python -m tools.index.embed_docs  # vector kullanıyorsan
```

## Curation İlkeleri

**Eklemen önerilen:**
- ✓ Unity Blog (CC-BY veya benzer açık)
- ✓ Microsoft Learn / .NET docs
- ✓ GitHub README'ler ve open-source proje docs'ları
- ✓ Unity Manual / ScriptReference (zaten otomatik)
- ✓ CC-licensed eğitim siteleri (her zaman lisans kontrol et)
- ✓ Kendi notların / notion / obsidian'dan export

**Eklemen önerilmeyen:**
- ✗ Asset Store sayfaları (telif)
- ✗ Paid course içerikleri (Udemy, Coursera, vb.)
- ✗ Kişisel siteler (yazardan izinsiz)
- ✗ Forum thread'leri (genelde kalitesiz, dağınık)
- ✗ Stack Overflow (legal olarak grey area; SO'nun resmi data dump'ı var, oradan filter edilebilir)

**Kişisel kullanım vs paylaşım:**
- Bu setup **kişisel kullanım** için. Knowledge folder gitignored, sadece sende.
- Knowledge'i başkasına dağıtıyorsan **lisans kontrol et**.

## Güncelleme Stratejisi

Önerilen frekans:
- **Unity Manual**: 6 ayda bir veya yeni Unity LTS çıktığında
- **Paket docs**: Paket sürümü değişince
- **Steamworks**: Yılda bir kez (yavaş değişiyor)
- **Articles**: Yeni okuduğun bir şeyi eklemek istediğinde

Hızlı update komutu (her şey değişmemiş ama Unity yeni sürüm):
```powershell
python -m tools.ingest.unity_manual --version 6000.1 --resume
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

`--resume` mevcut dosyaları atlar, sadece yenilerini çeker.

## Disk Yönetimi

knowledge/ büyüyebilir. Görmek için:
```powershell
Get-ChildItem knowledge -Recurse -File | Measure-Object -Property Length -Sum
# Toplam byte
```

Temizlik:
```powershell
Remove-Item -Recurse knowledge/articles/eski_proje_*
python -m tools.index.build_bm25
python -m tools.index.embed_docs --reset
```

`--reset` collection'u sıfırdan oluşturur — silinen doc'lar gerçekten gider.

## Manuel Doc Ekleme

Kendi notların veya custom doc'u eklemek için:

```
knowledge/notes/my_tycoon_patterns.md
```

İçeriği:
```markdown
---
title: "Tycoon Game Patterns"
source: "personal-notes"
section: "notes"
---

# Tycoon Sistem Mimarisi

...içerik...
```

Sonra re-index:
```powershell
python -m tools.index.build_bm25
python -m tools.index.embed_docs
```

Claude artık `search_unity_docs` ile bu notlarını da bulur.
