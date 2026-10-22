"""Teleoperado de la base desde el navegador del celular: joystick táctil → /cmd_vel.

Uso (en la Pi, con el agente de la base corriendo):
  source /opt/ros/jazzy/setup.bash
  python3 teleop_web.py            # y en el celular: http://100.116.96.71:8000 (Tailscale)

Solo la biblioteca estándar y rclpy (sin rosbridge). La página manda la consigna cada 100 ms mientras se toca el
joystick; si deja de llegar (se suelta, se cierra la página o se corta la red), no se publica nada y la S3 frena
sola por su watchdog de 300 ms.
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import String

PUERTO = 8000
V_MAX, W_MAX = 0.25, 1.0  # los mismos topes que CFG_DIF de la base
COMANDOS = {"armar", "desarmar", "s", "r"}

PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Arturito</title>
<style>
  body { margin: 0; font: 16px system-ui, sans-serif; background: #111; color: #eee; touch-action: none;
         user-select: none; -webkit-user-select: none; display: flex; flex-direction: column; align-items: center;
         gap: 14px; padding: 14px; box-sizing: border-box; min-height: 100vh; }
  #estado { font: 13px ui-monospace, monospace; background: #222; padding: 8px 10px; border-radius: 8px;
            width: 100%; max-width: 420px; box-sizing: border-box; min-height: 3em; word-break: break-word; }
  #pad { width: min(80vw, 320px); height: min(80vw, 320px); border-radius: 50%; background: #262626;
         border: 2px solid #444; position: relative; }
  #bola { width: 34%; height: 34%; border-radius: 50%; background: #3a7bd5; position: absolute;
          left: 33%; top: 33%; }
  .fila { display: flex; gap: 10px; width: 100%; max-width: 420px; }
  button { flex: 1; font: 600 17px system-ui, sans-serif; padding: 16px 0; border: 0; border-radius: 10px;
           color: #fff; background: #3b4148; }
  #parar { background: #c62828; font-size: 22px; padding: 22px 0; }
  #armar { background: #2e7d32; }
  label { width: 100%; max-width: 420px; display: flex; gap: 10px; align-items: center; }
  input[type=range] { flex: 1; }
</style></head><body>
<div id="estado">conectando…</div>
<div id="pad"><div id="bola"></div></div>
<label>Velocidad <input id="vel" type="range" min="10" max="100" value="40"><span id="pct">40 %</span></label>
<div class="fila"><button id="armar">ARMAR</button><button id="desarmar">DESARMAR</button><button id="r">r</button></div>
<div class="fila"><button id="parar">PARAR</button></div>
<script>
const pad = document.getElementById('pad'), bola = document.getElementById('bola');
const vel = document.getElementById('vel'), pct = document.getElementById('pct');
let x = 0, y = 0, tocando = false;
vel.oninput = () => pct.textContent = vel.value + ' %';
function mover(e) {
  const r = pad.getBoundingClientRect(), R = r.width / 2;
  let dx = (e.clientX - r.left - R) / R, dy = (e.clientY - r.top - R) / R;
  const n = Math.hypot(dx, dy); if (n > 1) { dx /= n; dy /= n; }
  x = dx; y = dy;
  bola.style.left = (33 + dx * 33) + '%'; bola.style.top = (33 + dy * 33) + '%';
}
function soltar() { tocando = false; x = y = 0; bola.style.left = bola.style.top = '33%';
  for (let i = 0; i < 3; i++) setTimeout(() => fetch('/cmd?v=0&w=0'), i * 60); }
pad.onpointerdown = e => { tocando = true; pad.setPointerCapture(e.pointerId); mover(e); };
pad.onpointermove = e => { if (tocando) mover(e); };
pad.onpointerup = pad.onpointercancel = soltar;
setInterval(() => {
  if (!tocando) return;
  const k = vel.value / 100;
  fetch('/cmd?v=' + (-y * k).toFixed(3) + '&w=' + (-x * k).toFixed(3));
}, 100);
function comando(c) {  // el botón destella cuando la Pi recibió el comando
  const b = document.getElementById(c === 's' ? 'parar' : c);
  fetch('/c?x=' + c).then(r => { if (r.ok) { b.style.outline = '4px solid #fff'; setTimeout(() => b.style.outline = '', 300); } });
}
document.getElementById('parar').onclick = () => { soltar(); comando('s'); };
document.getElementById('armar').onclick = () => comando('armar');
document.getElementById('desarmar').onclick = () => comando('desarmar');
document.getElementById('r').onclick = () => comando('r');
setInterval(async () => {
  try { document.getElementById('estado').textContent = await (await fetch('/estado')).text(); }
  catch (e) { document.getElementById('estado').textContent = 'sin conexión con la Pi'; }
}, 500);
document.addEventListener('visibilitychange', () => { if (document.hidden) soltar(); });
</script></body></html>
"""


def main():
    rclpy.init()
    nodo = rclpy.create_node("teleop_web")
    pub_vel = nodo.create_publisher(Twist, "/cmd_vel", 10)
    pub_cmd = nodo.create_publisher(String, "/base/comando", 10)
    ultimo = {"estado": "sin /base/estado todavía"}
    nodo.create_subscription(String, "/base/estado", lambda m: ultimo.update(estado=m.data), 10)

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
            elif u.path == "/c":
                c = q.get("x", [""])[0]
                if c not in COMANDOS:
                    return self.send_error(400)
                pub_cmd.publish(String(data=c))
                self.responder("ok")
            elif u.path == "/estado":
                self.responder(ultimo["estado"])
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
        servidor.shutdown()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
