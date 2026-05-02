#version 120

uniform sampler2D moonTexture;
uniform vec3 sunDirectionEci;
uniform float ambient;

varying vec3 fragNormalWorld;
varying vec2 vTexCoord;

void main() {
    vec3 normal = normalize(fragNormalWorld);
    vec3 sunDir = normalize(sunDirectionEci);

    float diffuse = max(dot(normal, sunDir), 0.0);
    float light = ambient + diffuse * (1.0 - ambient);

    vec4 texColor = texture2D(moonTexture, vTexCoord);
    gl_FragColor = texColor * vec4(light, light, light, 1.0);
}