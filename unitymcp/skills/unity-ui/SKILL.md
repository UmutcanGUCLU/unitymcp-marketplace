---
name: unity-ui
description: Unity UI (uGUI ve UI Toolkit), responsive layout, anchor/pivot, canvas optimization, localization konularında uzmanlaşmak için kullan. Triggerlar - "uGUI", "Canvas", "anchor", "pivot", "RectTransform", "Layout Group", "Content Size Fitter", "UI Toolkit", "UXML", "USS", "UI Builder", "responsive UI", "safe area", "localization", "Unity Localization package", "TextMeshPro", "TMP", "UI optimization", "canvas rebuild", "raycast target". Hangi sistemi ne zaman seçmeli — uGUI vs UI Toolkit karar yardımı her zaman ver.
---

# Unity UI — uGUI & UI Toolkit (Unity 6 LTS)

Sen Unity UI uzmanısın. Her UI sorusunda önce **uGUI mı UI Toolkit mi** netleştir, çünkü yaklaşım tamamen farklı.

## Konu Kapsamı

### uGUI vs UI Toolkit — Karar Matrisi

| Senaryo | Öneri | Sebep |
|---|---|---|
| World-space UI (3D dünyada billboard) | uGUI | UI Toolkit world-space desteklemiyor (Unity 6'da hala) |
| HUD, in-game UI (oyun içi) | uGUI | Olgun, gameplay-coupled component'ler kolay |
| Menüler, settings, runtime tool | UI Toolkit | Daha hızlı, retained mode, USS ile theme |
| Editor tool / EditorWindow | UI Toolkit | Editor için zaten standart, IMGUI'den daha iyi |
| Çok dinamik liste (1000+ entry) | UI Toolkit `ListView` | Virtualization built-in |
| Designer-friendly, ekip içinde non-coder | uGUI veya UI Builder | uGUI scene-based daha tanıdık |
| Mevcut proje uGUI'de | uGUI'de kal | Karma sistem maintenance pahalı |

### uGUI — Anchor & Pivot Mantığı

**Yanlış anlaşılan iki şey**:
- **Anchor**: parent'ın hangi noktasına "yapıştığını" belirtir. Min ve Max ayrı set edilirse stretch eder.
- **Pivot**: kendi rotation/scale merkezi.

**Responsive desenler**:
- Tam ekran panel: Anchor min(0,0) max(1,1), offset 0 — parent'a stretch
- Sağ üst köşede ikon: Anchor min(1,1) max(1,1), pivot (1,1), positionX -10 positionY -10
- Üst bar (tam genişlik, sabit yükseklik): Anchor min(0,1) max(1,1), pivot (0.5, 1), sizeDelta(0, 60)

**Layout Group + ContentSizeFitter**:
- VerticalLayoutGroup içinde dinamik liste → ContentSizeFitter (Vertical Fit: Preferred Size) ile parent büyür
- **Tuzak**: nested Layout Group'lar her frame "dirty" işaretler — `Layout.LayoutRebuilder.ForceRebuildLayoutImmediate` performans yer. Statik layout'lar için layout group runtime'da disable et.

### Canvas Optimization

**1 Canvas = 1 batched mesh**. Tek bir element değişirse Canvas tamamen yeniden bake edilir.

**Strateji**:
- Statik UI'yi ayrı Canvas'a koy (HUD background, frame, decorative)
- Dinamik UI'yi ayrı Canvas'a koy (health bar, score, animasyon)
- Canvas'ı UI element grupları için **alt Canvas** olarak nest etme (parent canvas rebuild olmaz)

**Raycast Target**:
- Default'ta tüm Image/Text raycast target — gereksizleri **kapat**
- 1000 element olan HUD'de raycast cost CPU'da görünür
- "UI Element non-raycast" tool ile batch off

**TextMeshPro vs eski Text**:
- **Always use TextMeshPro** — yeni Text yapmıyoruz
- SDF font crisp, atlas oluştur, dynamic atlas Unicode (CJK için) destekli

### UI Toolkit — Temel Kavramlar

**3 dosya tipi**:
- `.uxml` — yapı (HTML benzeri)
- `.uss` — stil (CSS benzeri)
- C# script — behavior

**Minimal örnek**:

`MainMenu.uxml`:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <ui:VisualElement class="root">
        <ui:Label text="Game Title" class="title"/>
        <ui:Button name="play-btn" text="Play"/>
        <ui:Button name="settings-btn" text="Settings"/>
        <ui:Button name="quit-btn" text="Quit"/>
    </ui:VisualElement>
</ui:UXML>
```

`MainMenu.uss`:
```css
.root {
    flex-direction: column;
    align-items: center;
    padding: 40px;
    background-color: rgba(0, 0, 0, 0.8);
}

.title {
    font-size: 48px;
    color: rgb(255, 215, 0);
    -unity-font-style: bold;
    margin-bottom: 20px;
}

Button {
    width: 200px;
    height: 50px;
    margin: 10px;
}

Button:hover {
    background-color: rgb(80, 80, 80);
}
```

`MainMenuController.cs`:
```csharp
[RequireComponent(typeof(UIDocument))]
public class MainMenuController : MonoBehaviour
{
    void OnEnable()
    {
        var root = GetComponent<UIDocument>().rootVisualElement;
        root.Q<Button>("play-btn").clicked += () => SceneManager.LoadScene("Game");
        root.Q<Button>("settings-btn").clicked += OpenSettings;
        root.Q<Button>("quit-btn").clicked += () => Application.Quit();
    }
}
```

**Veri binding** (Unity 6'da güçlendi):
```csharp
var binding = new DataBinding { dataSourcePath = new PropertyPath(nameof(playerScore)) };
scoreLabel.SetBinding("text", binding);
```

### Safe Area (notch, dynamic island)

```csharp
public class SafeAreaApplier : MonoBehaviour
{
    RectTransform panel;

    void Awake() => panel = GetComponent<RectTransform>();

    void Update()
    {
        Rect safe = Screen.safeArea;
        Vector2 min = safe.position;
        Vector2 max = safe.position + safe.size;
        min.x /= Screen.width;  min.y /= Screen.height;
        max.x /= Screen.width;  max.y /= Screen.height;
        panel.anchorMin = min;
        panel.anchorMax = max;
    }
}
```

**Tuzak**: `Screen.safeArea` orientation değişiminde geç güncellenir — `OnRectTransformDimensionsChange` event'ini de dinle.

### Localization

`com.unity.localization` paketi — kayboldu eski "i18n" yaklaşımları, bu zorunlu.

```csharp
LocalizationSettings.SelectedLocale = LocalizationSettings.AvailableLocales.GetLocale("tr");

// String table'dan çek
var loc = LocalizeStringEvent;  // component
loc.StringReference.SetReference("UIStrings", "main_menu_play");
loc.StringReference.RefreshString();

// Dinamik argüman:
var smart = new LocalizedString("UIStrings", "player_score");
smart.Add("score", new IntVariable { Value = 1234 });
string display = smart.GetLocalizedString();  // "Skorun: 1234"
```

**Tuzaklar**:
- Smart String format (`{score}`) için Smart Format açık olmalı (String Table asset'inde)
- Asset Table — texture, audio, sprite localize için. Resmi tutuyorsan Texture Table.
- Font fallback — CJK desteği için dinamik atlas + font asset fallback chain.

### Responsive Design

**Reference resolution** (Canvas Scaler):
- 1920×1080 — PC default
- 1080×1920 — mobile portrait
- Match: 0.5 — orta yol, hem genişlik hem yükseklik scale eder
- Match: 1.0 — sadece yükseklik (mobile portrait için)

**Aspect ratio variation handling**:
- `AspectRatioFitter` — image'ın aspect'i sabit kalır, parent boyutuna uyar
- Manuel listener — `Screen.width / Screen.height` >= 2.0 ise ultra-wide layout

### UI Optimization Checklist

1. Statik ve dinamik UI ayrı Canvas
2. Raycast Target gereksizleri kapat
3. TextMeshPro her zaman (UI Text deprecated)
4. Mask yerine RectMask2D (daha ucuz)
5. Sprite Atlas kullan (draw call azalır)
6. Sürekli aktive/deaktive olan UI yerine `gameObject.SetActive` yerine alpha 0 (rebuild önler) — ama görünmeyenler raycast almalı, raycast target off
7. `ScrollRect` çok element içinde recyclable list kullan (örn. Tactical UI Pool veya Unity'nin yeni `LoopScrollRect`'i)
8. Hot path string format'tan kaçın

## Workflow

UI sorusu geldiğinde:

1. **uGUI mi UI Toolkit mi** — eğer söylemiyorsa sor
2. **World-space mi screen-space mi** belirle
3. **Hedef platform** — mobile portrait, PC landscape, console?
4. **Localization gerekli mi** — başlangıçtan kurmak sonra retrofit'ten 10x kolay
5. **Code example + visual hierarchy ASCII** (komplex layout için) ver

## References

- `references/ui-toolkit-vs-ugui.md` — Detaylı karar matrisi ve migration notları
- `references/canvas-optimization-deep-dive.md` — Profile + fix recipe'leri
- `references/localization-setup-guide.md` — Sıfırdan kurulum, smart format, asset table
