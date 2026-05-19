# GitHub'a Push Etmek

Bu repo'yu kendi GitHub hesabına atmak için.

## Hesabını Hazırla

1. GitHub.com'a gir, `unitymcp-marketplace` adında yeni public repo aç (README ve LICENSE EKLEME — bizde var)
2. URL'i kopyala: `https://github.com/<senin_username>/unitymcp-marketplace.git`

## Repo'yu Local Git'e Çevir + Push

```powershell
cd C:\Users\umutc\ClaudePlugins\unitymcp-marketplace

# Git init (yoksa)
git init
git branch -M main

# Tüm dosyaları ekle (knowledge/ gitignore'da, push edilmez)
git add .
git status   # ne push edileceğini gör

# İlk commit
git commit -m "feat: initial release v0.2.0 — full-stack Unity 6 plugin + knowledge layer"

# Remote ekle
git remote add origin https://github.com/<senin_username>/unitymcp-marketplace.git

# Push
git push -u origin main
```

İlk push'ta kimlik doğrulama:
- GitHub username
- Personal Access Token (parola yerine — github.com/settings/tokens'tan oluştur)

## Tag + Release (sürüm yayını)

```powershell
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

GitHub web'de Releases > Draft new release > tag seç > açıklama yaz > Publish.

## Başka PC'den Çekme

```powershell
cd $env:USERPROFILE\ClaudePlugins
git clone https://github.com/<senin_username>/unitymcp-marketplace.git
cd unitymcp-marketplace

# Claude'u kur:
claude
# /plugin marketplace add .
# /plugin install unitymcp@unitymcp-marketplace
```

## Update Yapmak

Yerel değişiklik yaptın (skill ekledin, ingest tool güncelledin):

```powershell
cd C:\Users\umutc\ClaudePlugins\unitymcp-marketplace
git add .
git commit -m "feat: <ne değişti>"
git push
```

Diğer PC'de:
```powershell
git pull
```

Claude'da plugin'i refresh et:
```
/plugin update unitymcp@unitymcp-marketplace
/reload-plugins
```

## Public mi Private mi?

**Public yap** eğer:
- Plugin'i başkalarıyla paylaşmak istiyorsan
- Portfolio'da göstermek istiyorsan
- Topluluk PR'ları alabilirsin

**Private yap** eğer:
- Kişisel notlarını içeriyorsa (CLAUDE.md.template projem detaylarını içeriyorsa)
- Lisans belirsiz article URL'leri eklediysen
- Sadece kendin için

Public yaparken `articles.txt` ve proje-spesifik CLAUDE.md'leri commit etmemeye dikkat — `.gitignore` zaten korur.

## Marketplace URL kullanımı

Repo public ise herkes şununla install edebilir:

```
/plugin marketplace add github:<senin_username>/unitymcp-marketplace
/plugin install unitymcp@unitymcp-marketplace
```

Bu yöntem her PC'de USB ihtiyacını ortadan kaldırır — sadece git pull + reload.
