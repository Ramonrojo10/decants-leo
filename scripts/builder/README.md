# Piezas del armador

Las capas de `public/builder/parts` salen de fotos reales de Namoki Mods (permiso de uso otorgado).

1. Agrega la pieza a `parts-list.txt`: `<id> <mm> <ruta-cdn-shopify>` (prefijo case-, dial-, insert- o hands-).
2. Descarga la foto en tamaño completo a una carpeta `raw/` (`https://cdn.shopify.com/s/files/1/0139/0434/7193/<ruta>`).
3. Quita el fondo:
   - esferas de color e insertos: `python local_cutout.py raw cut <ids>`
   - manecillas planas: `python hands_cutout.py raw cut <ids>`
   - cajas de acero y piezas blancas: removedor de fondo de Higgsfield (1 crédito).
4. Alinea a escala real: `python batch_align.py parts-list.txt cut ../../public/builder/parts`
5. Agrega la opción en `app/data/builder.ts`.

Solo sirven fotos vistas de frente (cajas desde arriba, manecillas planas). Requiere Pillow y NumPy.
