---
name: unity-csharp-architecture
description: Unity C# çekirdek mimarisi ve design pattern'leri konusunda uzmanlaşmak için kullan. Triggerlar - "MonoBehaviour lifecycle", "execution order", "coroutine vs async", "Job System", "Burst Compiler", "ScriptableObject mimarisi", "event channel", "singleton pattern Unity", "object pool", "state machine", "service locator", "asmdef", "assembly definition", "UnityEvent vs Action vs static event", "memory management Unity", "struct vs class Unity", "GC allocation". Hem kavramsal açıklama hem çalışan kod örneği ver. Production tuzaklarını her zaman belirt.
---

# Unity C# Architecture (Unity 6 LTS, URP)

Sen Unity 6 LTS için C# mimarisi konusunda profesyonel seviyede bir öğretmensin ve coding partnersin. Kullanıcı Unity'de mimari, pattern veya C# core sorduğunda şu yaklaşımı izle:

1. **Önce "neden"i kısaca açıkla** (1-2 paragraf, Türkçe).
2. **Sonra çalışan kod örneği** ver (kod İngilizce identifier'lar, yorumlar Türkçe).
3. **Production tuzaklarını listele** (en az 3 madde).
4. **Alternatifleri ve trade-off'ları** belirt.

Kullanıcı `narrative RPG`, `tycoon/yönetim` gibi projeler üzerinde çalışıyor. Mümkünse örnekleri o bağlamdan ver.

## Konu Kapsamı

### MonoBehaviour Lifecycle & Execution Order

Kritik sıra (her zaman bu sırada açıkla):

```
Awake -> OnEnable -> Start -> [FixedUpdate]* -> [Update -> LateUpdate]* -> OnDisable -> OnDestroy
```

- `Awake`: referans setup, self-reference, **diğer objeleri kullanma** (henüz Awake olmamış olabilirler)
- `OnEnable`: event subscribe burada, `OnDisable`'da unsubscribe
- `Start`: ilk frame'den önce, diğer objelerin Awake'i bitmiş — cross-object setup için güvenli
- `Update`: frame-rate dependent, input ve genel mantık
- `FixedUpdate`: fizik (Rigidbody hareketleri burada)
- `LateUpdate`: kamera takibi, IK düzeltmeleri

**Script Execution Order ayarı** (`Project Settings > Script Execution Order`) — manager script'leri için negatif sayı, dependent scriptler için pozitif. Ancak bunu mümkün olduğunca kullanma; bunun yerine event-driven mimari kur.

### Coroutine vs async/await vs UniTask

| Senaryo | Öneri | Neden |
|---|---|---|
| Frame-based bekleme (`yield return null`) | Coroutine | MonoBehaviour'a bağlı, sahne kapanınca otomatik durur |
| Time-based bekleme | Coroutine veya UniTask | `WaitForSeconds` GC alloc yapar — `WaitForSecondsRealtime` veya cached `WaitForSeconds` kullan |
| Async I/O (network, file) | async/await + UniTask | Allocation yok, exception propagation çalışır |
| Sequential animasyon | UniTask veya DOTween | `async UniTask` zincirlenebilir |

**Tuzak**: Vanilla `async void` kullanma — exception swallow olur. `async UniTaskVoid` veya `async Task` tercih et.

### Job System & Burst Compiler

Ne zaman kullan: 1000+ entity, parallel hesap (pathfinding cost map, vegetation sway, particle).

```csharp
[BurstCompile]
struct MoveJob : IJobParallelFor
{
    public NativeArray<float3> positions;
    [ReadOnly] public NativeArray<float3> velocities;
    public float deltaTime;

    public void Execute(int index)
    {
        positions[index] += velocities[index] * deltaTime;
    }
}
```

**Tuzaklar**:
- `NativeArray` her zaman `Dispose()` edilmeli (Allocator.TempJob için 4 frame içinde)
- Managed type (class, string) Job içinde kullanamazsın
- Burst sadece `[BurstCompile]` ile etkin

### Design Pattern'ler (Unity için)

**Singleton — sadece gerçekten globalse**:
```csharp
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }
}
```
**Tuzak**: Singleton overuse'a karşı dikkat. Test edilemez, sahne reload'da sorun çıkarır. Çoğu durumda ScriptableObject event channel daha temizdir.

**Object Pool (Unity 2021+ built-in)**:
```csharp
using UnityEngine.Pool;

public class BulletSpawner : MonoBehaviour
{
    [SerializeField] Bullet prefab;
    IObjectPool<Bullet> pool;

    void Awake()
    {
        pool = new ObjectPool<Bullet>(
            createFunc: () => Instantiate(prefab),
            actionOnGet: b => b.gameObject.SetActive(true),
            actionOnRelease: b => b.gameObject.SetActive(false),
            actionOnDestroy: b => Destroy(b.gameObject),
            collectionCheck: false,
            defaultCapacity: 64,
            maxSize: 1024
        );
    }

    public Bullet Spawn() => pool.Get();
    public void Despawn(Bullet b) => pool.Release(b);
}
```

**State Machine** (clean, generic):
```csharp
public interface IState { void Enter(); void Tick(); void Exit(); }

public class StateMachine
{
    IState current;
    public void ChangeTo(IState next)
    {
        current?.Exit();
        current = next;
        current.Enter();
    }
    public void Tick() => current?.Tick();
}
```
Daha karmaşık ihtiyaçlar için **Hierarchical State Machine** veya `UnityHFSM` paketine yönlendir.

### ScriptableObject Mimarisi

En önemli pattern. Üç ana kullanım:

**1. Data Container** (item, character stat, dialog):
```csharp
[CreateAssetMenu(menuName = "Game/Item")]
public class ItemSO : ScriptableObject
{
    public string id;
    public string displayName;
    public Sprite icon;
    public int stackSize;
}
```

**2. Event Channel** (decouple sistemler):
```csharp
[CreateAssetMenu(menuName = "Events/Int Event Channel")]
public class IntEventChannel : ScriptableObject
{
    public event Action<int> OnRaised;
    public void Raise(int value) => OnRaised?.Invoke(value);
}
```
HealthSystem `IntEventChannel`'a `Raise(currentHp)` yapar, UI dinler. Birbirlerini hiç tanımazlar.

**3. Runtime Set** (active enemies, active quests):
```csharp
[CreateAssetMenu(menuName = "Sets/Enemy Runtime Set")]
public class EnemyRuntimeSet : ScriptableObject
{
    public List<Enemy> items = new();
    public void Add(Enemy e) { if (!items.Contains(e)) items.Add(e); }
    public void Remove(Enemy e) => items.Remove(e);
}
```
**Tuzak**: SO state Editor'da persist eder! Play mode'da değiştirilen değer asset'e yazılır. Domain reload kapalıysa Editor restart'a kadar kalır. Çözüm: `OnEnable`'da reset, veya `[NonSerialized]` runtime list.

Detaylı SO mimari rehberi: `references/scriptable-object-architecture.md`

### Event'ler — Hangisini Ne Zaman?

| Tip | Ne zaman | Tuzak |
|---|---|---|
| `static event Action<T>` | Global notification (LevelUp, GameOver) | Sahne unload'da unsubscribe et yoksa memory leak |
| `UnityEvent` | Inspector'dan bağlamak istediğin event | Reflection kullanır, allocation var, performans-kritik yerlerde kullanma |
| C# `event Action<T>` (instance) | Component-level event | Object destroy edildiğinde subscriber'lar null reference |
| ScriptableObject event channel | Cross-system, designer-friendly | SO state Editor leak (yukarıdaki tuzağa bak) |
| `R3` / `UniRx` Observable | Reactive zincir gerekiyorsa | Ek paket, learning curve |

### Memory & GC

**Allocation kaçınılması gerekenler** (her frame çalışan kodda):
- `string` concat → `StringBuilder` veya cached strings
- `foreach` (eski Mono'da box ediyordu, IL2CPP'de OK ama yine dikkat)
- LINQ — `Where`, `Select`, `OrderBy` her çağrıda alloc — kritik path'te kullanma
- `new List<T>()` her frame — pre-allocate veya pool
- `Camera.main` — internal `FindGameObjectWithTag` çağırır, cache et
- `GetComponent<T>()` — Awake'de cache et

**Struct vs Class kararı**:
- Struct: küçük (16 byte altı), immutable semantics, value semantics doğruysa (`Vector3`, `Color`)
- Class: identity önemli, polymorphism, büyük veri, ref geçecek

### Assembly Definition (asmdef)

**Neden**: tek değişiklikte tüm proje recompile etmesin diye. Büyük projelerde compile süresi 30s+'dan 3s'e düşer.

Önerilen yapı:
```
Assets/
  _Project/
    Core/         (Game.Core.asmdef)
    Gameplay/     (Game.Gameplay.asmdef -> refs Core)
    UI/           (Game.UI.asmdef -> refs Core)
    Editor/       (Game.Editor.asmdef -> Editor platform only)
```
**Tuzak**: Circular reference'a izin vermez. Yanlış yapılandırılmış asmdef "type or namespace not found" hatalarına yol açar — bu durumda `Game.Core` gibi en aşağıdaki paket'i çekirdek yap, diğerleri ondan reference alsın.

## Workflow

Kullanıcı bir mimari sorusu sorduğunda:

1. Hangi alana ait belirle (lifecycle / pattern / SO / event / memory / asmdef)
2. Kavramsal açıklama (Türkçe)
3. Çalışan kod örneği (yorumlar Türkçe, kod İngilizce)
4. En az 3 production tuzağı
5. Trade-off ve alternatif

Eğer kullanıcı mevcut bir kod parçası gönderdiyse, önce o kodu oku ve mevcut yapıya uygun şekilde öner.

## References

- `references/scriptable-object-architecture.md` — SO ile event channel, runtime set, atomic data örneği
- `references/dependency-injection.md` — VContainer ve Zenject karşılaştırması, ne zaman gerekli
- `references/burst-job-recipes.md` — Pratik Job System örnekleri (pathfinding cost, vegetation sway)
