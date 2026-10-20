"""Escalón de duty en las dos ruedas con log a 100 Hz (firmware por serial: env esp32s3 o serial_motores).

Uso (en la Pi, con el agente micro-ROS parado y las ruedas en el aire):
  python escalon_tau.py /dev/serial/by-id/usb-Espressif_... [duty] > escalon.csv
Saca τ de cada rueda: tiempo hasta el 63 % de la velocidad final (promedio del último medio segundo del escalón).
"""
import sys
import time

import serial

puerto, duty = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
s = serial.Serial()
s.port, s.baudrate, s.timeout = puerto, 115200, 0.05
s.dtr = s.rts = False  # no tocar EN/BOOT al abrir
s.open()
time.sleep(1.0)
s.reset_input_buffer()


def mandar(c):
    s.write((c + "\n").encode())


lineas = []


def leer(seg):
    fin = time.time() + seg
    while time.time() < fin:
        l = s.readline().decode(errors="replace").strip()
        if l:
            lineas.append(l)


mandar("s")
leer(0.5)
mandar("log 100")
leer(0.5)
t0 = time.time()
while time.time() - t0 < 2.0:  # d se corta a los 300 ms si no se repite
    mandar(f"d {duty} {duty}")
    leer(0.1)
mandar("s")
leer(1.0)
mandar("log 0")
leer(0.3)
s.close()

filas = [l.split(",") for l in lineas if l[:1].isdigit() and l.count(",") == 11]
print("t_ms,rpm_izq,rpm_der,u_izq,u_der")
for f in filas:
    print(f"{f[0]},{f[4]},{f[6]},{f[7]},{f[8]}")
otras = [l for l in lineas if not (l[:1].isdigit() and l.count(",") == 11)]
for l in otras:
    print("#", l, file=sys.stderr)

# τ: desde el primer u > 0 hasta el 63 % de la velocidad final
t = [int(f[0]) for f in filas]
u = [float(f[7]) for f in filas]
on = [i for i, x in enumerate(u) if x > 0]
if not on:
    sys.exit("sin escalón en el log")
i0, i1 = on[0], on[-1]
for k, nom in ((4, "izq"), (6, "der")):
    w = [float(f[k]) for f in filas]
    cola = [w[i] for i in range(i0, i1 + 1) if t[i] - t[i1] > -500]
    wf = sum(cola) / len(cola)
    i63 = next((i for i in range(i0, i1 + 1) if w[i] >= 0.63 * wf), None)
    tau = (t[i63] - t[i0]) / 1000 if i63 is not None else float("nan")
    print(f"{nom}: final {wf:.1f} rpm con {duty:.0f} %, tau = {tau:.3f} s", file=sys.stderr)
