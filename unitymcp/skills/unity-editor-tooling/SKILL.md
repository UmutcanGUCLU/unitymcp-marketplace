---
name: unity-editor-tooling
description: Unity editor tool yazımı — custom inspector, PropertyDrawer, EditorWindow, gizmos, scene tools, asset processor, build automation konularında uzmanlaşmak için kullan. Triggerlar - "custom inspector", "CustomEditor", "PropertyDrawer", "PropertyAttribute", "EditorWindow", "OnSceneGUI", "Handles", "Gizmos", "OnDrawGizmos", "AssetPostprocessor", "AssetModificationProcessor", "MenuItem", "EditorPrefs", "Undo system", "SerializedObject", "SerializedProperty", "BuildPipeline", "PostBuildProcessor", "procedural generation tool", "editor automation". Editor scripting'in production-grade ipuçlarını ve yaygın hataları her zaman göster.
---

# Unity Editor Tooling (Unity 6 LTS)

Sen Unity Editor scripting uzmanısın. Custom tool yazımı en kritik production accelerator'lardan biri — manuel iş 10 dakika sürüyorsa, 1 saat tool yazıp gerisini 30 saniyeye indirmek **doğru** yatırım.

## Konu Kapsamı

### Klasör Yapısı

```
Assets/
  Editor/                   <- Editor-only kod buraya
    PlayerStatsEditor.cs
    LevelGenerator.cs
  _Project/
    Editor/                 <- Project-specific tool'lar
```

`Editor` adlı **herhangi bir klasör** Editor assembly'ye gider — build'e dahil edilmez. Veya `*.Editor.asmdef` ile platform `Editor only` işaretle.

### Custom Inspector

```csharp
using UnityEditor;
using UnityEngine;

[CustomEditor(typeof(PlayerStats))]
public class PlayerStatsEditor : Editor
{
    SerializedProperty hp, mana, level;

    void OnEnable()
    {
        hp = serializedObject.FindProperty("hp");
        mana = serializedObject.FindProperty("mana");
        level = serializedObject.FindProperty("level");
    }

    public override void OnInspectorGUI()
    {
        serializedObject.Update();

        EditorGUILayout.PropertyField(level);

        // Conditional field — sadece level >=10 ise mana göster
        if (level.intValue >= 10)
            EditorGUILayout.PropertyField(mana);

        EditorGUILayout.Slider(hp, 0, 100, "Hit Points");

        if (GUILayout.Button("Reset to default"))
        {
            Undo.RecordObject(target, "Reset Stats");
            ((PlayerStats)target).ResetToDefault();
            EditorUtility.SetDirty(target);
        }

        serializedObject.ApplyModifiedProperties();
    }
}
```

**Kritik kurallar**:
- **`serializedObject.Update()` + `ApplyModifiedProperties()` çifti** — yoksa değişiklikler kaydetmez
- **`Undo.RecordObject` + `EditorUtility.SetDirty`** — yoksa Ctrl+Z çalışmaz ve sahne "dirty" işaretlemez (kayıtsız değişiklik)
- **`SerializedProperty` üzerinden eriş** — `target.fieldName` yerine — multi-edit ve undo otomatik destek

### PropertyDrawer (yeniden kullanılabilir)

Belirli bir tip veya attribute için custom render. Her yerde otomatik çıkar.

```csharp
[CustomPropertyDrawer(typeof(MinMaxAttribute))]
public class MinMaxDrawer : PropertyDrawer
{
    public override void OnGUI(Rect r, SerializedProperty p, GUIContent label)
    {
        var attr = (MinMaxAttribute)attribute;
        var v = p.vector2Value;
        EditorGUI.MinMaxSlider(r, label, ref v.x, ref v.y, attr.min, attr.max);
        p.vector2Value = v;
    }
}

public class MinMaxAttribute : PropertyAttribute
{
    public float min, max;
    public MinMaxAttribute(float min, float max) { this.min = min; this.max = max; }
}

// Kullanım:
[MinMax(0, 100)] public Vector2 healthRange = new(20, 80);
```

### EditorWindow (panel/tool)

```csharp
public class LevelGenerator : EditorWindow
{
    string seed = "default";
    int width = 64;
    int height = 64;

    [MenuItem("Tools/Level Generator")]
    public static void Open() => GetWindow<LevelGenerator>("Level Gen");

    void OnGUI()
    {
        EditorGUILayout.LabelField("Settings", EditorStyles.boldLabel);
        seed = EditorGUILayout.TextField("Seed", seed);
        width = EditorGUILayout.IntSlider("Width", width, 8, 256);
        height = EditorGUILayout.IntSlider("Height", height, 8, 256);

        if (GUILayout.Button("Generate"))
            Generate();
    }

    void Generate()
    {
        var go = new GameObject($"Level_{seed}_{width}x{height}");
        Undo.RegisterCreatedObjectUndo(go, "Generate Level");
        // ... procedural gen
    }
}
```

**Modern alternatif — UI Toolkit ile EditorWindow** (önerilir):
```csharp
public class LevelGenerator : EditorWindow
{
    public VisualTreeAsset uxml;  // .uxml asset
    public StyleSheet uss;

    void CreateGUI()
    {
        uxml.CloneTree(rootVisualElement);
        rootVisualElement.styleSheets.Add(uss);

        rootVisualElement.Q<Button>("generate-btn").clicked += Generate;
    }
}
```

### Scene GUI & Handles

Sahnede interactive widget çizme (path editor, area selector):

```csharp
[CustomEditor(typeof(PatrolPath))]
public class PatrolPathEditor : Editor
{
    void OnSceneGUI()
    {
        var path = (PatrolPath)target;

        for (int i = 0; i < path.points.Count; i++)
        {
            EditorGUI.BeginChangeCheck();
            Vector3 newPos = Handles.PositionHandle(path.points[i], Quaternion.identity);
            if (EditorGUI.EndChangeCheck())
            {
                Undo.RecordObject(path, "Move Patrol Point");
                path.points[i] = newPos;
                EditorUtility.SetDirty(path);
            }

            if (i < path.points.Count - 1)
                Handles.DrawLine(path.points[i], path.points[i + 1]);
        }
    }
}
```

### Gizmos

```csharp
public class SpawnZone : MonoBehaviour
{
    public float radius = 5f;

    void OnDrawGizmos()
    {
        Gizmos.color = new Color(1, 0, 0, 0.3f);
        Gizmos.DrawSphere(transform.position, radius);
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(transform.position, radius);
    }
}
```

**Tuzak**: `Gizmos` her frame çağrılır — pahalı şey yapma (texture sampling, deep iteration). Sadece basit shape ve cache'li veri.

### AssetPostprocessor

Asset import'unda otomatik kural uygulama (texture import settings, model fix-up):

```csharp
public class TexturePostprocessor : AssetPostprocessor
{
    void OnPreprocessTexture()
    {
        var importer = (TextureImporter)assetImporter;

        if (assetPath.Contains("/UI/"))
        {
            importer.textureType = TextureImporterType.Sprite;
            importer.mipmapEnabled = false;
        }
        else if (assetPath.Contains("/Normals/"))
        {
            importer.textureType = TextureImporterType.NormalMap;
        }
    }

    static void OnPostprocessAllAssets(string[] imported, string[] deleted, string[] moved, string[] movedFrom)
    {
        foreach (var path in imported)
            if (path.EndsWith(".prefab"))
                ValidatePrefab(path);
    }
}
```

**Kullanım örnekleri**:
- Tüm UI texture'ların `Compression: None` olmasını garanti
- Modellerin auto-mesh-compression
- Naming convention violation'a Console warning

### Custom Build Pipeline

```csharp
public class BuildScript
{
    [MenuItem("Build/Build All Platforms")]
    static void BuildAll()
    {
        BuildPlayer(BuildTarget.StandaloneWindows64, "Builds/Win/Game.exe");
        BuildPlayer(BuildTarget.StandaloneOSX, "Builds/Mac/Game.app");
    }

    static void BuildPlayer(BuildTarget target, string path)
    {
        var opts = new BuildPlayerOptions
        {
            scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(),
            locationPathName = path,
            target = target,
            options = BuildOptions.None
        };
        BuildPipeline.BuildPlayer(opts);
    }
}

// CI'dan çağırmak için:
// Unity -batchmode -quit -projectPath . -executeMethod BuildScript.BuildAll
```

**Pre/Post build hooks**:
```csharp
public class MyBuildProcessor : IPreprocessBuildWithReport, IPostprocessBuildWithReport
{
    public int callbackOrder => 0;
    public void OnPreprocessBuild(BuildReport report) { /* bump version, generate code */ }
    public void OnPostprocessBuild(BuildReport report) { /* upload, sign, notarize */ }
}
```

### Undo System — Hatırla

Her destructive operation:
- `Undo.RegisterCompleteObjectUndo` — array içeriği değişecekse
- `Undo.RecordObject` — basit field değişikliği
- `Undo.RegisterCreatedObjectUndo` — yeni GameObject
- `Undo.DestroyObjectImmediate` — silme operasyonu
- `Undo.SetTransformParent` — parent değişikliği

Olmadan undo bozulur — kullanıcılarına işkence olur.

### Procedural Generation Tool (örnek)

Roguelike level generator EditorWindow:

```csharp
public class DungeonGenerator : EditorWindow
{
    public DungeonConfig config;

    [MenuItem("Tools/Dungeon Generator")]
    static void Open() => GetWindow<DungeonGenerator>();

    void OnGUI()
    {
        config = (DungeonConfig)EditorGUILayout.ObjectField("Config", config, typeof(DungeonConfig), false);
        if (config != null && GUILayout.Button("Generate"))
        {
            var dungeon = DungeonAlgorithm.Generate(config);
            CreateSceneFromDungeon(dungeon);
        }
    }

    void CreateSceneFromDungeon(DungeonData d)
    {
        var root = new GameObject("Generated_Dungeon");
        Undo.RegisterCreatedObjectUndo(root, "Generate Dungeon");
        // tile/room prefab instantiate
    }
}
```

### Editor Performance

- `OnInspectorGUI` her frame çalışır — pahalı operasyon `OnEnable`'da
- `repaintOnSceneChange` — sadece gerektiğinde repaint
- `SerializedProperty` cache — `OnEnable`'da `FindProperty`, runtime'da kullan

## Workflow

Editor tool sorusu geldiğinde:

1. **Custom inspector mı, PropertyDrawer mı, EditorWindow mı, AssetPostprocessor mı** netleştir
2. **Undo desteği gerekli mi** — neredeyse her zaman EVET
3. **UI Toolkit mi IMGUI mi** — yeni tool için UI Toolkit
4. **Editor-only assembly** — Editor folder ya da asmdef Editor platform
5. **Concrete example** — kullanıcının senaryosuna özel

## References

- `references/editor-window-uitoolkit.md` — UI Toolkit ile EditorWindow tam örnek (theme, dock, save state)
- `references/custom-inspector-cookbook.md` — Conditional fields, list editing, drag-drop, custom buttons
- `references/asset-postprocessor-recipes.md` — Texture, model, audio import otomasyonu
- `references/build-automation-ci.md` — Unity Cloud Build alternatifi, GitHub Actions, version bump
