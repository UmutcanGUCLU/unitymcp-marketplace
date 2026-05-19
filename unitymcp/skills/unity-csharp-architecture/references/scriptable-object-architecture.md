# ScriptableObject Architecture — Pratik Rehber

Unity 6 LTS için SO mimari pattern'lerinin tam set'i. Bu Ryan Hipple ve Bob Nystrom'un yaklaşımlarının pratik özeti — kendi projende doğrudan kullanabilirsin.

## 1. Atomic Variables (Reactive Data)

Tek bir değişkeni SO olarak tut, hem designer ayarlayabilsin hem runtime'da reactive olsun:

```csharp
[CreateAssetMenu(menuName = "Atomic/Int Variable")]
public class IntVariable : ScriptableObject
{
    [SerializeField] int initial;
    int runtime;

    public event Action<int> OnChanged;

    public int Value
    {
        get => runtime;
        set { if (runtime != value) { runtime = value; OnChanged?.Invoke(value); } }
    }

    void OnEnable() => runtime = initial;
}
```

Kullanım:
- HealthSystem `playerHealth.Value -= damage`
- HealthBarUI `playerHealth.OnChanged += UpdateBar`
- İkisi birbirini hiç tanımıyor

**Tuzak — Editor state leak**: SO değerleri Editor'da persist eder. Play mode'da `Value`'yu değiştirirsen ve script `runtime` field'ı asset'e yazıyorsa, çıkışta değişiklik kalır. **Çözüm**: `runtime` field'ını `[NonSerialized]` işaretle veya yukarıdaki gibi `OnEnable`'da reset.

## 2. Event Channel

```csharp
[CreateAssetMenu(menuName = "Events/Void Event Channel")]
public class VoidEventChannel : ScriptableObject
{
    public event Action OnRaised;
    public void Raise() => OnRaised?.Invoke();
}

[CreateAssetMenu(menuName = "Events/Int Event Channel")]
public class IntEventChannel : ScriptableObject
{
    public event Action<int> OnRaised;
    public void Raise(int v) => OnRaised?.Invoke(v);
}

// Tip-spesifik daha fazla (Vector3, GameObject, string, custom struct...)
```

Listener tarafı:
```csharp
public class HealthBarUI : MonoBehaviour
{
    [SerializeField] IntEventChannel onPlayerDamaged;

    void OnEnable() => onPlayerDamaged.OnRaised += HandleDamage;
    void OnDisable() => onPlayerDamaged.OnRaised -= HandleDamage;

    void HandleDamage(int newHp) { /* UI güncelle */ }
}
```

Raiser tarafı:
```csharp
public class PlayerHealth : MonoBehaviour
{
    [SerializeField] IntEventChannel onPlayerDamaged;
    int hp = 100;

    public void TakeDamage(int amount)
    {
        hp -= amount;
        onPlayerDamaged.Raise(hp);
    }
}
```

## 3. Runtime Set

"Şu anda sahnede olan tüm enemy'ler" gibi dinamik liste:

```csharp
[CreateAssetMenu(menuName = "Sets/Enemy Runtime Set")]
public class EnemyRuntimeSet : ScriptableObject
{
    [NonSerialized] public readonly List<Enemy> items = new();

    public void Add(Enemy e) { if (!items.Contains(e)) items.Add(e); }
    public void Remove(Enemy e) => items.Remove(e);

    void OnEnable() => items.Clear();  // Editor state leak'i önle
}
```

```csharp
public class Enemy : MonoBehaviour
{
    [SerializeField] EnemyRuntimeSet enemySet;
    void OnEnable() => enemySet.Add(this);
    void OnDisable() => enemySet.Remove(this);
}
```

Kim isterse `enemySet.items`'a bakar — örn. MinimapUI tüm enemy ikonlarını çizer, AlertSystem yakındaki düşmanı detect eder.

## 4. Data Container

Item, character stat, dialogue node — pure data:

```csharp
[CreateAssetMenu(menuName = "Game/Items/Weapon")]
public class WeaponSO : ScriptableObject
{
    public string id;
    public string displayName;
    [TextArea] public string description;
    public Sprite icon;
    public int damage;
    public float attackSpeed;
    public WeaponType type;
}
```

**Designer flow**: Project'te right-click → Create → Game → Items → Weapon → asset düzenle. Kodda referans:
```csharp
[SerializeField] WeaponSO startWeapon;
```

## 5. Strategy / Behavior

Behavior'u SO'ya koy, polymorphic seç:

```csharp
public abstract class AIBehaviorSO : ScriptableObject
{
    public abstract void Execute(AIAgent agent);
}

[CreateAssetMenu(menuName = "AI/Patrol Behavior")]
public class PatrolBehaviorSO : AIBehaviorSO
{
    public float waypointWait = 2f;
    public override void Execute(AIAgent agent) { /* ... */ }
}

[CreateAssetMenu(menuName = "AI/Chase Behavior")]
public class ChaseBehaviorSO : AIBehaviorSO
{
    public float maxChaseDistance = 20f;
    public override void Execute(AIAgent agent) { /* ... */ }
}
```

Agent:
```csharp
public class AIAgent : MonoBehaviour
{
    [SerializeField] AIBehaviorSO currentBehavior;
    void Update() => currentBehavior.Execute(this);
}
```

## 6. Combine — Inventory Sistemi

Hep bir arada:

```
WeaponSO (Data)
EnemyRuntimeSet (Set)
IntEventChannel "OnPlayerDamaged" (Event)
IntVariable "PlayerGold" (Atomic)
```

InventorySystem MonoBehaviour `PlayerGold`'u günceller, GoldUI `PlayerGold.OnChanged`'i dinler, ShopSystem `PlayerGold.Value`'yu okur.

## Production Tuzakları

1. **Editor state leak** — `[NonSerialized]` veya `OnEnable` reset her zaman
2. **SO referansları için kim sahip**? — assignment Inspector'da, runtime'da yeni atama mümkün ama gerçekleşince re-subscribe gerekir
3. **Designer aboutness** — designer SO'yu yanlış set ederse silent bug. Min/max validation `[Min]`, `[Range]`, `OnValidate()` ile
4. **Domain reload kapalıysa** runtime state bir oturumdan diğerine taşır — `OnEnable` reset şart
5. **Çok fazla event channel** — gerçek decoupling değilse YAGNI; basit C# event yetiyorsa onu kullan

## Kaynak

- Ryan Hipple — "Unite Austin 2017 - Game Architecture with ScriptableObjects" (YouTube'da hala mevcut)
- Jason Storey — Atomic Variables yaklaşımı
- Unity Open Project — "Chop Chop" reposunda canlı örnek
