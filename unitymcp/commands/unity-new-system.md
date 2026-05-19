---
description: Unity'de yeni bir gameplay sistemi scaffold et (ör. inventory, dialogue, quest). MonoBehaviour + ScriptableObject + Event channel + interface ayrımıyla modüler, test edilebilir bir iskelet üretir. Argüman olarak sistemin adını al ($ARGUMENTS).
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /unity-new-system $ARGUMENTS

Kullanıcı yeni bir gameplay sistemi istiyor: `$ARGUMENTS`.

## Adımlar

1. **Sistem adını netleştir**: kullanıcı verdiyse kullan; yoksa sor.
2. **Modüler iskelet üret** — şu dosyalar:

```
Assets/_Project/Code/Gameplay/$SystemName/
  I$SystemNameService.cs           <- interface
  $SystemNameService.cs            <- MonoBehaviour implementation
  $SystemNameData.cs               <- ScriptableObject (config)
  $SystemNameEvents.cs             <- event channel
  $SystemNameTests.cs              <- Editor test (NUnit)
```

3. **Mimari kuralı uygula**:
   - Sistem dışarı `interface` üzerinden açılır
   - Config `ScriptableObject` ile ayarlanır
   - Diğer sistemlerle event channel üzerinden konuşur (direct ref minimize)
   - Singleton kullanma — varsa **Service Locator** veya DI öner

4. **Her dosya için**:
   - Başına dosya path comment (`// File: Assets/...`)
   - Kullanım örneği (XML doc comment)
   - TODO yorumları belirgin (kullanıcı doldursun)

5. **README.md** ekle: sistemin nasıl kurulacağı, nasıl entegre edileceği.

## Örnek (Inventory için)

`IInventoryService`: `AddItem`, `RemoveItem`, `HasItem`, `GetItems`
`InventoryService` (MonoBehaviour): implementation, eventleri raise eder
`InventoryData` (SO): default item'lar, max slot count
`InventoryEvents` (SO event channels): `OnItemAdded`, `OnItemRemoved`, `OnInventoryFull`

Üretilen kodu **çalışır halde** yaz — eksik referans, hayali API yok. Unity 6 LTS API'sini kullan.
