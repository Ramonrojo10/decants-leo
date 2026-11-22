# Armador de Seiko Mods: piezas de Leo

El armador usa solo piezas propias de Leo, en tres clases: GMT, Nautilus y Santos.

1. Las fotos originales están en `fotos-leo/` (fuera de la web). Se separan en capas PNG transparentes con `leo_gmt_batch.py` / `leo_gmt_split.py` (GMT) y `leo_nautilus_split.py` (Nautilus). Todas las capas comparten un lienzo de 1000 x 2000 px (1000 px = 48 mm, centro de la esfera en 500,1000), así que se apilan sin desplazamientos.
2. `export_leo_parts.py` exporta las piezas elegidas a `public/builder/leo/<clase>/<tipo>-<id>.webp` (WebP q85 con alfa). Incluye la sombra de contacto del bisel GMT recortada al metal de cada caja.
3. `app/data/builder.ts` define las opciones (nombres en español) y el orden de capas:
   - GMT: brazalete, caja, sombra de bisel, esfera, sombra de esfera, bisel.
   - Nautilus y Santos: correa, esfera, sombra de esfera, caja.

Para agregar una pieza: sumarla a las listas de `export_leo_parts.py`, correrlo (`python scripts/builder/export_leo_parts.py`) y añadir la opción en `builder.ts`. Dentro de una clase todo es combinable.

## Santos

Las fotos originales están en `fotos-leo/santos/`. `leo_santos_split.py` las separa en capas (caja, esfera, correa y `shadowdial`) y las escribe en `public/builder/leo/santos/` como `case-santos-<id>.webp`, `dial-santos-<id>.webp`, `strap-santos-<id>.webp`, mismo lienzo de 1000 x 2000 px. Enlace para compartir: `?arma=santos.<caja>.<esfera>.<correa>`.
