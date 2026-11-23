#!/usr/bin/env python3
"""Diagnóstico de la S3 colgada tras reiniciar la Pi (23/11), sin resetear el chip.

Hipótesis: el USB de la S3 (HWCDC) quedó marcado "sin host" y guarda lo que manda en vez de enviarlo; solo vuelve
a "conectado" al RECIBIR algo, y el agente micro-ROS nunca habla primero. Este script, con el agente de la base
DETENIDO: (1) escucha 3 s; (2) le manda unos bytes (el transporte micro-ROS descarta lo que no esté entre 0x7E);
(3) escucha otros 3 s. Si en (1) no llega nada y en (3) sí, la hipótesis se confirma.
Uso: python3 despertar_s3.py [/dev/serial/by-id/usb-Espressif...]
"""
import glob
import os
import sys
import termios
import time


def listen(fd, seconds):
    total, end = 0, time.time() + seconds
    while time.time() < end:
        try:
            total += len(os.read(fd, 4096))
        except BlockingIOError:
            time.sleep(0.02)
    return total


port = sys.argv[1] if len(sys.argv) > 1 else glob.glob('/dev/serial/by-id/usb-Espressif_USB_JTAG*')[0]
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
attrs = termios.tcgetattr(fd)
attrs[0] = attrs[1] = attrs[3] = 0          # crudo: sin eco ni traducciones
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[4] = attrs[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, attrs)
before = listen(fd, 3)
os.write(fd, b'\x00' * 16)
after = listen(fd, 3)
os.close(fd)
print(f'antes de escribirle: {before} bytes; después: {after} bytes')
print('HIPÓTESIS CONFIRMADA: despertarla escribiéndole' if before == 0 and after > 0 else
      'la S3 ya transmitía (no era esto)' if before > 0 else 'no transmite ni después: otra causa')
