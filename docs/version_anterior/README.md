# Versión anterior de las conexiones (v0.7)

Copia de cómo estaban las conexiones **antes del 15/10/2026** (commit `bb9263d`), cuando los pines de la S3 no
estaban ordenados por lado de la Freenove (IBT-2 en 4/5 y 6/7, encoders en 15/16 y 17/18, TRIG 10/41/42, ECHO
11/12/13, bumpers 14/21/39, reserva en el 40). Solo para consultar: **no se actualiza**.

- `CONEXIONES.md`: tablas de pines y potencia de entonces.
- `html/conexiones.html`, `html/placa_s3.html`, `html/potencia.html`: las páginas de entonces (abrir en el navegador).

La versión vigente (v0.8) está en `docs/CONEXIONES.md` y `docs/html/`. El firmware con los pines viejos se recupera con
`git show bb9263d:firmware/base/include/pins.h`.
