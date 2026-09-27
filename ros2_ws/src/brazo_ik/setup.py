from setuptools import find_packages, setup

paquete = 'brazo_ik'

setup(
    name=paquete,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + paquete]),
        ('share/' + paquete, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Héctor Velázquez',
    maintainer_email='hvelazquez@fiuna.edu.py',
    description='Cinemática inversa del brazo del recolector de limones (Entrega 4 de R1)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'nodo_ik = brazo_ik.nodo_ik:main',
        ],
    },
)
