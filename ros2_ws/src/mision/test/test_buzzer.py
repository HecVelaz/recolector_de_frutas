"""Avisos del buzzer (sin ROS ni GPIO): suenan solo en los cambios, nunca con el primer mensaje."""

from mision.nodo_buzzer import ENLACE_S, SONIDOS, Avisos

PARADA = 'DESARMADA modo=parado seguridad=sin comandos imu=ok rueda_izq=ninguna rueda_der=ninguna'
SETA = 'DESARMADA modo=parado seguridad=EMERGENCIA (seta) SETA imu=ok rueda_izq=ninguna rueda_der=ninguna'
ARMADA = 'ARMADA modo=parado seguridad=ok imu=ok rueda_izq=ninguna rueda_der=ninguna'
BAJA = 'ARMADA modo=parado seguridad=ok BATERIA_BAJA imu=ok rueda_izq=ninguna rueda_der=ninguna'


def test_seta_desde_el_encendido_no_suena_y_al_apretarla_si():
    a = Avisos()
    assert a.base(SETA, 0) == []          # se prende con la seta apretada: callado
    assert a.base(PARADA, 1) == []        # soltarla no suena
    assert a.base(SETA, 2) == ['emergencia']
    assert a.base(SETA, 3) == []          # mientras dura, no repite


def test_armado_bateria_y_bumper():
    a = Avisos()
    a.base(PARADA, 0)
    assert a.base(ARMADA, 1) == ['armada']
    assert a.base(BAJA, 2) == ['bateria']
    assert a.bumpers(0) == []
    assert a.bumpers(0b010) == ['emergencia']
    assert a.bumpers(0) == []


def test_homing_y_enlace_perdido_y_recuperado():
    a = Avisos()
    assert a.brazo('c=000;e=0,0,0', 0) == []
    assert a.brazo('c=111;e=0,0,0', 1) == ['homing']
    assert a.vigilar(1 + ENLACE_S / 2) == []
    assert a.vigilar(1 + ENLACE_S + 0.1) == ['enlace']
    assert a.vigilar(1 + ENLACE_S + 1) == []
    assert a.brazo('c=111;e=0,0,0', 9) == ['listo']


def test_todos_los_sonidos_son_audibles():
    for notas in SONIDOS.values():
        assert all(hz == 0 or 650 <= hz <= 4000 for hz, _ in notas)
