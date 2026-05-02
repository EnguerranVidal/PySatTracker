#version 120

uniform mat4 modelMatrix;
uniform vec3 sunDirectionEci;

varying vec3 fragNormalWorld;
varying vec2 vTexCoord;

void main()
{
    // Transform normal to world space
    vec3 normal = gl_Normal;
    fragNormalWorld = normalize((modelMatrix * vec4(normal, 0.0)).xyz);

    vTexCoord = gl_MultiTexCoord0.xy;
    gl_Position = ftransform();
}