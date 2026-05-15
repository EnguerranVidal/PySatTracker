#version 120

uniform sampler2D cloudTexture;
uniform float cloudOpacity;
uniform float cloudBrightnessCutoff;
uniform float cloudNightOpacity;
uniform vec3 cloudColor;
uniform vec3 sunDirectionLocal;

varying vec2 vTexCoord;
varying vec3 vLocalNormal;

void main()
{
    vec3 sampleColor = texture2D(cloudTexture, vTexCoord).rgb;
    float luminance = dot(sampleColor, vec3(0.2126, 0.7152, 0.0722));
    float cloudMask = smoothstep(cloudBrightnessCutoff, 1.0, luminance);
    vec3 normal = normalize(vLocalNormal);
    vec3 sunDirection = normalize(sunDirectionLocal);
    float dayFactor = dot(normal, sunDirection);
    dayFactor = smoothstep(-0.10, 0.25, dayFactor);
    float alphaScale = mix(cloudNightOpacity, 1.0, dayFactor);
    float brightnessScale = mix(0.18, 1.15, dayFactor);
    vec3 finalColor = cloudColor * brightnessScale;
    float finalAlpha = cloudMask * cloudOpacity * alphaScale;
    gl_FragColor = vec4(finalColor, finalAlpha);
}