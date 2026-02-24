INSERT INTO USUARIOS.USUARIO (nombre, password) 
VALUES 
    ('Eduardo', 'Eduardo'),
    ('Lorien', 'Lorien'),
    ('Alexit', 'Alexit'),
    ('Alonso', 'Alonso'),
    ('Juanma', 'Juanma'),
    ('Dani', 'Dani'),
    ('Salas', 'Salas'),
    ('Aritz', 'Aritz');

INSERT INTO JUEGO.PERSONAJE(nombre, habilidad, descripcion)
VALUES
    ('Banquero', 'Shalom', 'Como me gusta ciudad de Tel Avid'),
    ('Videojugador', 'Jugar', 'Viva vegetta777'),
    ('Escapista', 'Escapar','Me fui klk'),
    ('Vidente', 'Ver', 'Te veo los pensamientos');

INSERT INTO JUEGO.OBJETO(nombre, precio, descripcion)
VALUES
    ('Avanzar Casillas',1),
    ('Retroceder Casillas',1),
    ('Barrera', 2),
    ('Mejorar Dados',1),
    ('Empeorar Dados',1),
    ('Ruleta',1),
    ('Quitar Turno',1),
    ('Salvavidas',1);

INSERT INTO JUEGO.MINIJUEGO(nombre,descripcion)
VALUES
    ('Tren');
    ('Carrera de caballos'),
    ('Reflejos',),
    ('Cortar barra'),
    ('Cronometro Ciego'),
    ('Mayor o Menor'),
    ('Mano de Poker'),
    ('Doble o Nada'),
    ('Dilema del Prisionero');

INSERT INTO JUEGO.MINIJUEGO_DINERO(nombre,descripcion)
VALUES
    ('Mano de Poker'),
    ('Doble o Nada');

INSERT INTO JUEGO.MINIJUEGO_ELECCION(nombre,descripcion)
VALUES  
    ('Tren');
    ('Carrera de caballos'),
    ('Reflejos',),
    ('Cortar barra'),
    ('Cronometro Ciego'),
    ('Mayor o Menor');

INSERT INTO JUEGO.CASILLA(numero)
VALUES
    (0),        -- Casilla de salida
    (1),
    (4),
    (5),
    (6),
    (8),
    (13),
    (20),
    (21),
    (27),
    (28),
    (34),
    (36),
    (40),
    (44),
    (48),
    (52),
    (56),
    (59),
    (63),
    (65),
    (68),
    (69),
    (70),
    (71);       -- Casilla final

INSERT INTO JUEGO.C_MOV(numero, movimiento)
VALUES
    (3, 5),    
    (7, -3),   
    (10, 3),   
    (11, -5),  
    (16, -3),  
    (19, 3),   
    (25, -5),  
    (29, 5),   
    (33, -5),  
    (37, -3),  
    (39, 5),   
    (43, -3),  
    (49, 3),   
    (53, -5),  
    (57, -5),  
    (61, -5),  
    (70, -5);  

INSERT INTO JUEGO.C_OBJ(numero,ruleta)
VALUES
    (2, 1),
    (12, 1),
    (23, 1),
    (31, 1),
    (41, 1),
    (50, 1),
    (60, 1),
    (18, 0),
    (24, 0),
    (38, 0),
    (45, 0),
    (58, 0),
    (64, 0);

INSERT INTO JUEGO.C_MINI(numero, minijuego)
VALUES
    (9, 'Doble o Nada'),
    (14, 'Dilema del Prisionero'),
    (22, 'Doble o Nada'),
    (26, 'Dilema del Prisionero'),
    (35, 'Doble o Nada'),
    (42, 'Doble o Nada'),
    (47, 'Dilema del Prisionero'),
    (54, 'Doble o Nada'),
    (62, 'Doble o Nada'),
    (66, 'Dilema del Prisionero'),
    (15, 'Mano de Poker'),
    (32, 'Mano de Poker'),
    (46, 'Mano de Poker'),
    (55, 'Mano de Poker');
