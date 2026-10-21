from glob import glob

from setuptools import find_packages, setup

paquete = 'mision'

setup(
    name=paquete,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + paquete]),
        ('share/' + paquete, ['package.xml']),
        ('share/' + paquete + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Héctor Velázquez',
    maintainer_email='hvelazquez@fiuna.edu.py',
    description='Misión mínima del recolector: detectar, localizar quieto y agarrar el limón',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'nodo_mision = mision.nodo_mision:main',
            'marcar_gps = mision.marcar_gps:main',
        ],
    },
)
