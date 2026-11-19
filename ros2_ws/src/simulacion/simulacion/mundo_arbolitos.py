"""Mundo de la demo: un banderín ArUco y una hilera de arbolitos, afuera (tierra y sol).

Lo arma la misma hilera que usa la navegación (mision/navegacion.py: lo medido mirando el banderín de frente), así el
mundo y el plan no pueden quedar distintos. El banderín está en el origen mirando a -x; con la hilera por defecto los
árboles quedan en x = 1,5 / 3 / 4,5 m, y = 0. Limones cosechables `limon_<10·árbol + j>` (limones_sim los lee del
mundo): 8 por árbol, cada 45° alrededor del tronco, a 12 cm del eje (medido: 10-14 cm), de 32 a 52 cm del piso (el
brazo simulado no llega más arriba: Q3_LIM de brazo_ik).

    ros2 run simulacion mundo_arbolitos --arboles 3 --separacion 1.5 > arbolitos.sdf
"""

import argparse
import json
import math
import sys

from mision.navegacion import arboles_en_odom, hilera_recta, leer_hilera, rumbo_ida

BANDERIN, MIRA = (0.0, 0.0), math.pi
RADIO_LIMONES = 0.12
ALTURAS = (0.32, 0.37, 0.42, 0.47, 0.52)
N_LIMONES = 8

CABECERA = """<?xml version="1.0"?>
<!-- GENERADO por simulacion/mundo_arbolitos.py ({descripcion}): no editar a mano.
     Demo afuera: banderín ArUco ID 0 en el origen mirando a -x y la hilera de arbolitos detrás. -->
<sdf version="1.9">
  <world name="arbolitos">
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>

    <!-- FIUNA (aproximado): el GPS simulado da coordenadas de ahí (solo para la rúbrica); x = este, y = norte -->
    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>-25.3320</latitude_deg>
      <longitude_deg>-57.5190</longitude_deg>
      <elevation>120</elevation>
      <heading_deg>0</heading_deg>
    </spherical_coordinates>

    <scene>
      <ambient>0.45 0.45 0.45 1</ambient>
      <background>0.55 0.75 0.95 1</background>
    </scene>

    <!-- Sol de media tarde, con sombras -->
    <light type="directional" name="sol">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>1.0 0.97 0.9 1</diffuse>
      <specular>0.3 0.3 0.3 1</specular>
      <direction>-0.5 0.4 -0.75</direction>
    </light>

    <model name="suelo">
      <static>true</static>
      <link name="link">
        <collision name="c"><geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry></collision>
        <visual name="v">
          <geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
          <material><ambient>0.9 0.9 0.9 1</ambient><diffuse>1 1 1 1</diffuse><specular>0.1 0.1 0.1 1</specular><pbr><metal><albedo_map>model://texturas/tierra.png</albedo_map><roughness>0.95</roughness><metalness>0</metalness></metal></pbr></material>
        </visual>
      </link>
    </model>

    <include>
      <name>banderin</name>
      <uri>model://banderin</uri>
      <pose>{bx:.3f} {by:.3f} 0 0 0 {byaw:.6f}</pose>
    </include>
"""

ARBOL = """
    <include>
      <name>arbolito_{k}</name>
      <uri>model://arbolito</uri>
      <pose>{x:.3f} {y:.3f} 0 0 0 {yaw:.6f}</pose>
    </include>
"""

LIMON = """    <model name="limon_{n}">
      <pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose>
      <link name="link">
        <gravity>false</gravity>
        <inertial><mass>0.1</mass><inertia><ixx>3e-5</ixx><iyy>3e-5</iyy><izz>3e-5</izz></inertia></inertial>
        <visual name="v">
          <geometry><ellipsoid><radii>0.028 0.028 0.034</radii></ellipsoid></geometry>
          <material><ambient>0.9 0.9 0.9 1</ambient><diffuse>1 1 1 1</diffuse><specular>0.15 0.15 0.15 1</specular><pbr><metal><albedo_map>model://texturas/limon.png</albedo_map><roughness>0.5</roughness><metalness>0</metalness></metal></pbr></material>
        </visual>
      </link>
    </model>
"""


def limones(arboles, psi):
    """{n: (x, y, z)}: 8 por árbol (n = 10·árbol + j), cada 45° desde el rumbo de la hilera."""
    out = {}
    for k, (ax, ay) in enumerate(arboles, start=1):
        for j in range(N_LIMONES):
            a = psi + j * 2 * math.pi / N_LIMONES
            out[10 * k + j] = (ax + RADIO_LIMONES * math.cos(a), ay + RADIO_LIMONES * math.sin(a),
                               ALTURAS[(j + k) % len(ALTURAS)])
    return out


def generar(hilera_mm, descripcion=''):
    """Hilera (dict como el JSON, en mm) -> texto SDF del mundo."""
    h = leer_hilera(hilera_mm)
    arboles = arboles_en_odom(BANDERIN, MIRA, h)
    psi = rumbo_ida(BANDERIN, arboles)
    sdf = CABECERA.format(descripcion=descripcion, bx=BANDERIN[0], by=BANDERIN[1], byaw=MIRA)
    sdf += ''.join(ARBOL.format(k=k, x=x, y=y, yaw=psi) for k, (x, y) in enumerate(arboles, start=1))
    sdf += '\n' + ''.join(LIMON.format(n=n, x=x, y=y, z=z) for n, (x, y, z) in limones(arboles, psi).items())
    return sdf + '  </world>\n</sdf>\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hilera', help='JSON de la hilera (mision/config/hilera_arboles.json); si no, una recta')
    ap.add_argument('--arboles', type=int, default=3)
    ap.add_argument('--separacion', type=float, default=1.5, help='m entre árboles (hilera recta)')
    ap.add_argument('--banderin', type=float, default=1.5, help='m del banderín al árbol 1 (hilera recta)')
    a = ap.parse_args(argv)
    if a.hilera:
        with open(a.hilera) as f:
            j = json.load(f)
        j['arboles'] = j['arboles'][:a.arboles]
        desc = f'{a.hilera}, {a.arboles} árboles'
    else:
        j = hilera_recta(a.arboles, a.separacion, a.banderin)
        desc = f'--arboles {a.arboles} --separacion {a.separacion} --banderin {a.banderin}'
    sys.stdout.write(generar(j, desc))


if __name__ == '__main__':
    main()
