from glob import glob

from setuptools import find_packages, setup

paquete = 'simulacion'

setup(
    name=paquete,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + paquete]),
        ('share/' + paquete, ['package.xml']),
        ('share/' + paquete + '/launch', glob('launch/*.launch.py')),
        ('share/' + paquete + '/urdf', glob('urdf/*')),
        ('share/' + paquete + '/worlds', glob('worlds/*')),
        ('share/' + paquete + '/config', glob('config/*')),
        ('share/' + paquete + '/models/limonero', glob('models/limonero/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Héctor Velázquez',
    maintainer_email='hvelazquez@fiuna.edu.py',
    description='Simulación en Gazebo Harmonic del recolector de limones en una hilera',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'brazo_sim = simulacion.brazo_sim:main',
            'limones_sim = simulacion.limones_sim:main',
        ],
    },
)
