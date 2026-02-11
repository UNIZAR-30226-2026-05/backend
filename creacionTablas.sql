CREATE TABLE USUARIO (
    nombre VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE PERSONAJE(
    nombre VARCHAR(50) PRIMARY KEY,
    habilidad VARCHAR(50) NOT NULL,
    descripcion VARCHAR(200)
);

CREATE TABLE MINIJUEGO_DINERO(
    nombre VARCHAR(50) PRIMARY KEY,
    descripcion VARCHAR(200)
);

CREATE TABLE MINIJUEGO_ELECCION(
    nombre VARCHAR(50) PRIMARY KEY,
    descripcion VARCHAR(200)
);

CREATE TABLE OBJETO(
    nombre VARCHAR(50) PRIMARY KEY,
    precio INTEGER NOT NULL,
    descripcion VARCHAR(200),
    CONSTRAINT precio_pos CHECK ( precio > 0 )
);

CREATE TABLE CASILLA(
    numero INTEGER PRIMARY KEY,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE C_MINI(
    numero INTEGER PRIMARY KEY,
    minijuego VARCHAR(50) NOT NULL,
    CONSTRAINT fk_minijuego FOREIGN KEY(minijuego) REFERENCES MINIJUEGO_ELECCION(nombre),
    CONSTRAINT fk_casilla FOREIGN KEY (numero) REFERENCES CASILLA(numero) ON DELETE CASCADE,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE C_OBJ(
    numero INTEGER PRIMARY KEY,
    objeto VARCHAR(50) NOT NULL,
    CONSTRAINT fk_objeto FOREIGN KEY(objeto) REFERENCES OBJETO(nombre),
    CONSTRAINT fk_casilla FOREIGN KEY (numero) REFERENCES CASILLA(numero) ON DELETE CASCADE,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE C_MOV(
    numero INTEGER PRIMARY KEY,
    movimiento INTEGER NOT NULL,
    CONSTRAINT fk_casilla FOREIGN KEY (numero) REFERENCES CASILLA(numero) ON DELETE CASCADE,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE SESION_ACTIVA(
    usuario VARCHAR(50) PRIMARY KEY,
    token VARCHAR(100),
    ult_acceso timestamp,
    CONSTRAINT fk_usuario FOREIGN KEY(usuario) REFERENCES USUARIO(nombre) ON DELETE CASCADE
);

CREATE TABLE AMIGOS(
    usuario1 VARCHAR(50),
    usuario2 VARCHAR(50),
    CONSTRAINT fk_usuario1 FOREIGN KEY(usuario1) REFERENCES USUARIO(nombre) ON DELETE CASCADE,
    CONSTRAINT fk_usuario2 FOREIGN KEY(usuario2) REFERENCES USUARIO(nombre) ON DELETE CASCADE,
    PRIMARY KEY(usuario1, usuario2)
);

CREATE TABLE SOLICITUD(
    solicitante VARCHAR(50),
    solicitado VARCHAR(50),
    CONSTRAINT fk_solicitante FOREIGN KEY(solicitante) REFERENCES USUARIO(nombre) ON DELETE CASCADE,
    CONSTRAINT fk_solicitado FOREIGN KEY(solicitado) REFERENCES USUARIO(nombre) ON DELETE CASCADE,
    PRIMARY KEY(solicitante,solicitado)
);

CREATE TABLE PARTIDA_ACTIVA(
    id INTEGER PRIMARY KEY, 
    jugador VARCHAR(50),
    hay_barrera BOOLEAN[],
    turno INTEGER,
    minijuego VARCHAR(50),
    personaje VARCHAR(50),
    CONSTRAINT fk_jugador FOREIGN KEY(jugador) REFERENCES USUARIO(nombre),
    CONSTRAINT fk_personaje FOREIGN KEY(personaje) REFERENCES PERSONAJE(nombre),
    CONSTRAINT turno_positivo CHECK ( turno > 0 )
);

CREATE TABLE JUGANDO(
    nombre_jugador VARCHAR(50),
    id_partida INTEGER,
    personaje VARCHAR(50),
    dinero INTEGER NOT NULL,
    casilla INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    CONSTRAINT fk_partida FOREIGN KEY(id_partida) REFERENCES PARTIDA_ACTIVA(id) ON DELETE CASCADE,
    CONSTRAINT fk_personaje FOREIGN KEY(personaje) REFERENCES PERSONAJE(nombre),
    CONSTRAINT fk_jugador FOREIGN KEY(nombre_jugador) REFERENCES USUARIO(nombre),
    CONSTRAINT dinero_pos CHECK ( dinero >= 0 ),
    CONSTRAINT casilla_pos CHECK ( casilla >= 0 ),
    CONSTRAINT numeroCorrecto CHECK ( numero >= 1  and numero <= 4 ),
    PRIMARY KEY (nombre_jugador, id_partida)
);