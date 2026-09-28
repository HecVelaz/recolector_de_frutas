###elementos robot recogedor de limones
contexto del robot:
Robot movil recogedor de limones 
la parte movil cuenta con 2 motores DC para traccion y 2 ruedas locas
la parte superior es un robot tipo uarm , 3 grados de libertad RRR+manipulador 
el manipulador tiene 2 servos de alto torque uno de apertura y otro de rotacion sobre su eje longitudinal 
elementos a interconectar todos entre si
- x1 Raspberry pi 5 4 Gb ram 
- x1 esp32 s3 
- x1 esp32 32D
- x2 camaras Noir para la pi 5 (para la vision estereo)
- 1xMotor 36GP-555 160 rpm para la base rotativa 1ra articulacion (necesita control lazo cerrado)
- x2 motores DC 5840-31zy para articulaciones (necesita control lazo cerrado)
- x2 servo de alto torque para manipulador: DSSERVO RDS3218 digital, 20 kg·cm, 4,8-6,8 V (foto en `imagen_pinza/`); uno de apertura y otro de giro
- x3 drivers IBT-2 BTS 7960 para los motores dc 36gp
- x1 driver l298n para los motores articulares 
- x2 Motor DC 895 planetario 42 mm con encoder, 12 V, 53 rpm, eje D 8 mm para traccion ruedas (necesita control cerrado)
  (corregido el 28/09/2026: antes decía 36GP-555 53 rpm)
- x1 gps up501
- x1 imu mpu 9250 sin magnetometro
- x1 lidar 
- x3 sensor Ultrasonico hcsr04
- x4 bumpers o finales de carrera cant minima
TPF R1 grupo 2 son los trabajos que se entregan en la catedra de robotica 1 , se evalua solo el brazo. 
TPF R2 son los trabajos que se entregan en la catedra robotica 2 , se evalua el robot movil.
De la guia TPF se elijio limon opcion 6 (RRR - Limon), en vez de succion se usara agarre y traccion con manipulador tipo pinza que rota sobre su eje 
actualidad 27 de septiembre
Solo se tienen pruebas preliminares de los sensores imu , gps y lazo abierto del motor de la base de 160 rpm y prueba lazo abierto un motor de articulacion
en la pi 5 se corre ubuntu 24.04.5 lts noble con ros 2 jazzy , alli se tienen algunas pruebas de vision estereo calibrado por opencv pero no validado porque no se tiene todavia un soporte para las camaras asi que no se continuo 
los archivos estan en el github 
se cuenta con una notebook dell 5458 inspiron de 8 gb ram con ubuntu 24.04.5.1 noble y ros 2 jazzy

