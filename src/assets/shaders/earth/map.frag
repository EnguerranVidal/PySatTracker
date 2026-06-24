#version 120
uniform sampler2D dayTexture;
uniform sampler2D nightTexture;
uniform float sunLongitudeRadians;
uniform float sunLatitudeRadians;
uniform float twilightWidth;
varying vec2 vTexCoord;
void main() {
    float longitude = vTexCoord.x * 360.0 - 180.0;
    float latitude = vTexCoord.y * 180.0 - 90.0;
    float lonRad = radians(longitude);
    float latRad = radians(latitude);
    float cosTheta = sin(latRad) * sin(sunLatitudeRadians) + cos(latRad) * cos(sunLatitudeRadians) * cos(lonRad - sunLongitudeRadians);
    float factor = clamp((cosTheta + twilightWidth / 2.0) / twilightWidth, 0.0, 1.0);
    vec3 dayColor = texture2D(dayTexture, vTexCoord).rgb;
    vec3 nightColor = texture2D(nightTexture, vTexCoord).rgb;
    vec3 color = mix(nightColor, dayColor, factor);
    gl_FragColor = vec4(color, 1.0);
}