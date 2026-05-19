# unitymcp — Full-Stack Unity 6 (URP) Agent

Claude'u Unity 6 LTS (URP) için profesyonel düzey bir geliştirme partneri ve öğretmene dönüştüren plugin. PC/Console 3D oyun geliştirme odaklı.

## Ne Sağlar?

### 8 Domain Skill

Claude bu konularda derinleşir — soru sorduğunda doğru skill otomatik aktif olur:

| Skill | Kapsam |
|---|---|
| `unity-csharp-architecture` | MonoBehaviour lifecycle, design pattern'ler, ScriptableObject mimarisi, event sistemi, Job System, asmdef |
| `unity-gameplay-systems` | New Input System, NavMesh, Cinemachine 3, fizik, animasyon, IK |
| `unity-data-saving` | JSON/Binary save, versioning, migration, encryption, async save, Steam Cloud |
| `unity-rendering-urp` | URP, HLSL, Shader Graph, Renderer Feature, post-process, Camera stacking |
| `unity-performance` | Profiler, GC alloc, draw call, batching, mobile optimization |
| `unity-ui` | uGUI + UI Toolkit, responsive, safe area, localization |
| `unity-editor-tooling` | Custom inspector, EditorWindow, AssetPostprocessor, build pipeline |
| `unity-workflow` | Git/LFS, asmdef mimari, CI/CD, Addressables, Steamworks |

### 3 Sub-Agent

İhtiyaç duyulduğunda otomatik veya manuel çağrılır:

- **shader-reviewer** — URP shader'ını SRP Batcher uyumu, variant patlama, mobile suitability açısından review eder
- **perf-auditor** — Kod veya Profiler verisi üzerinde performans audit yapar, P0/P1/P2 önceliklendirir
- **editor-tool-builder** — Editor automation tool'ları üretir (UI Toolkit ile EditorWindow)

### 4 Slash Command

- `/unity-new-system <isim>` — Yeni gameplay sistemi scaffold et (interface + MonoBehaviour + SO + event channel + test)
- `/unity-shader-from-spec <açıklama>` — Görsel efekt spec'inden URP shader üret (HLSL + Shader Graph)
- `/unity-review-mono <path>` — MonoBehaviour code review (mimari + performans + style)
- `/unity-explain <konu>` — Kavram → kod → tuzaklar → trade-off formatında öğretim

### Unity Editor MCP

`.mcp.json` — [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) entegrasyonu. Claude doğrudan Unity Editor'a komut gönderebilir: sahne okuma, GameObject oluşturma, component ekleme, asset modify.

## Kurulum

### 1. Plugin'i kur

Cowork'te `.plugin` dosyasını drag & drop yap, "Install" butonuna tıkla.

Veya manuel (Claude Code için):
```bash
mkdir -p ~/.claude/plugins
unzip unitymcp.plugin -d ~/.claude/plugins/unitymcp
```

### 2. Unity Editor MCP'yi bağla

**Unity tarafı**:
1. Unity Package Manager → "+" → "Add package from git URL"
2. URL: `https://github.com/CoplayDev/unity-mcp.git?path=/UnityMcpBridge`
3. Package import bitince: `Window > Unity MCP > Auto-configure Claude Code`

Auto-configure çalışmazsa, plugin'in içindeki `.mcp.json` zaten doğru config içeriyor — manuel kullanabilirsin. Önkoşul: `pip install uv` (uvx için).

### 3. Her Unity projende CLAUDE.md koy

Plugin içindeki `templates/CLAUDE.md.template` dosyasını proje köküne `CLAUDE.md` olarak kopyala, açıklamalı yerleri doldur.

## Kullanım

### Konuşma içinde

Claude'a sor:
- "Inventory sistemi nasıl SO event channel ile kurulur?"
- "Toon shader yazalım, fresnel rim glow olsun"
- "Bu MonoBehaviour'ı review et"
- "Save sisteminde V1'den V2'ye migration nasıl?"

İlgili skill otomatik açılır.

### Slash command ile

```
/unity-new-system Inventory
/unity-shader-from-spec dissolve effect with orange edge glow
/unity-review-mono Assets/_Project/Code/Gameplay/PlayerController.cs
/unity-explain Coroutine vs async UniTask
```

### Sub-agent ile

Claude büyük bir görev görürse otomatik delege eder. Manuel delege istersen:
- "Bu shader'ı shader-reviewer ile incele"
- "Tüm Gameplay klasörüne perf-auditor'u çalıştır"

## Dosya Yapısı

```
unitymcp/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── skills/
│   ├── unity-csharp-architecture/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── unity-gameplay-systems/
│   ├── unity-data-saving/
│   ├── unity-rendering-urp/
│   ├── unity-performance/
│   ├── unity-ui/
│   ├── unity-editor-tooling/
│   └── unity-workflow/
├── agents/
│   ├── shader-reviewer.md
│   ├── perf-auditor.md
│   └── editor-tool-builder.md
├── commands/
│   ├── unity-new-system.md
│   ├── unity-shader-from-spec.md
│   ├── unity-review-mono.md
│   └── unity-explain.md
├── templates/
│   └── CLAUDE.md.template
└── README.md
```

## Felsefe

Bu plugin Claude'u Unity konusunda hem **öğretmen** hem **çalışan partner** yapar:

- **Öğretmen** çünkü her cevap kavramsal → kod → tuzaklar → trade-off sırasıyla gelir
- **Partner** çünkü sub-agent'lar ve command'ler hazır iş üretir

Hedef: hobi tutorial seviyesinde değil, production studio seviyesinde tavsiye.

## Genişletme

Plugin'i kendi ihtiyaçlarına göre uyarla:

1. **Kendi konventionunu CLAUDE.md'ye yaz** — her proje için ayrı
2. **Yeni skill ekle** — `skills/<isim>/SKILL.md` (örn. `unity-multiplayer`, `unity-vfx-graph`)
3. **Sub-agent ekle** — `agents/<isim>.md`
4. **Slash command ekle** — `commands/<isim>.md`

Skill yazma rehberi için: Cowork → "skill-creator" skill'i kullan.

## Lisans

MIT. İçindeki kod örnekleri MIT lisansı ile kullanılabilir.

## Geri Bildirim

Bu plugin gelişmeye açık — sürekli kullandıkça eksik gördüğün yerleri ekle, fazla gelen yerleri sadeleştir.
