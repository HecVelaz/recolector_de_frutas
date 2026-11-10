"""Caracteriza una articulación del brazo con motor (firmware/brazo env esp32dev, por serial):
signo, zona muerta a cada lado y escalón de duty en los dos sentidos (K rpm/%, tau, rizado en régimen).

Uso (agente micro-ROS parado, 12 V APAGADOS al arrancar: abrir el puerto resetea la WROOM):
  python prueba_articulacion.py <puerto> [n=2] [duty=35] > j2.csv
El script espera Enter para empezar (prender los 12 V antes). Pulsos cortos y alternados (+/-) para que el
brazo no se vaya; corta si q se aleja más de Q_MAX grados del arranque. Seta a mano.
w del log = rpm a la salida del motorreductor (articulación = w / 5 con los helicoidales 15 -> 75).
"""
import sys
import time

import serial

puerto = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
duty = float(sys.argv[3]) if len(sys.argv) > 3 else 35.0
Q_MAX = 30.0      # grados de articulación desde el arranque
W_ARRANQUE = 2.0  # rpm: por encima, el eje se movió
PASO_ZM = 3.0     # % de duty entre pulsos de la zona muerta

s = serial.Serial()
s.port, s.baudrate, s.timeout = puerto, 115200, 0.02
s.dtr = s.rts = False
s.open()
print("# esperando el arranque de la WROOM...", file=sys.stderr)
time.sleep(3.0)
s.reset_input_buffer()

filas = []  # (fase, t_ms, q, w, u)
fase = "inicio"
q0 = None
buf = b""


class Lejos(Exception):
    pass


def mandar(c):
    s.write((c + "\n").encode())


def leer(seg):
    global buf, q0
    fin = time.time() + seg
    while time.time() < fin:
        buf += s.read(512)
        *lineas, buf = buf.split(b"\n")
        for l in lineas:
            l = l.decode(errors="replace").strip()
            p = l.split(",")
            if len(p) == 6 and l[:1].isdigit():
                t, q, w, u = int(p[0]), float(p[2]), float(p[4]), float(p[5])
                q0 = q if q0 is None else q0
                filas.append((fase, t, q, w, u))
                if abs(q - q0) > Q_MAX:
                    raise Lejos(f"q = {q:.1f}°, se alejó más de {Q_MAX}° del arranque")
            elif l:
                print("#", l, file=sys.stderr)


def pulso(pct, seg):
    """d se corta a los 300 ms si no se repite: repetirlo cada 100 ms. Devuelve las filas del pulso."""
    i = len(filas)
    t0 = time.time()
    while time.time() - t0 < seg:
        mandar(f"d {n} {pct:g}")
        leer(0.1)
    mandar("s")
    leer(0.6)  # frena y queda quieto
    return [f for f in filas[i:] if f[4] != 0]


mandar("log 0")
leer(0.3)
mandar("e")
leer(0.5)
input(f"J{n}, duty {duty:g} %. Prender los 12 V, mano en la seta, y Enter para empezar (Ctrl-C para salir)... ")
mandar("r")
leer(0.3)
mandar(f"log {n} 100")
leer(0.5)

res = {}
try:
    # 1) zona muerta: pulsos de 0,4 s, alternando + y -, subiendo de a PASO_ZM
    fase = "zona_muerta"
    zm = {+1: None, -1: None}
    pct = PASO_ZM
    while pct <= 50 and None in zm.values():
        for sg in (+1, -1):
            if zm[sg] is None:
                p = pulso(sg * pct, 0.4)
                if p and max(abs(f[3]) for f in p) > W_ARRANQUE:
                    zm[sg] = pct
                    wm = max((f[3] for f in p), key=abs)
                    print(f"zona muerta {'+' if sg > 0 else '-'}: arranca con {pct:g} % (w = {wm:+.1f} rpm)",
                          file=sys.stderr)
        pct += PASO_ZM
    res["zm"] = zm

    # 2) escalón de duty, +duty y -duty, 1 s cada uno
    for sg in (+1, -1):
        fase = f"escalon_{'+' if sg > 0 else '-'}"
        p = pulso(sg * duty, 1.0)
        if not p:
            print(f"{fase}: sin datos", file=sys.stderr)
            continue
        t = [f[1] for f in p]
        w = [f[3] for f in p]
        cola = [w[i] for i in range(len(p)) if t[-1] - t[i] < 400]  # últimos 0,4 s
        wf = sum(cola) / len(cola)
        rizo = (sum((x - wf) ** 2 for x in cola) / len(cola)) ** 0.5
        i63 = next((i for i in range(len(p)) if abs(w[i]) >= 0.63 * abs(wf)), None)
        tau = (t[i63] - t[0]) / 1000 if i63 is not None else float("nan")
        res[fase] = (wf, wf / (sg * duty), tau, rizo)
        print(f"{fase}: w final {wf:+.1f} rpm, K = {wf / (sg * duty):.3f} rpm/%, tau = {tau:.3f} s, "
              f"rizado {rizo:.2f} rpm ({100 * rizo / max(abs(wf), 1e-6):.0f} %)", file=sys.stderr)
except Lejos as e:
    print(f"CORTE: {e}", file=sys.stderr)
except KeyboardInterrupt:
    print("CORTE: Ctrl-C", file=sys.stderr)
finally:
    mandar("s")
    mandar("log 0")
    time.sleep(0.5)
    s.close()

print("fase,t_ms,q,w_rpm,u_pct")
for f in filas:
    print(",".join(str(x) for x in f))

# signo: con duty + la velocidad debería salir +
if "escalon_+" in res:
    ok = res["escalon_+"][0] > 0
    print(f"signo: con duty + w sale {'+ (ENC_INVERTIDO bien)' if ok else '- -> invertir ENC_INVERTIDO'}; "
          "MOTOR_INVERTIDO según para dónde se movió el brazo (mirarlo)", file=sys.stderr)
