# Unity Profiler — Pratik Tarifler

Profiler'ı açtın, ne göreceksin, hangi pattern hangi soruna işaret? Bu dokümantasyon SOMUT pattern'leri ve düzeltmelerini listeler.

## Profiler Açma

`Window > Analysis > Profiler` (Ctrl+7)

**Önemli ayarlar**:
- **Deep Profile**: Off normalde. Detaylı drill-down için kısa süreliğine aç, sonra kapat — çok pahalı, kendi başına oyunu yavaşlatır
- **Profile Editor**: Sadece editor performans debug ediyorsan
- **Autoconnect Profiler**: Build için aç, otomatik connect

**Build üzerinde profile** (gerçek sayılar):
1. Build Settings → Development Build + Autoconnect Profiler aç
2. Build çıkar, koş
3. Profiler "Connect" menüsünden çalışan build'i seç

## Module Module — Ne Anlıyor?

### CPU Usage
- **PlayerLoop**: ana frame loop. İçinde scripts, physics, rendering, animation, vb.
- **Yellow bar > 16.67ms** (60fps hedefi için) → frame drop
- **Red flame**: GC.Collect tetiklendi → GC spike

**Hierarchy view**:
- Most expensive method'ları gör
- `GC Alloc` sütunu — frame başına kaç byte ayrıldı
- `Time ms` — bu sample'ın kendi maliyeti (children dahil değil)
- `Total ms` — kendi + children
- `Calls` — kaç kez çağrıldı (1000+ ise hot path)

### GPU Usage
- Forward+, Deferred için ayrı kategoriler
- Shadow, Lighting, Post-Process ayrı dilimler
- "Render.OpaqueGeometry" çok pahalıysa → draw call veya shader cost
- Frame Debugger'a geç

### Memory
- Total Reserved: Unity'nin allocate ettiği toplam RAM
- Mono Heap: managed heap (C# objects)
- GFX Driver: GPU resource (textures, mesh on VRAM)
- Audio: ses memory
- Profiler.GetTotalAllocatedMemoryLong(): runtime'da kontrol

### Audio
- Voice count
- DSP load (gerçek zamanlı efekt cost'u)

### Physics
- Active rigidbodies
- Collisions per frame
- Solver iterations

### UI
- Canvas rebuild count (UI optimization'da kritik)
- Batches (draw call benzeri)

## Yaygın Pattern'ler ve Çözümleri

### Pattern 1: "GC.Collect" her birkaç saniyede bir, hatırı sayılır spike

**Sebep**: Hot path'te alloc → heap dolu → collect.

**Bulma**: CPU Usage → Hierarchy → GC Alloc sütununa göre sırala → en üsttekileri incele.

**Çözüm prioritesi**:
1. String operations → StringBuilder cache veya hash
2. LINQ → manual loop
3. `new Vector3/Color/etc.` her frame → struct OK (stack), ama emin değilsen Profiler'a sor
4. Closure lambdas → static delegate veya stored Action

**Geçici fix** (production önerilmez): Incremental GC. Player Settings → Other Settings → "Use incremental GC". Spike'ı küçük parçalara böler.

### Pattern 2: Update'lerin "Behaviour.Update" toplamı 5ms+

**Sebep**: Çok sayıda script Update implement ediyor, her birinin overhead'i.

**Bulma**: Profiler → CPU → Hierarchy → "BehaviourUpdate" ara. Altında her script ayrı sample olarak görünür.

**Çözüm**:
- Tickable interface + tek manager Update (yukarıdaki performance SKILL'de örnek var)
- Veya ECS'e geç (DOTS) — overkill çoğu proje için
- Veya Update'i kaldır, event-driven yap

### Pattern 3: Draw Calls çok yüksek (URP'de >2000)

**Bulma**: Frame Debugger (Window > Analysis > Frame Debugger). Her draw call'a tıkla, neden batch'lenmediğini gör.

**Yaygın sebepler**:
- Material farklı (instance) → instancing aç veya MaterialPropertyBlock
- SRP Batcher uyumsuz shader → CBUFFER düzelt
- Dynamic batching limitleri (URP'de fayda az)
- UI Canvas çok parçalı

**Çözüm**:
- Static GameObject'leri Static Batching için işaretle
- Aynı mesh → GPU instancing
- Shader → SRP Batcher uyumlu (CBUFFER doğru)
- UI Canvas — statik/dinamik ayrı

### Pattern 4: Memory sürekli artıyor (leak şüphesi)

**Bulma**: Memory Profiler package'ını kur. Snapshot al, oyna, başka snapshot al, "Diff View" ile karşılaştır.

**Yaygın leak'ler**:
- Subscription unsubscribe edilmemiş (static event'lerde özellikle)
- `Texture2D` runtime'da `new` ile yaratılıp `Destroy` edilmemiş
- `RenderTexture` `Release` edilmemiş
- Addressables `Release` çağrısı eksik
- `List<T>` referansları sürekli büyüyor

### Pattern 5: Frame Spike — düzenli olmayan, ara sıra büyük spike

**Bulma**: Profiler timeline'da spike'a click → o frame'in hierarchy'sini incele.

**Yaygın sebepler**:
- Asset on-demand load (`Resources.Load` veya Addressables sync load)
- Sahnede yüklenen prefab instantiate spike
- Async operation main thread'e dönerken çakışma
- GC.Collect (yukarıdaki pattern 1)

**Çözüm**:
- Pre-load asset'ler, sahne yüklenirken
- Object pooling
- Async load instead of sync

### Pattern 6: Mobile'da overheat, frame rate dalgalanması

**Sebep**: Throttling — telefon ısınınca CPU/GPU klock düşer.

**Bulma**: Profiler GPU module → her frame ne kadar GPU time? Mobile target'ta 16.6ms (60fps) için maksimum ~12ms GPU.

**Çözüm**:
- Application.targetFrameRate = 30 (60'a hedeflenmiyorsa)
- QualitySettings.vSyncCount = 1
- Resolution scale düşür (URP Asset'te)
- Shadow distance + cascade azalt
- Post-process azalt veya kaldır

## Profile İçin Hazır Workflow

1. Build çıkar (Development), profiler bağla
2. 1-2 dakika oyna, "normal" durumu gözle, baseline al
3. Spike olduğunda durdur, o frame'i incele
4. Hipotez kur ("LINQ'i Update'te kullanıyorum, GC alloc yapıyor olabilir")
5. Tek bir change yap, tekrar profile
6. **Diff** — değişti mi? Ölçülebilir miktar?
7. Commit veya revert

**Genel kural**: Bir seferde sadece bir değişiklik yap, ölç. Aksi takdirde hangisinin etki ettiğini bilemezsin.

## Profiler.BeginSample — Kendi İşaretlerin

```csharp
using UnityEngine.Profiling;

void Update()
{
    Profiler.BeginSample("MyExpensiveCalculation");
    DoExpensiveWork();
    Profiler.EndSample();
}
```

Profiler hierarchy'sinde "MyExpensiveCalculation" görünür — kendi metodlarını kolayca işaretle. Development build'de kalır, release build'de strip edilir.
