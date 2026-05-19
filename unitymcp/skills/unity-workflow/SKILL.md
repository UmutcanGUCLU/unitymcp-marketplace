---
name: unity-workflow
description: Unity profesyonel iş akışı — Git/LFS, .gitignore, merge conflict, klasör yapısı, naming convention, modüler mimari, build pipeline, addressables, Steam entegrasyonu, CI/CD konularında uzmanlaşmak için kullan. Triggerlar - "git unity", "LFS", "gitignore unity", "merge conflict unity", "smartmerge", "yamlmerge", "klasör yapısı", "folder structure", "naming convention", "addressables", "asset bundle", "build pipeline", "CI/CD unity", "Github Actions unity", "Steam integration", "Steamworks", "platform specific build", "il2cpp", "code stripping", "link.xml". Production studio'ların kullandığı standartları öner.
---

# Unity Professional Workflow (Unity 6 LTS)

Sen Unity production workflow uzmanısın. Studio'ların gerçekte kullandığı standartlara göre konuş — hobi tutorial'larından değil.

## Konu Kapsamı

### Git + Unity Doğru Kurulum

**1. `.gitignore`** — Unity'nin resmi şablonunu kullan, eklemeler:
```
# Unity generated
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
[Mm]emoryCaptures/

# IDE
.vs/
.vscode/
.idea/
*.csproj
*.sln
*.suo
*.user
*.pidb

# OS
.DS_Store
Thumbs.db

# Build outputs
*.apk
*.aab
*.unitypackage
```

**2. `.gitattributes` — LFS pattern'leri**:
```
*.psd filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.fbx filter=lfs diff=lfs merge=lfs -text
*.obj filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.unity filter=lfs diff=lfs merge=lfs -text  # büyük .unity sahneleri için tartışmalı, küçükse plain text bırak
```
**Tuzak**: `.unity` ve `.prefab` LFS'e atılırsa text merge yapılamaz. Studio kararı: sahne büyük ve binary-gibiyse LFS, küçük ve sık merge ediliyorsa plain text + Unity Smart Merge.

**3. Force Text Serialization + Visible Meta Files**
`Edit > Project Settings > Editor`:
- Asset Serialization Mode: **Force Text**
- Version Control Mode: **Visible Meta Files**

Yoksa merge mümkün olmaz, meta dosya kayıpları olur.

**4. Smart Merge (UnityYAMLMerge) ayarı**

`.git/config`:
```
[merge]
    tool = unityyamlmerge
[mergetool "unityyamlmerge"]
    trustExitCode = false
    cmd = '<unity_install>/Editor/Data/Tools/UnityYAMLMerge' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```
Şimdi `git mergetool` `.unity` ve `.prefab` dosyalarını anlamlı şekilde merge eder.

### Branching Strategy

**Trunk-based** (küçük ekip, hızlı iterate):
- `main` — her zaman çalışır durumda
- Kısa ömürlü feature branch'ler → günde merge
- Daily build CI'dan

**GitFlow** (büyük ekip, release cycle'ı sıkı):
- `main` (release), `develop` (integration), `feature/*`, `release/*`, `hotfix/*`
- Genelde Unity için overkill

**Trunk + Release branch** (genelde en doğru orta yol):
- `main` aktif geliştirme
- Release zamanı `release/v1.0` cut, sadece bugfix'ler oraya
- Hotfix → main + release branch

### Klasör Yapısı

```
Assets/
  _Project/                        <- senin kodun her şeyi burada (alt-tire ile en üstte sıralanır)
    Art/
      Characters/
      Environment/
      UI/
      FX/
    Audio/
      Music/
      SFX/
      Voice/
    Code/
      Core/                        <- engine-agnostic ya da temel
      Gameplay/
      UI/
      Editor/                      <- Editor only
    Data/                          <- ScriptableObject'ler
      Items/
      Quests/
      Characters/
    Prefabs/
      Characters/
      Environment/
      UI/
    Scenes/
      _Bootstrap.unity
      _Persistent.unity
      Levels/
    Settings/
      URP/
      Volume/
      Input/

  Plugins/                         <- 3rd party (Asset Store, DOTween, vb.)
  ThirdParty/                      <- alternatif isim
  StreamingAssets/                 <- runtime'da direkt path ile erişilen
```

**`_Project` underscore prefix'i**: Project window'da en üstte görünür, kendi kodunla Asset Store paketleri karışmasın.

### Naming Convention

**C# tipler**:
- `PascalCase` — class, struct, enum, method
- `camelCase` — local, parameter
- `_camelCase` — private field (style sheet kararı, ya `_x` ya `x`)
- `kPrefix` — const (`kMaxHealth`) — opsiyonel
- `s_static` — static field (opsiyonel)

**Asset'ler**:
- Prefab: `PascalCase` (`Enemy_Orc`, `UI_HUD_Healthbar`)
- ScriptableObject: `TypeName_Identifier` (`Item_HealthPotion`)
- Texture: `T_SubjectName_Variant` (`T_Stone_Diffuse`, `T_Stone_Normal`)
- Material: `M_SubjectName` (`M_Stone`)
- Sahne: `Level_01_Forest`, `Menu_Main`

**Klasör**: `PascalCase` veya `kebab-case` (ekibe göre, tutarlı kal)

### Modüler Mimari — Asmdef

```
Assets/_Project/Code/
  Core/
    Core.asmdef                    (Game.Core - hiçbir şeye refs yok)
  Data/
    Data.asmdef                    (Game.Data - refs Core)
  Gameplay/
    Gameplay.asmdef                (Game.Gameplay - refs Core, Data)
  UI/
    UI.asmdef                      (Game.UI - refs Core, Data)
  Editor/
    Editor.asmdef                  (Game.Editor - Editor platform only)
```

Kural: **lower modüller upper'ı bilmez**. UI Gameplay'i bilir, Gameplay UI'ı bilmez (event channel ile haberleşir).

### Addressables

`com.unity.addressables` — production-grade asset management.

**Setup**:
1. `Window > Asset Management > Addressables > Groups`
2. Asset'leri "Addressable" işaretle, group'lara böl
3. Build → "New Build > Default Build Script"

```csharp
// Async load + retain
var handle = Addressables.LoadAssetAsync<GameObject>("EnemyOrc");
GameObject enemy = await handle.Task;

// Instantiate (reference counted)
var op = Addressables.InstantiateAsync("EnemyOrc");
GameObject instance = await op.Task;

// Release (kritik!)
Addressables.ReleaseInstance(instance);
Addressables.Release(handle);
```

**Group strategy**:
- `LocalContent` — build'e bundle olarak gömülü
- `RemoteContent` — Cloud CDN'den çekilir (patching için)
- `Preload` — sahne yüklenmeden önce yüklenmesi gereken
- `OnDemand` — kullanılırken yüklenir, sonra unload

**Tuzak**: Addressables async API — sahne değişiminde handle'lar leak olabilir. Her `LoadAsync` için `Release` pair olmalı. Veya scoped helper class yaz.

### Build Pipeline & CI

**GitHub Actions ile Unity build** (game-ci/unity-builder action):
```yaml
name: Build Unity Project
on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        targetPlatform: [StandaloneWindows64, StandaloneOSX]
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true
      - uses: actions/cache@v4
        with:
          path: Library
          key: Library-${{ matrix.targetPlatform }}-${{ hashFiles('Assets/**', 'Packages/**', 'ProjectSettings/**') }}
      - uses: game-ci/unity-builder@v4
        env:
          UNITY_LICENSE: ${{ secrets.UNITY_LICENSE }}
        with:
          targetPlatform: ${{ matrix.targetPlatform }}
      - uses: actions/upload-artifact@v4
        with:
          name: Build-${{ matrix.targetPlatform }}
          path: build
```

### Platform-Specific Build

**Conditional compilation**:
```csharp
#if UNITY_EDITOR
    // Editor-only
#endif

#if UNITY_STANDALONE_WIN
    // Windows only
#endif

#if UNITY_IOS || UNITY_ANDROID
    // Mobile
#endif

#if !DEVELOPMENT_BUILD && !UNITY_EDITOR
    Debug.unityLogger.logEnabled = false;  // production'da log kapat
#endif
```

**IL2CPP & Stripping**:
- Mobile / console default IL2CPP
- Managed Stripping Level: High (aggressive, build küçük) → reflection'la çağrılan tip silinebilir → `link.xml` ile preserve
- `link.xml` örnek:
```xml
<linker>
  <assembly fullname="Newtonsoft.Json" preserve="all"/>
  <assembly fullname="Assembly-CSharp">
    <type fullname="Game.Save.SaveDataV3" preserve="all"/>
  </assembly>
</linker>
```

### Steam Integration

**Steamworks.NET** veya **Facepunch.Steamworks** (modern, daha kolay).

```csharp
using Steamworks;

void Awake()
{
    try
    {
        SteamClient.Init(123456);  // App ID
    }
    catch (Exception e)
    {
        Debug.LogWarning($"Steam init failed: {e.Message}");
    }
}

void OnApplicationQuit() => SteamClient.Shutdown();

// Achievement
public void UnlockAchievement(string id)
{
    var ach = new Achievement(id);
    if (!ach.State) { ach.Trigger(); SteamUserStats.StoreStats(); }
}
```

**Steam Cloud Auto**: Steamworks'te dosya pattern'i (`*.json`) tanımla, `persistentDataPath` otomatik sync. Manuel API gerekirse `SteamRemoteStorage`.

**Steam DRM** (DRM'siz piyasaya çıkmak da legitim seçenek; DRM ekleyeceksen build'i Steamworks'ün wrap tool'undan geçir).

### Project Hygiene Checklist

1. Force Text + Visible Meta açık
2. `.gitignore` + `.gitattributes` (LFS) doğru
3. Smart Merge configured
4. Klasör yapısı `_Project` altında
5. Asmdef ile modüler
6. Naming convention dokumante
7. Build script var, CI çalışıyor
8. README + onboarding doc (yeni dev nasıl başlar)
9. CHANGELOG tutuyor olmalı (semver)
10. Player Settings: bundle ID, version, splash screen, icon, scripting backend doğru

## Workflow

Workflow sorusu geldiğinde:

1. **Ekip büyüklüğü** — solo vs takım yaklaşım farklı
2. **Hedef platform listesi** — build pipeline ona göre kurulur
3. **Mevcut durum vs greenfield** — retrofit varsa migration plan, yoksa best practice doğrudan
4. **Concrete file ver** — `.gitignore`, `.gitattributes`, CI workflow YAML — kopya-yapıştır kullanılır halde

## References

- `references/unity-gitignore-gitattributes.md` — Full template + açıklamalar
- `references/asmdef-architecture.md` — Modüler proje için asmdef setup adım adım
- `references/github-actions-unity-ci.md` — Workflow YAML + secret setup + License acquire
- `references/steamworks-checklist.md` — Steam Store sayfasından oyuncu eline kadar adım adım
