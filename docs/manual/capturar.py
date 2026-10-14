#!/usr/bin/env python3
"""Captura los diagramas de docs/html como PNG para el manual (Firefox headless; el snap no ve /tmp).
Uso: python3 docs/manual/capturar.py"""
import pathlib, subprocess
from PIL import Image, ImageChops

HTML = pathlib.Path(__file__).resolve().parent.parent / 'html'
FIG = pathlib.Path(__file__).resolve().parent / 'figuras'
# (página, índice del <svg> en el documento, archivo, ancho de ventana)
CAPTURAS = [
    ('conexiones', 0, 'html_general', 1300), ('conexiones', 1, 'html_potencia_resumen', 1300),
    ('potencia', 0, 'html_potencia', 1500), ('placa_s3', 0, 'html_s3_cableado', 1400),
    ('placa_s3', 1, 'html_s3_perforadas', 1400), ('placa_wroom', 0, 'html_wroom_cableado', 1400),
    ('placa_wroom', 1, 'html_wroom_plano', 1400), ('seta', 0, 'html_seta_foto', 1000), ('seta', 1, 'html_seta_circuito', 1200),
]
JS = """<script>addEventListener('load', function(){
  document.documentElement.setAttribute('data-theme','light');
  var s = document.querySelectorAll('svg:not([aria-hidden])')[%d].cloneNode(true);
  s.style.width='%dpx'; s.style.height='auto'; s.style.minWidth='0'; s.style.maxWidth='none'; s.style.overflow='visible';
  document.body.innerHTML=''; document.body.style.background='#fff'; document.body.style.margin='0';
  var d=document.createElement('div'); d.className='page'; d.style.padding='90px 10px'; d.appendChild(s); document.body.appendChild(d);
});</script>"""
for pag, i, nombre, ancho in CAPTURAS:
    tmp = HTML / f'_cap_{nombre}.html'
    tmp.write_text((HTML / f'{pag}.html').read_text() + JS % (i, ancho - 120))
    png = FIG / f'{nombre}.png'
    subprocess.run(['firefox', '--headless', f'--window-size={ancho},2600', '--screenshot', str(png), tmp.as_uri()],
                   capture_output=True, timeout=90)
    tmp.unlink()
    im = Image.open(png).convert('RGB')
    alto = im.height  # Firefox deja una franja negra abajo: sacarla antes de recortar el blanco
    while alto > 1 and max(im.crop((0, alto - 1, im.width, alto)).convert('L').getdata()) < 40:
        alto -= 1
    im = im.crop((0, 0, im.width, alto))
    caja = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox()
    im.crop(caja).save(png)
    print(nombre, im.crop(caja).size)
