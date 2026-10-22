#!/usr/bin/env python3
"""Arma todo.html: las 8 páginas de docs/html en un solo archivo, con pestañas y cajas clickeables.

Cada página va en un iframe (srcdoc) para que no se pisen sus estilos, ids ni scripts; las fotos van
embebidas en base64. Volver a correrlo cada vez que cambie una página:  python3 docs/html/armar_todo.py
"""
import base64, html, json, pathlib, re

AQUI = pathlib.Path(__file__).resolve().parent
PAGINAS = [  # (id, archivo, pestaña)
    ("general", "conexiones.html", "Vista general"),
    ("potencia", "potencia.html", "Potencia"),
    ("s3", "placa_s3.html", "Placa S3 (base)"),
    ("wroom", "placa_wroom.html", "Placa WROOM (brazo)"),
    ("seta", "seta.html", "Seta"),
    ("continuidad", "checklist_traccion.html", "Continuidad (tracción)"),
    ("cont-brazo", "checklist_brazo.html", "Continuidad (brazo)"),
    ("pi", "pi5.html", "Pi 5 y GPS"),
]

# Texto de una caja (regex, sin distinguir mayúsculas) -> [página, destino]. Gana la primera que coincide.
# Destino: un id ("h-...") o el comienzo del texto de un h2/h3 de esa página.
REGLAS = [
    [r"bloque a", "seta", "Bloque A"],
    [r"bloque b", "seta", "Bloque B"],
    [r"seta", "seta", "h-idea"],
    [r"esp32-s3|^s3\b", "s3", "h-cb"],
    [r"wroom|^17 · esp32", "wroom", "h-cb"],
    [r"raspberry|cámaras|gps", "pi", "h-diag"],
    [r"lipo", "potencia", "1 ·"],
    [r"fusible", "potencia", "3 ·"],
    [r"xt60", "potencia", "2 ·"],
    [r"selector", "potencia", "4 ·"],
    [r"tracción|42gm|ibt-2 (izq|der)", "potencia", "5-6"],
    [r"^j[123] (base|hombro|codo)|finales? de carrera|pinza", "wroom", "h-tabla"],
    [r"brazo|^j[123] ·|ibt-2 de j", "potencia", "7-9"],
    [r"encoder", "potencia", "h-enc"],
    [r"buck", "potencia", "10 ·"],
    [r"servo", "potencia", "Servos"],
    [r"voltímetro|indicador de barras", "potencia", "12 ·"],
    [r"power bank|^14 · power", "potencia", "14 ·"],
    [r"capacitores", "potencia", "h-parts"],
    [r"imu|hc-sr04|bumper|tensión de batería|divisor|en de la tracción", "s3", "h-born"],
]

# Va dentro de cada iframe: marca las cajas clickeables y avisa al marco de afuera (postMessage anda
# aunque el artifact ponga los iframes en otro origen).
HIJO = """<style>
.nav-hit{cursor:pointer}
.nav-hit:hover{filter:drop-shadow(0 0 4px #2a66ad)}
.nav-flash{outline:3px solid #2a66ad;outline-offset:6px;border-radius:4px;transition:outline-color 1.5s}
.nav-flash.fin{outline-color:transparent}
</style>
<script>
(function(){
  var REGLAS = %s;
  function destino(t){
    for (var i = 0; i < REGLAS.length; i++) if (new RegExp(REGLAS[i][0], 'i').test(t)) return REGLAS[i];
  }
  function marcar(){
    document.querySelectorAll('svg text').forEach(function(tx){
      if (tx.dataset.nav) return;
      var r = destino(tx.textContent.trim()); if (!r) return;
      // en los bloques de las placas solo el título: el clic en el bloque ya filtra el cableado
      var caja = tx.closest('.cb-blk') ? null : tx.previousElementSibling, n = 0;
      while (caja && caja.tagName !== 'rect' && n++ < 3) caja = caja.previousElementSibling;
      [tx, caja && caja.tagName === 'rect' ? caja : null].forEach(function(e){
        if (!e) return;
        e.dataset.nav = 1; e.classList.add('nav-hit');
        var tit = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        tit.textContent = 'Ver detalle'; e.appendChild(tit);
        e.addEventListener('click', function(ev){ ev.stopPropagation(); parent.postMessage({nav: [r[1], r[2]]}, '*'); });
      });
    });
  }
  function ir(dest){
    var el = document.getElementById(dest);
    if (!el) el = [].find.call(document.querySelectorAll('h1,h2,h3'), function(h){ return h.textContent.trim().indexOf(dest) === 0; });
    if (!el) return;
    var bloque = el.closest('article, .card, section') || el;
    el.scrollIntoView({block: 'start', behavior: 'smooth'});
    bloque.classList.remove('fin'); bloque.classList.add('nav-flash');
    setTimeout(function(){ bloque.classList.add('fin'); }, 1200);
    setTimeout(function(){ bloque.classList.remove('nav-flash', 'fin'); }, 2800);
  }
  addEventListener('message', function(e){ if (e.data && e.data.ir) ir(e.data.ir); });
  addEventListener('load', marcar); setTimeout(marcar, 500);
})();
</script>"""

SHELL = """<!doctype html>
<html lang="es">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cableado Arturito R2D2</title>
<style>
  :root { --paper:#f2f5f3; --card:#fff; --ink:#17231f; --muted:#56655f; --rule:#c3cfca; --acc:#2a66ad; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    color-scheme:dark; --paper:#101614; --card:#18201d; --ink:#e2ebe7; --muted:#9aaaa4; --rule:#34423d; --acc:#6fa6ea; } }
  :root[data-theme="dark"] { color-scheme:dark; --paper:#101614; --card:#18201d; --ink:#e2ebe7; --muted:#9aaaa4; --rule:#34423d; --acc:#6fa6ea; }
  html, body { margin:0; height:100%%; background:var(--paper); color:var(--ink); font:15px/1.4 "IBM Plex Sans", system-ui, sans-serif; }
  body { display:flex; flex-direction:column; }
  nav { display:flex; flex-wrap:wrap; align-items:center; gap:6px 8px; padding:10px 16px; border-bottom:1px solid var(--rule); background:var(--card); }
  nav b { margin-right:8px; }
  nav button { font:inherit; color:var(--ink); background:none; border:1px solid var(--rule); border-radius:999px; padding:4px 12px; cursor:pointer; }
  nav button[aria-current="page"] { border-color:var(--acc); box-shadow:inset 0 0 0 1px var(--acc); color:var(--acc); }
  nav button:focus-visible { outline:2px solid var(--acc); outline-offset:2px; }
  #atras { margin-left:auto; }
  nav small { color:var(--muted); flex-basis:100%%; }
  iframe { flex:1; width:100%%; border:0; display:none; }
  iframe.on { display:block; }
</style>
<nav>
  <b>Arturito R2D2</b>
  %s
  <button id="atras" onclick="history.back()">← Volver</button>
  <small>Hacé click en cualquier caja de un diagrama (ESP32, LiPo, seta, motores…) para ir a su detalle.</small>
</nav>
%s
<script>
  var marcos = {}; document.querySelectorAll('iframe').forEach(function(f){ marcos[f.dataset.p] = f; });
  function mostrar(){
    var h = decodeURIComponent(location.hash.slice(1)).split('/'), p = marcos[h[0]] ? h[0] : 'general';
    for (var k in marcos) marcos[k].classList.toggle('on', k === p);
    document.querySelectorAll('nav [data-p]').forEach(function(b){
      if (b.dataset.p === p) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    if (h[1]) marcos[p].contentWindow.postMessage({ir: h.slice(1).join('/')}, '*');
  }
  function ir(p, d){ location.hash = encodeURIComponent(p) + (d ? '/' + encodeURIComponent(d) : ''); }
  addEventListener('message', function(e){ if (e.data && e.data.nav) ir(e.data.nav[0], e.data.nav[1]); });
  addEventListener('hashchange', mostrar);
  for (var k in marcos) marcos[k].addEventListener('load', function(){ if (this.classList.contains('on')) mostrar(); });
  document.querySelectorAll('nav [data-p]').forEach(function(b){ b.onclick = function(){ ir(b.dataset.p); }; });
  mostrar();
</script>
</html>
"""


def pagina(archivo):
    s = (AQUI / archivo).read_text()
    # Solo rutas dentro de un atributo (src="fotos/..."): una ruta citada en el texto quedaría como un base64 sin
    # espacios que estira la página a miles de px de ancho.
    for foto in sorted(set(re.findall(r'(?<=["\'])fotos/[^"\']+\.jpe?g', s))):
        b64 = base64.b64encode((AQUI / foto).read_bytes()).decode()
        s = re.sub(r'(?<=["\'])' + re.escape(foto), "data:image/jpeg;base64," + b64, s)
    hijo = HIJO % json.dumps(REGLAS, ensure_ascii=False)
    return s.replace("</body>", hijo + "</body>") if "</body>" in s else s + hijo


botones = "\n  ".join(f'<button data-p="{p}">{t}</button>' for p, _, t in PAGINAS)
marcos = "\n".join(f'<iframe data-p="{p}" title="{t}" srcdoc="{html.escape(pagina(a))}"></iframe>'
                   for p, a, t in PAGINAS)
(AQUI / "todo.html").write_text(SHELL % (botones, marcos))
print("todo.html:", (AQUI / "todo.html").stat().st_size // 1024, "kB")
