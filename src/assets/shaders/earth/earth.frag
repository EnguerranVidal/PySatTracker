#version 120

uniform sampler2D earthDay;
uniform sampler2D earthNight;
uniform vec3 sunDirectionEcef;
uniform float twilightWidth;
uniform float nightIntensity;
varying vec3 vNormal;
varying vec2 vTexCoord;

void main()
{
    vec3 N = normalize(vNormal);
    vec3 L = normalize(sunDirectionEcef);
    float NdotL = dot(N, L);
    float night = smoothstep(-twilightWidth, twilightWidth, -NdotL);
    vec4 dayColor   = texture2D(earthDay,   vTexCoord);
    vec4 nightColor = texture2D(earthNight, vTexCoord) * nightIntensity;
    gl_FragColor = mix(dayColor, nightColor, night);
}
