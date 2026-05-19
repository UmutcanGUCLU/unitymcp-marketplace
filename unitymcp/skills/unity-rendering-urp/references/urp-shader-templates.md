# URP Shader Template'leri — Hazır Kullanım

Doğrudan kopyala, projeye at, material ata. Unity 6 LTS URP uyumlu, SRP Batcher friendly.

## 1. Unlit (En Basit, Sprite/Particle/UI)

```hlsl
Shader "Custom/Unlit_Basic"
{
    Properties
    {
        [MainTexture] _BaseMap("Base Map", 2D) = "white" {}
        [MainColor]   _BaseColor("Base Color", Color) = (1,1,1,1)
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }

        Pass
        {
            Name "Unlit"
            Tags { "LightMode"="UniversalForward" }

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
            CBUFFER_END

            TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv         : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float2 uv          : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_TRANSFER_INSTANCE_ID(IN, OUT);

                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(IN);
                half4 col = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv);
                return col * _BaseColor;
            }
            ENDHLSL
        }
    }
}
```

## 2. Toon (Cel Shading)

```hlsl
Shader "Custom/Toon"
{
    Properties
    {
        _BaseMap("Base Map", 2D) = "white" {}
        _BaseColor("Base Color", Color) = (1,1,1,1)
        _RampSteps("Ramp Steps", Range(1, 8)) = 3
        _ShadowColor("Shadow Color", Color) = (0.3, 0.3, 0.4, 1)
        _SpecPower("Specular Power", Range(0.1, 256)) = 16
        _SpecColor("Specular Color", Color) = (1, 1, 1, 1)
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Name "ToonForward"
            Tags { "LightMode"="UniversalForward" }

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHTS

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
                half4  _ShadowColor;
                half4  _SpecColor;
                half   _RampSteps;
                half   _SpecPower;
            CBUFFER_END

            TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 normalWS    : TEXCOORD0;
                float3 positionWS  : TEXCOORD1;
                float2 uv          : TEXCOORD2;
                float4 shadowCoord : TEXCOORD3;
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs pos = GetVertexPositionInputs(IN.positionOS.xyz);
                VertexNormalInputs   nor = GetVertexNormalInputs(IN.normalOS);

                OUT.positionHCS = pos.positionCS;
                OUT.normalWS    = nor.normalWS;
                OUT.positionWS  = pos.positionWS;
                OUT.uv          = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.shadowCoord = GetShadowCoord(pos);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half4 baseCol = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv) * _BaseColor;

                Light mainLight = GetMainLight(IN.shadowCoord);
                half3 N = normalize(IN.normalWS);
                half3 L = mainLight.direction;
                half  NdotL = saturate(dot(N, L));

                // Stepped ramp — toon shading core
                half ramp = floor(NdotL * _RampSteps) / _RampSteps;
                half shadow = mainLight.shadowAttenuation;
                ramp *= shadow;

                half3 lit  = baseCol.rgb * mainLight.color * ramp;
                half3 dark = baseCol.rgb * _ShadowColor.rgb * (1 - ramp);
                half3 col  = lit + dark;

                // Simple specular
                half3 V = normalize(GetWorldSpaceViewDir(IN.positionWS));
                half3 H = normalize(L + V);
                half  spec = pow(saturate(dot(N, H)), _SpecPower);
                spec = step(0.5, spec);  // step'li toon specular
                col += spec * _SpecColor.rgb * shadow;

                return half4(col, baseCol.a);
            }
            ENDHLSL
        }

        // Shadow caster pass — gölge düşürmek için
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On
            ColorMask 0

            HLSLPROGRAM
            #pragma vertex   ShadowPassVertex
            #pragma fragment ShadowPassFragment
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/ShadowCasterPass.hlsl"
            ENDHLSL
        }
    }
}
```

## 3. Outline (Inverted Hull, Toon ile birleşir)

İki pass — ilki büyütülmüş arka yüzleri siyah renderlar, ikincisi normal renderlar.

```hlsl
Shader "Custom/Outline"
{
    Properties
    {
        _BaseColor("Base Color", Color) = (1,1,1,1)
        _OutlineColor("Outline Color", Color) = (0,0,0,1)
        _OutlineWidth("Outline Width", Range(0, 0.1)) = 0.02
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }

        // PASS 1 — Outline
        Pass
        {
            Name "Outline"
            Cull Front           // Arka yüzleri renderla
            ZWrite On

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                half4 _OutlineColor;
                half  _OutlineWidth;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings   { float4 positionHCS : SV_POSITION; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                // Normal yönünde dışa it
                float3 expanded = IN.positionOS.xyz + IN.normalOS * _OutlineWidth;
                OUT.positionHCS = TransformObjectToHClip(expanded);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target { return _OutlineColor; }
            ENDHLSL
        }

        // PASS 2 — Base color (basit unlit, sen kendi shading'ini koy)
        Pass
        {
            Name "Base"
            Cull Back

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                half4 _OutlineColor;
                half  _OutlineWidth;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings   { float4 positionHCS : SV_POSITION; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target { return _BaseColor; }
            ENDHLSL
        }
    }
}
```

**Outline alternatifi — Renderer Feature ile screen-space outline** (daha kaliteli, ama daha pahalı): post-process pass'ı kenar tespit eder (depth + normal edge detection). HLSL'i `references/render-graph-migration.md` içinde bulabilirsin.

## 4. Dissolve (Burn-in Effect)

```hlsl
Shader "Custom/Dissolve"
{
    Properties
    {
        _BaseMap("Base Map", 2D) = "white" {}
        _BaseColor("Base Color", Color) = (1,1,1,1)
        _NoiseMap("Noise Map", 2D) = "gray" {}
        _DissolveAmount("Dissolve", Range(0,1)) = 0
        _EdgeColor("Edge Color", Color) = (1, 0.5, 0, 1)
        _EdgeWidth("Edge Width", Range(0, 0.2)) = 0.05
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                float4 _NoiseMap_ST;
                half4  _BaseColor;
                half4  _EdgeColor;
                half   _DissolveAmount;
                half   _EdgeWidth;
            CBUFFER_END

            TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);
            TEXTURE2D(_NoiseMap); SAMPLER(sampler_NoiseMap);

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float2 uv : TEXCOORD0; float2 noiseUV : TEXCOORD1; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv          = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.noiseUV     = TRANSFORM_TEX(IN.uv, _NoiseMap);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half noise = SAMPLE_TEXTURE2D(_NoiseMap, sampler_NoiseMap, IN.noiseUV).r;
                clip(noise - _DissolveAmount);  // bu pixel'i discard et

                half4 col = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv) * _BaseColor;

                // Edge glow
                half edge = step(noise - _DissolveAmount, _EdgeWidth);
                col.rgb = lerp(col.rgb, _EdgeColor.rgb, edge);
                return col;
            }
            ENDHLSL
        }
    }
}
```

`_DissolveAmount` 0'dan 1'e animate edersen "objenin yanması" efektidir. `clip()` Z-prepass'i bozar — eğer post-process'in depth-dependent şeyleri varsa karışım problemi olabilir.

## 5. UI Frosted Glass (Blur Background)

Bu daha karmaşık — Camera'nın depth+color buffer'ına sample yapmak gerekir. URP'de **Opaque Texture**'ı açman lazım (URP Asset → Quality → Opaque Texture).

```hlsl
Shader "Custom/FrostedGlass"
{
    Properties
    {
        _Tint("Tint", Color) = (1,1,1,0.3)
        _BlurSize("Blur Size", Range(0, 0.05)) = 0.01
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareOpaqueTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Tint;
                half  _BlurSize;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings   { float4 positionHCS : SV_POSITION; float4 screenPos : TEXCOORD0; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.screenPos   = ComputeScreenPos(OUT.positionHCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 uv = IN.screenPos.xy / IN.screenPos.w;

                // 9-tap box blur
                half4 col = 0;
                for (int x = -1; x <= 1; x++)
                    for (int y = -1; y <= 1; y++)
                        col += SampleSceneColor(uv + float2(x, y) * _BlurSize);
                col /= 9.0;

                col.rgb = lerp(col.rgb, _Tint.rgb, _Tint.a);
                return half4(col.rgb, 1);
            }
            ENDHLSL
        }
    }
}
```

**Tuzak**: Opaque Texture URP Asset'te kapalıysa `_CameraOpaqueTexture` null olur. Quality > Opaque Texture aç.

## Tüm Template'ler İçin Genel Kural

1. `CBUFFER_START(UnityPerMaterial)` → SRP Batcher uyumu
2. `TransformObjectToHClip()` — built-in `UnityObjectToClipPos` URP'de yok
3. Pass başında `Name "..."` ekle — Frame Debugger'da görünür, debug kolay
4. `#pragma multi_compile_instancing` + instance ID macros — GPU instancing destek
5. URP shader library include path: `Packages/com.unity.render-pipelines.universal/...`
6. `half` precision mobile için tercih, PC'de fark az
