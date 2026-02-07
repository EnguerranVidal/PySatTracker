#version 120

varying vec3 vNormal;
varying vec2 vTexCoord;

void main()
{
    vNormal = normalize(gl_Normal);
    vTexCoord = gl_MultiTexCoord0.st;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
