#version 120

uniform sampler2D moonTexture;
uniform vec3 sunDirectionMoonFixed;
uniform float ambient;

varying vec3 vNormal;
varying vec2 vTexCoord;

void main()
{
    vec3 N = normalize(vNormal);
    vec3 L = normalize(sunDirectionMoonFixed);
    float NdotL = max(dot(N, L), 0.0);
    vec4 color = texture2D(moonTexture, vTexCoord);
    float lighting = ambient + (1.0 - ambient) * NdotL;
    gl_FragColor = vec4(color.rgb * lighting, color.a);
}