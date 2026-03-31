INSERT INTO USUARIOS.USUARIO (nombre, password) 
VALUES 
    ('Eduardo', '$2b$12$fgsc6y4lf27fMRBAwmjPkOIL55uA8zOSi.KdQTr.VfSXHd6zl7FbO'),
    ('Lorien', '$2b$12$ftpTFKR/kF3qDouKX/PDf.dgEnIh9qFARstmGYBhnUFieJ/SUSRyK'),
    ('Alexit', '$2b$12$0xT6lkg.9aHG3OqP1O5U4uF1.jWcuHNG8/JWMIbCC0gYJbfdXejvW'),
    ('Alonso', '$2b$12$4CdEomaDwyjXwGeWNFz42e5aHdYBcaU9gCZiJ3FbGK6Y5UUsAJFWa'),
    ('Juanma', '$2b$12$cCoDk1mu/QyywlXuwWcTHueIl81Hnpu8pD6FaPiaT3d/sThXTStWC'),
    ('Dani', '$2b$12$M3wGjXpJKLTg6v5EanQ8AuL93TItFBDLfjPnR7zxyPq6GAY5nGWYS'),
    ('Salas', '$2b$12$CqEvGpDBZCVn85SahVgbkeuVVquNENWw/ryHiYuFVhZ.zu3itodAu'),
    ('Aritz', '$2b$12$d.QZOKG1AYWBxq1P/PNuJuXHkn.pE/Fw2c9cZ1buFjxtsmZP1pfiC');

INSERT INTO JUEGO.PERSONAJE(nombre, habilidad, descripcion)
VALUES
    ('Banquero', 'Prestamo sin devolución', 'Lo que seria un prestamo, vamos, un robo'),
    ('Videojugador', 'El juego en tus manos', 'Decidiras cual sera el siguiente minijuego para elegir orden'),
    ('Escapista', 'Reduccion de penalizaciones','Ninguna penalizacion te afectara como al resto de personajes'),
    ('Vidente', 'Vision anticipada', 'Podras ver el resultado de los dados antes de jugar el minijuego de eleccion de orden de tirada');

INSERT INTO JUEGO.OBJETO(nombre, precio, descripcion)
VALUES
    ('Avanzar Casillas',1, 'El jugador que elijas avanza un numero de casillas aleatorias (0-3)'),
    ('Retroceder Casillas',1, 'El jugador que elijas retrocede un numero de casillas aleatorias (0-3)'),
    ('Barrera', 2, 'Coloca una barrera en el tablero'),
    ('Mejorar Dados',1, 'Mejora los dados en uno del jugador que elijas para esta tirada'),
    ('Empeorar Dados',1, 'Empeora los dados en uno del jugador que elijas para esta tirada'),
    ('Ruleta',1, 'Tira una ruleta para conseguir un objeto aleatorio'),
    ('Quitar Turno',1, 'Haz que un jugador no tire en este turno'),
    ('Salvavidas',1, 'Te salvará de tu próxima penalización que obtengas');

INSERT INTO JUEGO.MINIJUEGO(nombre)
VALUES
    ('Tren'),
    ('Reflejos'),
    ('Cortar pan'),
    ('Cronometro ciego'),
    ('Mayor o Menor'),
    ('Mano de Poker'),
    ('Doble o Nada'),
    ('Dilema del Prisionero');

INSERT INTO JUEGO.MINIJUEGO_DINERO(nombre,descripcion)
VALUES
    ('Mano de Poker', 'Jugareis una mano entre todos'),
    ('Dilema del Prisionero', 'Elige entre pactar o traicionar'),
    ('Doble o Nada', 'O ganas o pierdes');

INSERT INTO JUEGO.MINIJUEGO_ELECCION(nombre,descripcion)
VALUES  
    ('Tren', 'Pasajeros al tren, cuenta bien'),
    ('Reflejos','¿Ser rapido es tu virtud?'),
    ('Cortar pan', 'Corta por la mitad para ganar'),
    ('Cronometro ciego', 'Manten la concentracion y no pierdas el tiempo'),
    ('Mayor o Menor', 'Pues mas o menos');

-- CAMBIAR CASILLAS ACORDES AL TABLERO
INSERT INTO JUEGO.CASILLA(numero, tipo)
VALUES
    (0, 'normal'),        -- Casilla de salida
    (1, 'normal'),
    (4, 'normal'),
    (5, 'normal'),
    (6, 'normal'),
    (8, 'normal'),
    (13, 'normal'),
    (20, 'normal'),
    (21, 'normal'),
    (27, 'normal'),
    (28, 'normal'),
    (34, 'normal'),
    (36, 'normal'),
    (40, 'normal'),
    (44, 'normal'),
    (48, 'normal'),
    (52, 'normal'),
    (56, 'normal'),
    (59, 'normal'),
    (63, 'normal'),
    (65, 'normal'),
    (68, 'normal'),
    (69, 'normal'),
    (71, 'normal');       -- Casilla final

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
    (2, B'1'),
    (12, B'1'),
    (23, B'1'),
    (31, B'1'),
    (41, B'1'),
    (50, B'1'),
    (60, B'1'),
    (18, B'0'),
    (24, B'0'),
    (38, B'0'),
    (45, B'0'),
    (58, B'0'),
    (64, B'0');

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
