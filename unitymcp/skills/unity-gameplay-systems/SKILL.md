---
name: unity-gameplay-systems
description: Unity gameplay sistemleri (Input System, NavMesh, Cinemachine, fizik, animasyon) konusunda uzmanlaşmak için kullan. Triggerlar - "new input system", "input action", "control scheme", "rebinding", "navmesh", "navmesh surface", "off-mesh link", "cinemachine virtual camera", "cinemachine 3", "kamera takibi", "rigidbody", "collision matrix", "raycast", "layer mask", "animator state machine", "blend tree", "animation rigging", "root motion", "IK". Her sistemi hem kavramsal hem örnek koduyla anlat. Production tuzakları zorunlu.
---

# Unity Gameplay Systems (Unity 6 LTS)

Sen Unity gameplay sistemleri uzmanısın. Bu skill aktive olduğunda kullanıcının sorduğu sistemi hem kavramsal olarak hem de çalışan kod örneğiyle anlat. Türkçe açıklama + İngilizce kod + Türkçe yorumlar.

## Konu Kapsamı

### New Input System

`com.unity.inputsystem` — Unity 6 LTS'de default. Eski `Input.GetKey` API'sini terk et.

**3 temel kavram**:
- **InputAction**: bir eylem ("Jump", "Move")
- **Binding**: o eyleme bağlı physical input ("Spacebar", "Gamepad/buttonSouth")
- **InputActionAsset**: tüm action'ları gruplayan asset (control scheme'ler ve action map'ler içerir)

**Önerilen kullanım — generated C# class**:
```csharp
public class PlayerController : MonoBehaviour, GameInput.IGameplayActions
{
    GameInput input;
    Vector2 moveInput;

    void Awake()
    {
        input = new GameInput();
        input.Gameplay.SetCallbacks(this);
    }

    void OnEnable() => input.Gameplay.Enable();
    void OnDisable() => input.Gameplay.Disable();

    public void OnMove(InputAction.CallbackContext ctx) => moveInput = ctx.ReadValue<Vector2>();
    public void OnJump(InputAction.CallbackContext ctx) { if (ctx.performed) Jump(); }

    void Jump() { /* ... */ }
}
```

**Rebinding** (kullanıcı tuş değiştirsin):
```csharp
public void StartRebinding(InputAction action, int bindingIndex)
{
    action.Disable();
    var op = action.PerformInteractiveRebinding(bindingIndex)
        .WithControlsExcluding("Mouse")
        .OnComplete(operation =>
        {
            action.Enable();
            SaveBindings(action);  // PlayerPrefs veya save file
            operation.Dispose();
        })
        .Start();
}
```

**Local multiplayer** — `PlayerInputManager` + `PlayerInput` component. Her oyuncu kendi `InputUser`'ına bağlanır, control scheme otomatik ayrılır.

**Tuzaklar**:
- UI elementleri input'u "consume" eder; `EventSystem` ve `InputSystemUIInputModule` gerekli
- `performed` callback yalnızca threshold'u geçince tetiklenir — analog input için `ReadValue` kullan
- Generated class file'ı manuel düzenleme — her zaman `.inputactions`'tan regen et

### NavMesh & NavMeshSurface

**Klasik vs Component-based**: Yeni projeler için her zaman `com.unity.ai.navigation` paketini kur — `NavMeshSurface` component'i runtime bake'i ve multiple surface'i destekler.

```csharp
[RequireComponent(typeof(NavMeshAgent))]
public class EnemyChase : MonoBehaviour
{
    [SerializeField] Transform target;
    NavMeshAgent agent;

    void Awake() => agent = GetComponent<NavMeshAgent>();

    void Update()
    {
        if (target == null) return;
        if (Time.frameCount % 10 == 0)  // path recalc'i seyrekleştir
            agent.SetDestination(target.position);
    }
}
```

**Off-mesh links** — yüksek platform atlama, ladder, jump pad:
```csharp
public class JumpLink : MonoBehaviour
{
    NavMeshAgent agent;
    void Update()
    {
        if (agent.isOnOffMeshLink)
        {
            // burada custom traversal animasyonu / coroutine ile zıplat
            StartCoroutine(TraverseLink());
        }
    }
}
```

**Runtime bake** (procedural level, açık dünya tile streaming):
```csharp
[SerializeField] NavMeshSurface surface;
public void RebuildNav() => surface.BuildNavMesh();
```

**Tuzaklar**:
- `SetDestination` her frame çağrılırsa CPU yer — interval kullan veya destination değişti mi kontrol et
- Agent radius / step height level scale'iyle uyuşmuyorsa agent takılır
- Static obstacle değişirse `NavMeshObstacle` (carve true) veya runtime rebake gerekli

### Cinemachine 3.x

Unity 6'da Cinemachine 3 default — namespace `Unity.Cinemachine`, component'ler `CinemachineCamera` (eski `CinemachineVirtualCamera`).

**3 ana pattern**:
1. **Follow + LookAt** — third-person karakter takibi
2. **State-Driven Camera** — Animator state'e göre kamera değişimi (dialogue, combat, exploration)
3. **Cinemachine Blend List** — sırayla yürüyen kamera (cutscene)

```csharp
public class CameraManager : MonoBehaviour
{
    [SerializeField] CinemachineCamera gameplayCam;
    [SerializeField] CinemachineCamera dialogueCam;

    public void EnterDialogue(Transform speaker)
    {
        dialogueCam.LookAt = speaker;
        dialogueCam.Priority = 20;  // yüksek priority -> aktif
        gameplayCam.Priority = 0;
    }
}
```

**Procedural noise** (hand-held effect, hasar shake):
```csharp
var noise = gameplayCam.GetComponent<CinemachineBasicMultiChannelPerlin>();
noise.AmplitudeGain = 2f;
noise.FrequencyGain = 5f;
// duration sonra 0'a dön
```

**Tuzak**: Cinemachine 3'te API tamamen değişti — eski tutoriallar `CinemachineVirtualCamera` referansı veriyor, bunu `CinemachineCamera`'ya çevir.

### Fizik (Rigidbody, Collision)

**Kural**: Rigidbody hareketi her zaman `FixedUpdate`'te ve `MovePosition`/`AddForce` ile. `transform.position` kullanma — fiziği bozar.

```csharp
public class PlayerMovement : MonoBehaviour
{
    Rigidbody rb;
    Vector2 input;

    void Awake() => rb = GetComponent<Rigidbody>();

    void Update() => input = inputAction.ReadValue<Vector2>();

    void FixedUpdate()
    {
        Vector3 move = new Vector3(input.x, 0, input.y) * speed * Time.fixedDeltaTime;
        rb.MovePosition(rb.position + move);
    }
}
```

**Collision Matrix** (`Project Settings > Physics > Layer Collision Matrix`):
- Player layer, Enemy layer, Projectile layer, Trigger layer ayrı tut
- Player <-> Player collision kapatılabilir (multiplayer'da pass-through için)
- Performance: gereksiz collision'ları kapat — broad phase ucuzlar

**Raycast / Overlap optimizasyonu**:
- `Physics.RaycastNonAlloc` veya `Physics.OverlapSphereNonAlloc` kullan — allocation yok
- `LayerMask` parametresini her zaman ver — gereksiz collider'ları filtrele
- `QueryTriggerInteraction.Ignore` trigger'ları görmezse hızlanır

```csharp
RaycastHit[] hits = new RaycastHit[16];
int count = Physics.RaycastNonAlloc(origin, dir, hits, maxDist, enemyMask);
for (int i = 0; i < count; i++) { /* hits[i] */ }
```

### Animasyon

**Animator State Machine**:
- State'leri **mantıksal** grupla (Locomotion, Combat, Reactions sub-state machines)
- Transition condition'larını parameter-driven yap (Trigger, Bool, Float)
- `Has Exit Time` — istisnai durum dışında kapat (loop'lu state için açık)

**Blend Tree**:
- 1D: walk/run blend
- 2D Directional: 8-yön strafe (Free Form Directional)
- 2D Cartesian: aim offset

**Animation Rigging** (procedural animation):
```csharp
// Aim constraint runtime'da set edilir
[SerializeField] MultiAimConstraint headAim;

void LateUpdate()
{
    headAim.data.sourceObjects = new WeightedTransformArray()
    {
        new WeightedTransform(targetTransform, 1f)
    };
}
```

**Root Motion**:
- Açık tut: animasyondan gelen hareket geçerli (kombo animasyon, custom traversal)
- Kapalı tut: kod hareketi kontrol ediyor (FPS, top-down)

**Tuzaklar**:
- Animator parameter string'leri `Animator.StringToHash("Speed")` ile cache et
- `Animator.SetTrigger` reset edilmek isteniyorsa `ResetTrigger` çağır
- Layer weight blend'i `LateUpdate`'te değiştir, yoksa transition glitch olur

### IK (Inverse Kinematics)

Animation Rigging paketi (`com.unity.animation.rigging`) — Two Bone IK, Multi-Aim, Twist Correction, Damped Transform.

Foot IK (terrain'e ayak hizalama):
```csharp
[SerializeField] TwoBoneIKConstraint leftFootIK;
[SerializeField] Transform leftFootTarget;

void LateUpdate()
{
    if (Physics.Raycast(leftFootTarget.position + Vector3.up, Vector3.down, out var hit, 1f, groundMask))
    {
        leftFootTarget.position = hit.point + Vector3.up * 0.1f;
        leftFootTarget.rotation = Quaternion.FromToRotation(Vector3.up, hit.normal) * transform.rotation;
    }
}
```

## Workflow

Kullanıcı bir gameplay sistemi sorduğunda:

1. Hangi sistem (input / nav / camera / physics / animation / ik) belirle
2. Bağlamı sor: solo mu multiplayer mı, 3D mü 2D mi, hangi karakter tipi
3. Kavramsal açıklama → kod örneği → tuzaklar
4. Performans implikasyonlarını mutlaka belirt (özellikle nav ve physics için)
5. Mevcut Unity 6 LTS API'sini kullan (eski API'leri "deprecated" olarak işaretle)

## References

- `references/input-system-recipes.md` — Rebinding kaydetme, action map switching, gamepad/keyboard schemes
- `references/cinemachine-3-cookbook.md` — State-driven camera, dolly track, custom extensions
- `references/animation-rigging-patterns.md` — Foot IK, aim IK, look-at, procedural hand placement
