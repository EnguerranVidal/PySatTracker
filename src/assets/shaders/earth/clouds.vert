#version 120

varying vec2 vTexCoord;
varying vec3 vLocalNormal;

void main()
{
    vTexCoord = gl_MultiTexCoord0.xy;
    vLocalNormal = normalize(gl_Normal);
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}