"""Inicio explícito en la Pi, con clave local y sin modificar servicios existentes."""
import argparse
import ipaddress
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description='Arturito: observación y prueba de base a velocidad cero')
    parser.add_argument('--source', choices=['simulation', 'estado', 'ros2'], default='simulation')
    parser.add_argument('--data-dir', help='Directorio existente para conservar clave y geocerca')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--simulate-base-output', action='store_true')
    bench = parser.add_mutually_exclusive_group()
    bench.add_argument('--bench-base-zero', action='store_true')
    bench.add_argument('--bench-base-pulse', action='store_true')
    bench.add_argument('--physical-manual', action='store_true')
    args = parser.parse_args()
    if args.simulate_base_output and (args.source != 'simulation' or args.host != '127.0.0.1'):
        parser.error('El simulador de mando requiere --source simulation --host 127.0.0.1')
    bench_test = args.bench_base_zero or args.bench_base_pulse
    # El mando escucha solo en loopback o en la IP de Tailscale (100.64.0.0/10: cifrada y solo dispositivos propios)
    tailnet = args.host.startswith('100.') and ipaddress.ip_address(args.host) in ipaddress.ip_network('100.64.0.0/10')
    if (bench_test or args.physical_manual) and (args.source != 'ros2' or (args.host != '127.0.0.1' and not tailnet)
                                or args.port == 8001 or not args.data_dir
                                or os.getenv('ROS_AUTOMATIC_DISCOVERY_RANGE') != 'LOCALHOST'
                                or os.getenv('ROS_STATIC_PEERS')):
        parser.error('La prueba de banco requiere ROS 2 local, loopback o Tailscale, otro puerto y directorio de datos explícito')
    os.chdir(Path(__file__).resolve().parent)
    data = Path(args.data_dir).expanduser().resolve() if args.data_dir else Path('data').resolve()
    data.mkdir(parents=True, exist_ok=True)
    path = data / '.connection-token'
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(secrets.token_urlsafe(24))
    token = path.read_text(encoding='ascii').strip()
    if not token:
        raise ValueError('La clave guardada está vacía')
    os.environ['ARTURITO_TOKEN'] = token
    os.environ['ARTURITO_SOURCE'] = args.source
    os.environ['ARTURITO_DATA_DIR'] = str(data)
    print(f'Puente de observación en puerto {args.port}; origen: {args.source}', flush=True)
    if args.physical_manual:
        print('Mando físico supervisado por loopback. Base con ruedas elevadas.', flush=True)
    elif args.bench_base_pulse:
        print('Prueba de pulso en loopback. Requiere ruedas elevadas y brazo aislado.', flush=True)
    elif args.bench_base_zero:
        print('Prueba de base en loopback. Solo publica armado, desarmado y velocidad cero.', flush=True)
    else:
        print(f'Clave para ingresar en la app: {token}', flush=True)
        print('No habilita movimiento ni aplica geocercas al robot. Ctrl+C detiene solamente este puente.', flush=True)
    import uvicorn
    target = 'bridge:app'
    if args.simulate_base_output:
        from bridge import create_app
        target = create_app(source='simulation', control_dry_run=True, simulate_base_output=True)
    elif bench_test or args.physical_manual:
        from bridge import create_app
        target = create_app(source='ros2', control_dry_run=False, base_zero_test=args.bench_base_zero,
                            base_pulse_test=args.bench_base_pulse, physical_manual=args.physical_manual)
    # 21/11: con el keep-alive de 5 s de uvicorn, la tablet (adb reverse + túnel ssh) no se enteraba del cierre y el
    # primer pedido tras 5 s quietos (p. ej. «Iniciar recolección» después del cero) moría: había que tocar dos veces.
    # 600 s > los 5 min que OkHttp guarda una conexión ociosa: cierra siempre la tablet primero.
    uvicorn.run(target, host=args.host, port=args.port, access_log=False, proxy_headers=False, timeout_keep_alive=600)


if __name__ == '__main__':
    main()
