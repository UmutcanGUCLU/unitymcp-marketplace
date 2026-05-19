# Unity .gitignore + .gitattributes Tam Şablon

Production-grade Unity Git setup. Doğrudan kopyala, projeye at.

## `.gitignore`

```gitignore
# =============================================================================
# Unity generated files
# =============================================================================
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
[Mm]emoryCaptures/
[Rr]ecordings/

# Asset meta data without parent
!/[Aa]ssets/**/*.meta

# Burst
.burst/
Library/Bee/

# =============================================================================
# IDE / Editor
# =============================================================================
.vs/
.vscode/
.idea/
*.csproj
*.unityproj
*.sln
*.suo
*.tmp
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db
ExportedObj/
.consulo/
*.csproj.bak

# =============================================================================
# OS
# =============================================================================
.DS_Store
.AppleDouble
.LSOverride
._*
Thumbs.db
ehthumbs.db
Desktop.ini

# =============================================================================
# Build outputs
# =============================================================================
*.apk
*.aab
*.unitypackage
*.app
crashlytics-build.properties

# =============================================================================
# Asset Store / 3rd party crap (eğer git'te tutmak istemiyorsan)
# =============================================================================
# Assets/Plugins/Demigiant/DOTweenPro/Examples/

# =============================================================================
# Custom
# =============================================================================
# Secrets, API keys
secrets/
*.secret
*.private
.env

# Build numbers, generated files
Assets/Resources/BuildInfo.asset

# Local test scenes
Assets/_LocalTests/
```

## `.gitattributes`

```gitattributes
# =============================================================================
# Line endings — Unity için CRLF kaçınılması gerekenler
# =============================================================================
* text=auto eol=lf

# Unity asset / meta files
*.cs            text eol=lf diff=csharp
*.cginc         text eol=lf
*.shader        text eol=lf
*.hlsl          text eol=lf
*.shadergraph   text eol=lf
*.shadersubgraph text eol=lf
*.compute       text eol=lf
*.uxml          text eol=lf
*.uss           text eol=lf
*.tss           text eol=lf
*.asmdef        text eol=lf
*.asmref        text eol=lf
*.json          text eol=lf
*.md            text eol=lf
*.txt           text eol=lf

# Unity scenes & prefabs — TEXT (Force Text Serialization gerekli)
# Eğer LFS'e atmak istersen alt satırı uncomment et
*.unity         text eol=lf merge=unityyamlmerge
*.prefab        text eol=lf merge=unityyamlmerge
*.asset         text eol=lf merge=unityyamlmerge
*.meta          text eol=lf merge=unityyamlmerge
*.mat           text eol=lf merge=unityyamlmerge
*.anim          text eol=lf merge=unityyamlmerge
*.controller    text eol=lf merge=unityyamlmerge
*.physicMaterial text eol=lf merge=unityyamlmerge
*.physicsMaterial2D text eol=lf merge=unityyamlmerge

# =============================================================================
# LFS — Binary asset'ler
# =============================================================================
# Images
*.psd  filter=lfs diff=lfs merge=lfs -text
*.png  filter=lfs diff=lfs merge=lfs -text
*.jpg  filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.tga  filter=lfs diff=lfs merge=lfs -text
*.tif  filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.exr  filter=lfs diff=lfs merge=lfs -text
*.hdr  filter=lfs diff=lfs merge=lfs -text
*.bmp  filter=lfs diff=lfs merge=lfs -text

# Models
*.fbx  filter=lfs diff=lfs merge=lfs -text
*.obj  filter=lfs diff=lfs merge=lfs -text
*.dae  filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text
*.3ds  filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav  filter=lfs diff=lfs merge=lfs -text
*.mp3  filter=lfs diff=lfs merge=lfs -text
*.ogg  filter=lfs diff=lfs merge=lfs -text
*.aif  filter=lfs diff=lfs merge=lfs -text
*.aiff filter=lfs diff=lfs merge=lfs -text
*.flac filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4  filter=lfs diff=lfs merge=lfs -text
*.mov  filter=lfs diff=lfs merge=lfs -text
*.avi  filter=lfs diff=lfs merge=lfs -text
*.webm filter=lfs diff=lfs merge=lfs -text

# Documents
*.pdf  filter=lfs diff=lfs merge=lfs -text

# Compressed
*.zip  filter=lfs diff=lfs merge=lfs -text
*.7z   filter=lfs diff=lfs merge=lfs -text
*.gz   filter=lfs diff=lfs merge=lfs -text

# Big binary
*.dll  filter=lfs diff=lfs merge=lfs -text
*.so   filter=lfs diff=lfs merge=lfs -text
*.dylib filter=lfs diff=lfs merge=lfs -text
*.a    filter=lfs diff=lfs merge=lfs -text
*.bundle filter=lfs diff=lfs merge=lfs -text

# Unity packed asset bundles
*.ress filter=lfs diff=lfs merge=lfs -text
*.resource filter=lfs diff=lfs merge=lfs -text
```

## İlk Kurulum Komutları

```bash
# Repo'yu init et
git init
git lfs install

# .gitignore ve .gitattributes ekle (yukarıdaki içerikler)
# Commit
git add .gitignore .gitattributes
git commit -m "chore: setup Unity gitignore + LFS"

# Unity'de Project Settings > Editor:
#   - Asset Serialization Mode: Force Text
#   - Version Control Mode: Visible Meta Files
# (Bunlar ProjectSettings/EditorSettings.asset'e yazılır)

# Şimdi Unity asset'lerini ekle
git add Assets/ ProjectSettings/ Packages/
git commit -m "feat: initial Unity project"
```

## UnityYAMLMerge Kurulumu

`.git/config` (her klon için yapılmalı, veya global):

```
[merge]
    tool = unityyamlmerge

[mergetool "unityyamlmerge"]
    trustExitCode = false
    keepTemporaries = true
    keepBackup = false
    cmd = '<UnityInstallPath>/Editor/Data/Tools/UnityYAMLMerge' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```

`<UnityInstallPath>` örneği:
- Windows: `C:/Program Files/Unity/Hub/Editor/6000.0.30f1`
- macOS: `/Applications/Unity/Hub/Editor/6000.0.30f1/Unity.app/Contents`
- Linux: `~/Unity/Hub/Editor/6000.0.30f1`

Şimdi:
```bash
git mergetool
# .unity ve .prefab conflict'lerinde otomatik akıllı merge dener
```

## LFS Quota & Maliyet

GitHub LFS:
- Free: 1 GB storage + 1 GB bandwidth/month
- Paid: $5/month → 50GB storage + 50GB bandwidth

Unity oyunları 5GB+ asset'e kolay ulaşır. Alternatifler:
- **Self-hosted Git LFS** (Gitea, Forgejo)
- **GitLab** (ucuz LFS)
- **Perforce / Plastic SCM** (Unity'nin kendi tercihi, büyük studio'lar)
