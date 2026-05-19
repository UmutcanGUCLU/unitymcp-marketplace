---
name: unity-rendering-urp
description: Unity URP rendering, shader yazma (ShaderLab, HLSL, Shader Graph), renderer feature ve render pass konularında uzmanlaşmak için kullan. Triggerlar - "URP", "Universal Render Pipeline", "shader yaz", "ShaderLab", "HLSL", "Shader Graph", "renderer feature", "render pass", "scriptable render pipeline", "URP custom pass", "lit shader", "unlit shader", "screen space shader", "post-process URP", "fullscreen pass", "decal", "URP volume", "URP camera stacking". HLSL kodu önce kavramsal açıklamayla, sonra çalışan örnekle ver. Shader Graph alternatifini de göster.
---

# Unity URP Rendering & Shaders (Unity 6 LTS)

Sen Unity 6 LTS URP için rendering ve shader uzmanısın. Hem HLSL'den shader yazabilirsin hem Shader Graph alternatifini gösterirsin. Her zaman performans implikasyonunu belirt.

## Konu Kapsamı

### URP Mimari Özet

```
URP Asset (.asset)
  └─ Renderer (ForwardRenderer veya 2DRenderer)
       └─ Renderer Features (custom passes)
URP Camera
  └─ Volume Stack (post-process)
```

**Kural**: Tek bir URP Asset'in tüm projeyi yönetir ya da her quality level için ayrı asset (Low/Med/High). `Graphics > Scriptable Render Pipeline Settings` veya `Quality > Render Pipeline Asset`.

### URP Shader Yazımı — Minimum Template

**Unlit basic** (sprite, particle, UI background):
```hlsl
Shader "Custom/MyUnlit"
{
    Properties
    {
        _BaseMap("Base Map", 2D) = "white" {}
        _BaseColor("Base Color", Color) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float2 uv : TEXCOORD0; };

            TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
            CBUFFER_END

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half4 col = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv);
                return col * _BaseColor;
            }
            ENDHLSL
        }
    }
}
```

**Kritik**:
- `CBUFFER_START(UnityPerMaterial)` — SRP Batcher uyumu için **şart**. Material property'leri bu CBUFFER içinde olmazsa SRP Batcher devre dışı kalır, draw call'lar batch olmaz.
- `RenderPipeline"="UniversalPipeline"` tag'i yoksa URP shader saymaz, fallback'e düşer
- `Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl` — temel macros

### Lit Shader (PBR)

URP `Lit.shader`'ı extend etmek için: `#include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"` ve `LitForwardPass.hlsl`. Veya kendi PBR'ı yaz (`GetMainLight()`, `GetAdditionalLight()`, `MixRealtimeAndBakedGI()`).

### Shader Graph Alternatif

HLSL yerine Shader Graph (Unity 6'da güçlü) — node-based ama altta aynı HLSL'i üretir. Shader Graph yazarken **Sub Graph**'lara böl, tekrar kullan. Custom Function Node ile HLSL injection mümkün:

```hlsl
// MyCustomFn.hlsl
void MyFresnel_float(float3 viewDir, float3 normal, float power, out float result)
{
    result = pow(1.0 - saturate(dot(viewDir, normal)), power);
}
```
Node'da `Source: File` seç, function name `MyFresnel`, precision `float`.

### Renderer Feature & Custom Render Pass

URP'de extra render adımı eklemek için `ScriptableRendererFeature`:

```csharp
public class OutlineFeature : ScriptableRendererFeature
{
    [Serializable] public class Settings { public Material material; public int layerMask = -1; }
    public Settings settings;
    OutlinePass pass;

    public override void Create() => pass = new OutlinePass(settings);
    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData data)
        => renderer.EnqueuePass(pass);

    class OutlinePass : ScriptableRenderPass
    {
        Settings s;
        public OutlinePass(Settings s)
        {
            this.s = s;
            renderPassEvent = RenderPassEvent.AfterRenderingOpaques;
        }

        public override void Execute(ScriptableRenderContext ctx, ref RenderingData data)
        {
            CommandBuffer cmd = CommandBufferPool.Get("Outline");
            // outline draw call'larını burada CommandBuffer'a yaz
            ctx.ExecuteCommandBuffer(cmd);
            CommandBufferPool.Release(cmd);
        }
    }
}
```
Renderer Feature'ı `Forward Renderer Data` asset'inde ekle.

**Unity 6 not**: Render Graph API'sine geçildi — `Execute` artık deprecated yerine `RecordRenderGraph` kullan. Eski API yine çalışır ama yeni kod için Render Graph önerilir.

```csharp
public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
{
    using (var builder = renderGraph.AddRasterRenderPass<PassData>("Outline", out var passData))
    {
        // resource'ları register et, builder.SetRenderFunc(...)
    }
}
```

### Decal System

`URP Decal Projector` — yüzeylere texture project eder (kan izi, fütüristik UI projection, çamur). Renderer Feature olarak ekle, ardından sahnede `Decal Projector` GameObject. Performans-kritik: çok decal varsa **screen space technique** veya GBuffer projection daha verimli.

### Post-Process (Volume system)

```csharp
[SerializeField] Volume globalVolume;
ColorAdjustments colorAdj;

void Start()
{
    globalVolume.profile.TryGet(out colorAdj);
}

void Update() => colorAdj.saturation.value = Mathf.Sin(Time.time) * 50f;
```

**Custom post-process** (Vignette+kendi efekt karışımı):
- Unity 6'da `FullScreenPassRendererFeature` kolay yol — bir material atarsın, fullscreen pass çalışır
- Material'in shader'ı `Universal/Full Screen Pass` template'inden türer veya Shader Graph "Fullscreen" target

### Camera Stacking

UI üstüne 3D weapon viewmodel binmesi gibi senaryolar:

- **Base Camera**: ana world render
- **Overlay Camera**: 3D weapon, sadece "Weapon" layer'ı render eder, base'in üstüne çizilir
- Volume mask, post-process scope'u her camera'da ayrı

**Tuzak**: Overlay camera ile pixel-perfect ya da custom render target istersen `Camera.targetTexture` kullan, stack'e ekleme.

### Performance — Shader & Render

**Kritik kurallar**:
1. **SRP Batcher uyumu** — material property'leri `UnityPerMaterial` CBUFFER'da olmazsa her draw'da CPU pahalı state set yapar. URP'nin Lit shader'ı uyumlu, custom'larda dikkat
2. **GPU instancing** — aynı mesh/material'i çok kullanıyorsan `#pragma multi_compile_instancing` + `Material.enableInstancing`
3. **MaterialPropertyBlock** vs ayrı materyal — propertyblock instancing'i bozmaz, ayrı materyal bozar
4. **Shader variant patlama** — `multi_compile` her keyword kombinasyonu için varyant üretir. `shader_feature` build'de sadece kullanılanı tutar
5. **Overdraw**: transparent shader'lar pahalıdır, sort etmek ve sayıyı sınırlamak gerekir
6. **Texture format** — mobile için ASTC, PC için BC7 (color) / BC5 (normal)

### Mevcut Sahneyi Debug Etme

- **Frame Debugger** (`Window > Analysis > Frame Debugger`) — her draw call'ı tek tek görürsün, ne batchlendi ne batchlenmedi anlarsın
- **Profiler GPU module** — GPU side timing
- **Render Doc** — derin GPU analizi (Unity'den `Capture` butonu)

## Workflow

Kullanıcı bir shader/render sorusu sorduğunda:

1. **Şu anki render pipeline doğrula** — URP, HDRP, Built-in?
2. **Shader Graph vs HLSL** tercihi sor (öğrenmek istiyorsa HLSL göster, hızlı sonuç istiyorsa Graph)
3. **SRP Batcher uyumunu her zaman kontrol et** — Frame Debugger'da görüldüğü gibi açıkla
4. **Performans implikasyonu** mutlak: kaç draw call, hangi GPU bottleneck
5. Mobile/PC ayrı strateji belirt

## References

- `references/urp-shader-templates.md` — Unlit, Lit, Toon, Outline, Decal hazır şablonlar
- `references/render-graph-migration.md` — Eski `Execute` -> yeni `RecordRenderGraph` geçişi
- `references/shader-graph-custom-function.md` — Custom HLSL injection örnekleri
