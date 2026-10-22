# CLAUDE.md — entregas (Colab / Drive)

Complementa el `CLAUDE.md` de la raíz. Vale también para `docs/TPF R2/`.

## Quién edita qué
- **El usuario edita las entregas a mano en Drive/Colab** (el profesor sigue el panel de actividad). Claude edita el
  `.ipynb` y el `.md` locales y le pasa qué copiar.
- El conector de Drive no tiene permiso de escritura: el usuario sube todo a mano.
- **Si el usuario edita en Colab, manda su versión:** bajar el `.ipynb` de Drive y reconstruir el `.md` desde él antes
  de tocar nada.
- Las entregas ya entregadas no se tocan sin preguntar.

## Formato (desde la E7 de R1, 17/10)
- El `.md` es la fuente; el cuaderno se arma desde él (una celda por cada `<!-- celda -->`). El que va a Colab es
  `Entrega7_.ipynb`, con links `lh3`.
- No incrustar imágenes en base64 (la celda queda ilegible en Colab).
- Diagramas `.drawio` + PNG en `Diagramas/`, figuras en `Imagenes/FigN_*`. Tablas y figuras grandes (diagramas con letra
  de 16-20 pt), párrafos cortos, sin emojis.

## Imágenes
- Por link `lh3.googleusercontent.com/d/<ID>=w2400`. Al cambiar una: subir nueva versión en Drive (mismo ID) y
  cambiar el `=w` para saltear la caché.
- Los IDs que pasa el usuario se verifican bajando cada `lh3` y comparando el tamaño con el archivo local.
- Diagramas: `.drawio` → PNG con Firefox headless + visor de diagrams.net (no hay draw.io instalado; el snap de
  Firefox no ve `/tmp`: usar `~/snap/firefox/common/render/`).
