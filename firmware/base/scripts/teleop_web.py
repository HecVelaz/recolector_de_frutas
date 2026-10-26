"""Teleoperado de la base y del brazo desde el navegador del celular: joysticks táctiles → /cmd_vel y /brazo/comando.

Uso (en la Pi, con los agentes de la base y del brazo corriendo):
  source /opt/ros/jazzy/setup.bash
  python3 teleop_web.py            # y en el celular: http://100.116.96.71:8000 (Tailscale)

Solo la biblioteca estándar y rclpy (sin rosbridge). La página manda la consigna cada 100 ms mientras se toca el
joystick; si deja de llegar (se suelta, se cierra la página o se corta la red), no se publica nada y la S3 frena
sola por su watchdog de 300 ms. El brazo igual: cada consigna es un `d <n> <pct>` (lazo abierto, como la prueba
17-brazo-joystick) que el WROOM corta solo a los JOG_MS = 300 ms; los límites desde el cero y el atasco los cuida el
firmware. El brazo tiene su propio ARMAR y su "Cero aquí" (z): sin cero no hay límites.
"""
import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import String

PUERTO = 8000
V_MAX, W_MAX = 0.25, 1.0  # los mismos topes que CFG_DIF de la base
DUTY_MAX = 30.0  # JOG_DUTY_MAX del brazo (el firmware recorta igual)
COMANDOS = {"armar", "desarmar", "s", "r", "z"}

PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Arturito</title>
<style>
  body { margin: 0; font: 16px system-ui, sans-serif; background: #111; color: #eee;
         user-select: none; -webkit-user-select: none; display: flex; flex-direction: column; align-items: center;
         gap: 14px; padding: 14px; box-sizing: border-box; min-height: 100vh; }
  #estado, .estado { font: 13px ui-monospace, monospace; background: #222; padding: 8px 10px; border-radius: 8px;
            width: 100%; max-width: 420px; box-sizing: border-box; min-height: 3em; word-break: break-word; }
  .pad { width: min(80vw, 320px); height: min(80vw, 320px); border-radius: 50%; background: #262626;
         border: 2px solid #444; position: relative; flex: none; touch-action: none; }
  .bola { width: 34%; height: 34%; border-radius: 50%; background: #3a7bd5; position: absolute;
          left: 33%; top: 33%; }
  #padB { width: min(60vw, 240px); height: min(60vw, 240px); }
  #barra { width: 70px; height: min(60vw, 240px); border-radius: 35px; background: #262626; border: 2px solid #444;
           position: relative; flex: none; touch-action: none; }
  #barra .bola { width: 60px; height: 60px; left: 5px; top: calc(50% - 30px); background: #e08a1e; }
  #padB .bola { background: #e08a1e; }
  h2 { margin: 6px 0 0; font-size: 16px; color: #aaa; }
  .fila { display: flex; gap: 10px; width: 100%; max-width: 420px; }
  button { flex: 1; font: 600 17px system-ui, sans-serif; padding: 16px 0; border: 0; border-radius: 10px;
           color: #fff; background: #3b4148; }
  #parar { background: #c62828; font-size: 22px; padding: 22px 0; }
  #armar, #armarB { background: #2e7d32; }
  label { width: 100%; max-width: 420px; display: flex; gap: 10px; align-items: center; }
  input[type=range] { flex: 1; }
</style></head><body>
<div id="estado">conectando…</div>
<h2>Base</h2>
<div class="pad" id="pad"><div class="bola"></div></div>
<label>Velocidad <input id="vel" type="range" min="10" max="100" value="40"><span id="pct">40 %</span></label>
<div class="fila"><button id="armar">ARMAR</button><button id="desarmar">DESARMAR</button><button id="r">r</button></div>
<h2>Brazo — J1 ←→ · J2 ↑↓ · J3 barra</h2>
<div class="fila" style="justify-content:center"><div class="pad" id="padB"><div class="bola"></div></div>
<div id="barra"><div class="bola"></div></div></div>
<label>Duty brazo <input id="duty" type="range" min="10" max="100" value="60"><span id="pctB">60 %</span></label>
<div class="fila"><button id="armarB">ARMAR</button><button id="desarmarB">DESARMAR</button><button id="zB">Cero aquí</button><button id="rB">r</button></div>
<div class="fila"><button id="parar">PARAR TODO</button></div>
<div id="estadoB" class="estado"></div>
<script>
// Joystick genérico: ejes -1..1 (y hacia arriba = +1); al soltar vuelve al centro y llama a alSoltar
function stick(el, soloY, alSoltar) {
  const bola = el.querySelector('.bola'), j = { x: 0, y: 0, tocando: false };
  function mover(e) {
    const r = el.getBoundingClientRect();
    let dx = soloY ? 0 : (e.clientX - r.left) / r.width * 2 - 1, dy = (e.clientY - r.top) / r.height * 2 - 1;
    const n = Math.hypot(dx, dy); if (n > 1) { dx /= n; dy /= n; }
    j.x = dx; j.y = -dy;
    if (!soloY) bola.style.left = (33 + dx * 33) + '%';
    bola.style.top = soloY ? `calc(${50 + dy * 38}% - 30px)` : (33 + dy * 33) + '%';
  }
  j.soltar = () => { j.tocando = false; j.x = j.y = 0; bola.style.left = bola.style.top = ''; alSoltar(); };
  el.onpointerdown = e => { j.tocando = true; el.setPointerCapture(e.pointerId); mover(e); };
  el.onpointermove = e => { if (j.tocando) mover(e); };
  el.onpointerup = el.onpointercancel = j.soltar;
  return j;
}
const $ = id => document.getElementById(id);
const tres = url => { for (let i = 0; i < 3; i++) setTimeout(() => fetch(url), i * 60); };
const base = stick($('pad'), false, () => tres('/cmd?v=0&w=0'));
const frenoB = () => tres('/brazo?d1=0&d2=0&d3=0');
const brazo = stick($('padB'), false, frenoB), codo = stick($('barra'), true, frenoB);
$('vel').oninput = () => $('pct').textContent = $('vel').value + ' %';
$('duty').oninput = () => $('pctB').textContent = $('duty').value + ' %';
setInterval(() => {
  if (base.tocando) {
    const k = $('vel').value / 100;
    fetch('/cmd?v=' + (base.y * k).toFixed(3) + '&w=' + (-base.x * k).toFixed(3));
  }
  if (brazo.tocando || codo.tocando) {
    const k = $('duty').value / 100;
    fetch('/brazo?d1=' + (brazo.x * k).toFixed(3) + '&d2=' + (brazo.y * k).toFixed(3) + '&d3=' + (codo.y * k).toFixed(3));
  }
}, 100);
function comando(c, a, id) {  // el botón destella cuando la Pi recibió el comando
  const b = $(id);
  return fetch('/c?x=' + c + '&a=' + a).then(r => { if (r.ok) { b.style.outline = '4px solid #fff'; setTimeout(() => b.style.outline = '', 300); } });
}
function pararTodo() { [base, brazo, codo].forEach(j => j.soltar()); comando('s', 'base', 'parar'); comando('s', 'brazo', 'parar'); }
$('parar').onclick = pararTodo;
for (const c of ['armar', 'desarmar', 'r']) {
  $(c).onclick = () => comando(c, 'base', c);
  $(c + 'B').onclick = () => comando(c, 'brazo', c + 'B');
}
$('zB').onclick = () => comando('z', 'brazo', 'zB');
setInterval(async () => {
  try {
    const e = JSON.parse(await (await fetch('/estado')).text());
    $('estado').textContent = 'Base: ' + e.base; $('estadoB').textContent = 'Brazo: ' + e.brazo;
  } catch (e) { $('estado').textContent = 'sin conexión con la Pi'; }
}, 500);
document.addEventListener('visibilitychange', () => { if (document.hidden) pararTodo(); });
</script></body></html>
"""


def main():
    rclpy.init()
    nodo = rclpy.create_node("teleop_web")
    pub_vel = nodo.create_publisher(Twist, "/cmd_vel", 10)
    pub_cmd = {a: nodo.create_publisher(String, f"/{a}/comando", 10) for a in ("base", "brazo")}
    ultimo = {a: f"sin /{a}/estado todavía" for a in ("base", "brazo")}
    for a in ultimo:
        nodo.create_subscription(String, f"/{a}/estado", lambda m, a=a: ultimo.update({a: m.data}), 10)

    class Manejador(BaseHTTPRequestHandler):
        def responder(self, cuerpo, tipo="text/plain; charset=utf-8"):
            datos = cuerpo.encode()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/":
                self.responder(PAGINA, "text/html; charset=utf-8")
            elif u.path == "/cmd":
                try:
                    v, w = float(q["v"][0]), float(q["w"][0])
                except (KeyError, ValueError):
                    return self.send_error(400)
                t = Twist()
                t.linear.x = max(-1.0, min(1.0, v)) * V_MAX
                t.angular.z = max(-1.0, min(1.0, w)) * W_MAX
                pub_vel.publish(t)
                self.responder("ok")
            elif u.path == "/brazo":
                try:
                    d = [max(-1.0, min(1.0, float(q[f"d{i}"][0]))) * DUTY_MAX for i in (1, 2, 3)]
                except (KeyError, ValueError):
                    return self.send_error(400)
                if not all(math.isfinite(x) for x in d):
                    return self.send_error(400)
                for i, x in enumerate(d, 1):
                    pub_cmd["brazo"].publish(String(data=f"d {i} {x:.1f}"))
                self.responder("ok")
            elif u.path == "/c":
                c, a = q.get("x", [""])[0], q.get("a", ["base"])[0]
                if c not in COMANDOS or a not in pub_cmd or (c == "z" and a != "brazo"):
                    return self.send_error(400)
                pub_cmd[a].publish(String(data=c))
                self.responder("ok")
            elif u.path == "/estado":
                self.responder(json.dumps(ultimo), "application/json")
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"Teleop web en http://0.0.0.0:{PUERTO} (desde el celular: http://100.116.96.71:{PUERTO})")
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        pub_vel.publish(Twist())
        pub_cmd["brazo"].publish(String(data="s"))
        servidor.shutdown()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
