---
description: Bir Unity konseptini "kavramsal -> kod -> production tuzakları -> trade-off" formatında derinlemesine açıkla. Öğrenme amaçlı — kullanıcı temelden ileri seviyeye ilerliyor.
allowed-tools: Read, Glob, Grep
---

# /unity-explain $ARGUMENTS

Konu: `$ARGUMENTS`

## Format (her zaman bu sırada)

### 1. Tek Cümle Özet
"<Konu>, <şu işi yapar>, çünkü <şu sebep>."

### 2. Kavramsal Açıklama (Türkçe, 1-2 paragraf)
- Konunun "neden var olduğu" — hangi problemi çözüyor
- Unity'nin diğer parçalarıyla ilişkisi
- Görsel analoji varsa kullan

### 3. Çalışan Kod Örneği
- Identifier'lar İngilizce
- Yorumlar Türkçe
- Tam çalışan örnek (eksik referans yok)
- Mümkün olduğunca minimal — 30 satır altı tercih

### 4. Adım Adım Açıklama
Kod satırları neden o sırada, neden o API:
- `Awake()` neden `Start()` değil
- `[SerializeField]` neden `public` değil
- vs.

### 5. Production Tuzakları (en az 3 madde)
"Bunu öğrenmek hobi seviyesi. Production'a çıkarken karşılaşacakların:"
- Tuzak 1 — semptomu ve çözümü
- Tuzak 2
- Tuzak 3

### 6. Trade-off ve Alternatifler
"X yöntemi ile Y yöntemi arasındaki seçim..."

| X yöntemi | Y yöntemi |
|---|---|
| ne zaman kullan | ne zaman kullan |
| pro | pro |
| con | con |

### 7. Sonraki Adımlar (öğrenme yolu)
- Bu konuya hakim olduktan sonra hangi konu doğal devam?
- Hangi paket/asset bu konuda derinleşmek için?
- Hangi resmi Unity manual sayfası ek okuma için?

## Önemli

- Hobi tutorial kalitesinde değil, **production seviyesinde** açıkla
- "Bu basit, dert etmeyin" deme — kullanıcı temelden ileri seviyeye gidiyor, her şeyi anlamak istiyor
- Eğer konu bir başka konuya bağımlıysa, prerequisite'i 1 cümlede özetle ve önce onu öğrenmeyi öner
- Spesifik tuzaklar — "GC alloc yapar" yetmez, "kaç byte, hangi durumda" yaz
