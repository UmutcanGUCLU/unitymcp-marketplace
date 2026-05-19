---
description: Verilen MonoBehaviour / Unity C# dosyasını mimari, performans, naming convention, allocation, Unity 6 LTS API uyumu açısından review et. Sadece bulguları rapor et — kod değiştirme.
allowed-tools: Read, Grep, Glob
---

# /unity-review-mono $ARGUMENTS

Kullanıcı bir dosya path'i, dizin veya snippet verir. Hepsini systematik review et.

## Review Eksenleri

### Mimari
- MonoBehaviour vs ScriptableObject vs static class — doğru tip mi?
- Singleton overuse, Inspector'da olmayan dependency
- Tight coupling — başka sistemleri direkt referans alma
- Hidden state — initializer'sız field, default'a güveniyor

### Lifecycle Doğru Kullanımı
- `Awake` vs `Start` ayrımı doğru mu? (self setup Awake, cross-object Start)
- `OnEnable` / `OnDisable` event sub/unsub için kullanılmış mı?
- `OnDestroy` cleanup var mı? (subscription leak)

### Performance
- `Update`/`FixedUpdate`/`LateUpdate` doğru yerde mi?
- Hot path'te GC alloc kaynakları (LINQ, string, foreach boxing, new collection)
- `GetComponent`, `Camera.main`, `FindObjectOfType` Awake'de cache'lenmiş mi?
- `Animator.SetTrigger("name")` string lookup mu yoksa hash mi?
- `Coroutine` yerine `async UniTask` daha mı uygun?

### Null & Defensive Coding
- `null` check eksik, NRE açıkları
- `MissingReferenceException` riski (sahne unload sonrası referans)
- `[SerializeField]` private vs public ayrımı tutarlı mı?

### Unity 6 LTS API Uyumu
- Deprecated API kullanılmış mı? (`Input.GetKey` → New Input System, `CinemachineVirtualCamera` → `CinemachineCamera`)
- `WaitForSeconds` her frame `new` → cache veya UniTask
- `Resources.Load` → Addressables öner

### Style
- Naming convention: `PascalCase` type, `camelCase` local/param, `_camelCase` veya `m_` private (consistent kal)
- Magic number → const
- Method uzunluğu (50 satır üstü → refactor öner)
- Public field vs property — Inspector'da görünmesi gerekmiyorsa property

## Output

```
# Review: <dosya_adı>

## Genel Skor: <1-10>

## Kritik
1. <bulgu> @ line N — <neden critic> — <önerilen yaklaşım>

## Önemli
1. ...

## Minor / Style
1. ...

## Pozitifler
- <iyi yapılan şey>

## Suggested Refactor
<sözlü olarak ne yapılmalı — kod değişikliği değil>
```

**Kural**: Kod değiştirme. Sadece analiz. Kullanıcı isterse `/unity-new-system` veya direkt sohbette refactor isteyebilir.
