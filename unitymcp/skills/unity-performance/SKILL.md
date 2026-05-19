---
name: unity-performance
description: Unity performans, profiling, optimization, draw call batching, GC azaltma ve memory yönetimi konularında uzmanlaşmak için kullan. Triggerlar - "performans", "optimization", "profiler", "frame debugger", "memory profiler", "GC alloc", "garbage collection", "draw call", "batching", "SRP batcher", "GPU instancing", "static batching", "dynamic batching", "LOD", "occlusion culling", "FPS düşük", "stutter", "frame spike", "mobile performance", "build size". Önce profile et, sonra optimize et — premature optimization'a karşı uyar.
---

# Unity Performance & Optimization (Unity 6 LTS, URP)

Sen Unity performans uzmanısın. **Altın kural**: Her zaman önce profile et, sonra optimize et. Tahminle optimize etme — Unity Profiler ne diyorsa o.

## Konu Kapsamı

### Profiling — Ne Zaman Hangi Tool?

| Tool | Ne Görür | Ne Zaman |
|---|---|---|
| Unity Profiler | CPU, GPU, memory, audio, physics timeline | Genel performans audit, frame spike sebebi |
| Frame Debugger | Her draw call'ın detayı, batching neden bozuluyor | Render bottleneck şüphesi, batching debug |
| Memory Profiler (package) | Heap snapshot, leak detection | Memory growth, sandbox limit aşan platformlar |
| Deep Profile | Her method call profile'da görünür | Pinpoint root cause (NORMAL kapatılır, çok pahalı) |
| Performance Testing API | Otomatik regression test | CI'da performance regression catch |
| `Profiler.BeginSample("...")` | Kendi kod bloklarını işaretle | Spesifik fonksiyon time'ı |

**Build üzerinde profile** — Editor profiler yanıltıcı olabilir. Development Build + Autoconnect Profiler ile gerçek runtime'a bak.

### CPU Bottleneck — Yaygın Sebepler

**1. `Update` / `LateUpdate` patlamaları**
- 1000+ MonoBehaviour `Update`'i her frame çağırılır. Çözüm: **manager pattern** — bir manager script Update'te tüm "tickable" objeleri tickler
```csharp
public class TickManager : MonoBehaviour
{
    static readonly List<ITickable> tickables = new();
    public static void Register(ITickable t) => tickables.Add(t);
    public static void Unregister(ITickable t) => tickables.Remove(t);

    void Update()
    {
        for (int i = 0; i < tickables.Count; i++) tickables[i].Tick();
    }
}
```

**2. `GetComponent<T>` / `FindObjectOfType` hot path'te**
- Awake'de cache et, runtime'da tekrar arama yapma
- `Camera.main` aynı (internal `FindGameObjectWithTag`)

**3. String alloc'ları**
- `Debug.Log($"Score: {score}")` her frame → GC çöp. Conditional compilation veya `#if UNITY_EDITOR`
- `Animator.SetTrigger("Jump")` her frame → string lookup. `Animator.StringToHash` cache et

**4. LINQ**
- `enemies.Where(e => e.Hp > 0).OrderBy(e => e.Distance).First()` her frame → onlarca alloc
- Hot path'te elle döngü yaz, soğuk path'te LINQ tamam

**5. `foreach` Unity Mono 2018 öncesi enum boxing** — IL2CPP'de OK, ama yine de `for` daha hızlı array'lerde

### GC (Garbage Collection)

**Hedef**: Hot path'te 0 byte alloc. Profiler "GC Alloc" sütununa bak.

**Yaygın alloc kaynakları**:
- `new` (her tip) — heap alloc, struct hariç
- String concat → `StringBuilder` + `Clear()` reuse
- `List<T>.Add` capacity aşarsa array realloc → pre-size `new List<T>(64)`
- Lambda closures — local'ı capture eden lambda alloc yapar → static method veya cache delegate
- `params object[]` — vararg her çağrıda array alloc

**Incremental GC** (Unity 2019+): GC pause'u küçük parçalara böler — Player Settings > Other Settings'te aç. Mobile'da kritik.

### GPU Bottleneck — Draw Calls & Fill Rate

**Draw call azaltma teknikleri**:

| Teknik | Ne Zaman | Limitasyonlar |
|---|---|---|
| **SRP Batcher** | URP/HDRP, shader uyumlu | Material property layout `UnityPerMaterial` CBUFFER'da olmalı |
| **GPU Instancing** | Aynı mesh+material, farklı transform | Material'de "Enable GPU Instancing", shader `multi_compile_instancing` |
| **Static Batching** | Hareketsiz mesh'ler, aynı material | Player Settings > Static Batching açık; GameObject "Static" işaretli |
| **Dynamic Batching** | <900 vertex küçük mesh | URP'de devre dışı, fayda az |

**Frame Debugger'da batching neden bozuldu görme**: tıkladığın draw'ın yanında "Why this draw call cannot be batched with the previous one" yazısı çıkar.

**Overdraw azaltma**:
- Transparent shader'ları minimize et
- `Camera > Render > Allow MSAA = false` (mobile'da MSAA pahalı)
- UI Canvas'larda `Raycast Target` gereksiz ise kapat

**Fill rate (mobile)**:
- Resolution scaling — `XRSettings.eyeTextureResolutionScale` veya URP Asset'te Render Scale
- Post-process minimize — bloom, depth-of-field mobile'da pahalı

### LOD (Level of Detail)

```
LOD Group component:
  LOD0: Original mesh (>50% screen)
  LOD1: 50% triangles (25-50%)
  LOD2: 25% triangles (10-25%)
  Culled (<10%)
```

**Tuzak**: LOD geçişleri "popping" yapar — Crossfade Animation Mode aç. Veya Imposter (billboard) kullan uzak nesneler için.

### Occlusion Culling

Statik geometry için: `Window > Rendering > Occlusion Culling > Bake`. Sahnede gizlenen objeler render edilmez.

**Tuzaklar**:
- Sadece `Static` işaretli mesh'ler için çalışır
- Procedural level'larda `OcclusionPortal` veya gerek yok (open world'de fayda az)
- Bake süresi büyük sahnelerde dakikalar sürer

### Memory Optimization

**Texture**:
- En büyük memory hog. Max size düşür (4K → 2K mobile)
- Format: PC `BC7` (color), `BC5` (normal). Mobile `ASTC 6x6` veya `ASTC 8x8`
- Mip-maps aç (uzak texture daha küçük versiyonu kullanır → bandwidth ve cache friendly)
- Aniso level 0-2 mobil için yeterli

**Mesh**:
- Read/Write disable (CPU'da mesh data tutmaz, RAM tasarrufu)
- Compressed mesh data (Player Settings > Vertex Compression)

**Audio**:
- Music → Streaming (sıkıştırılmış halde diskte, decode runtime'da)
- Short SFX → Decompress On Load (instant playback)
- Vorbis quality 50-70 yeterli

### Addressables (memory + build size)

`com.unity.addressables` — referans-based asset yükleme, on-demand load/unload.

```csharp
var handle = Addressables.LoadAssetAsync<GameObject>("Enemy_Orc");
await handle.Task;
var instance = Instantiate(handle.Result);
// kullanım bitince:
Addressables.ReleaseInstance(instance);
Addressables.Release(handle);
```

**Build size azaltır** (kullanılmayan asset bundle build'e girmez), **memory verimli** (sahnede olmayan asset yükte değil), **patching** (yeni asset update'i ufak download).

**Tuzak**: Async API — herhangi bir yerde await'i unutursan handle leak olur. Reference counting'i dikkatli yönet.

### Mobile vs PC Strateji Farkı

| Konu | Mobile | PC |
|---|---|---|
| Hedef FPS | 30/60 | 60/120/144 |
| Resolution Scale | 0.5-0.8 | 1.0 |
| Shadow distance | 20-40m | 100m+ |
| Real-time light sayısı | 0-1 directional | 1 dir + N point/spot |
| Post-process | Sadece tonemapping + bloom düşük | Full stack |
| MSAA | Kapalı veya 2x | 2x-4x |
| URP Renderer | Forward (basit) | Forward+ veya Deferred |

### Build Size

- **Player Settings > Strip Engine Code** — kullanılmayan engine kod stripped
- **Managed Stripping Level: High** (IL2CPP) — sözde kullanılmayan ama reflection'la çağrılan kod silinebilir → `link.xml` ile preserve et
- **Texture Streaming** — Player Settings > Other Settings; çok büyük texture sahne yüklenmesini patlatmaz
- **Build Report Tool** veya Build Profile (Unity 6) — neyin build'e ne kadar yer kapladığını gösterir

## Workflow

Performans sorusu geldiğinde:

1. **Önce profile** — "FPS düşük" yetmez, hangi bottleneck? CPU mu, GPU mu, memory mi?
2. **Hedef platform** — mobile vs PC tamamen farklı strateji
3. **Profiler ekran görüntüsü iste** veya Frame Debugger output'unu sor
4. **Tek bir change'i öner** ve etkisini ölç (bir seferde bir şey değiştir)
5. **Premature optimization'a karşı uyar** — "şimdi optimize et"e direnci kullanıcının gerçek dataya ihtiyacı varsa

## References

- `references/profiler-recipes.md` — Profile ekran görüntüsü okuma rehberi, common patterns
- `references/gc-allocation-cookbook.md` — Yaygın GC alloc kaynakları ve çözümler (LINQ-free filter, string-free animator parameter)
- `references/mobile-optimization-checklist.md` — Mobile-specific 30 maddelik checklist
