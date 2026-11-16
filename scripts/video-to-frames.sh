#!/bin/sh
# Convierte el video de portada (Higgsfield) en cuadros para el scroll.
# Uso: sh scripts/video-to-frames.sh ruta/al/video.mp4 [fps] [ancho]
set -e
VIDEO="$1"
FPS="${2:-24}"
WIDTH="${3:-1280}"
OUT="public/hero/frames"

[ -f "$VIDEO" ] || { echo "No existe el video: $VIDEO" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"
ffmpeg -loglevel error -i "$VIDEO" -vf "fps=$FPS,scale=$WIDTH:-2" -q:v 8 "$OUT/%04d.jpg"

COUNT=$(ls "$OUT" | wc -l | tr -d ' ')
HEIGHT=$(sips -g pixelHeight "$OUT/0001.jpg" | awk '/pixelHeight/ {print $2}')
printf '{ "frames": %s, "width": %s, "height": %s }\n' "$COUNT" "$WIDTH" "$HEIGHT" > public/hero/manifest.json
echo "Listo: $COUNT cuadros en $OUT"
