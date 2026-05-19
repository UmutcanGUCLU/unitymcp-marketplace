---
description: Bir görsel efekt spesifikasyonundan (örn. "kenarları parıldayan toon shader") URP uyumlu shader üret. Hem HLSL hem Shader Graph alternatifi sun. SRP Batcher uyumlu yaz.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /unity-shader-from-spec $ARGUMENTS

Kullanıcı spec: `$ARGUMENTS`

## Adımlar

1. **Spec'i parse et**:
   - Lit mi unlit mi?
   - Transparent mı opaque mı?
   - Hangi efektler? (fresnel, dissolve, outline, vertex displacement, scroll UV, vb.)
   - Hedef platform (mobile için `half`, PC için `float` ağırlıklı)?

2. **HLSL versiyonu üret** (`Assets/_Project/Art/Shaders/$Name.shader`):
   - URP-uyumlu (`RenderPipeline = UniversalPipeline` tag)
   - `CBUFFER_START(UnityPerMaterial)` — SRP Batcher uyumlu
   - Gerekirse multi-pass (outline için OutlinePass + ForwardLit)
   - `#pragma multi_compile_instancing` GPU instancing için
   - Mobile için `half` precision tercih

3. **Shader Graph alternatifi** (eğer mantıklıysa):
   - Node hiyerarşisini ASCII olarak göster
   - Sub Graph önerilen yerleri belirt
   - Custom Function Node gerekirse HLSL snippet ekle

4. **Test material örneği** üret (`Assets/_Project/Art/Materials/M_$Name.mat` için kullanım talimatı)

5. **Performance notu**:
   - Tahmini fragment cost (texture sample, instruction count tahmini)
   - Mobile suitability
   - Variant sayısı

## Önemli

- Sahte fonksiyon / hayali macro yok — sadece gerçek URP shader library API
- Vertex shader'da `TransformObjectToHClip()`, normal için `TransformObjectToWorldNormal()`
- Built-in shader'dan kopya kalıntı yok (`UnityCG.cginc` URP'de kullanılmaz)
- Sample texture: `TEXTURE2D` + `SAMPLER` ayrı declare, `SAMPLE_TEXTURE2D` macro ile sample
