CREATE SCHEMA USUARIOS;
CREATE SCHEMA JUEGO;
CREATE SCHEMA PARTIDAS;

/* ESQUEMA USUARIOS */
CREATE TABLE USUARIOS.USUARIO (
    nombre VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE USUARIOS.SESION_ACTIVA(
    usuario VARCHAR(50) PRIMARY KEY,
    token VARCHAR(100),
    ult_acceso timestamp,
    CONSTRAINT fk_usuario FOREIGN KEY(usuario) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE
);

CREATE TABLE USUARIOS.AMIGOS(
    usuario1 VARCHAR(50),
    usuario2 VARCHAR(50),
    CONSTRAINT fk_usuario1 FOREIGN KEY(usuario1) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
    CONSTRAINT fk_usuario2 FOREIGN KEY(usuario2) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
    --CONSTRAINT amigos_unicos CHECK (usuario1 < usuario2),
    CONSTRAINT usuarios_diferentes CHECK (usuario1 <> usuario2),
    PRIMARY KEY(usuario1, usuario2)
);

CREATE TABLE USUARIOS.SOLICITUD(
    solicitante VARCHAR(50),
    solicitado VARCHAR(50),
    CONSTRAINT fk_solicitante FOREIGN KEY(solicitante) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
    CONSTRAINT fk_solicitado FOREIGN KEY(solicitado) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
    --CONSTRAINT amigos_unicos CHECK (solicitante < solicitado),
    CONSTRAINT usuarios_diferentes CHECK (solicitante <> solicitado),
    PRIMARY KEY(solicitante,solicitado)
);

/* ESQUEMA JUEGO */
CREATE TABLE JUEGO.PERSONAJE(
    nombre VARCHAR(50) PRIMARY KEY,
    habilidad VARCHAR(50) NOT NULL,
    descripcion VARCHAR(200)
);

/*CREATE TYPE tipo_minijuego AS ENUM ('dinero', 'eleccion');*/

CREATE TABLE JUEGO.MINIJUEGO(
    nombre VARCHAR(50) PRIMARY KEY
);

CREATE TABLE JUEGO.MINIJUEGO_DINERO(
    nombre VARCHAR(50) PRIMARY KEY,
    descripcion VARCHAR(200),
    CONSTRAINT fk_minijuego FOREIGN KEY(nombre) REFERENCES JUEGO.MINIJUEGO(nombre)
);

CREATE TABLE JUEGO.MINIJUEGO_ELECCION(
    nombre VARCHAR(50) PRIMARY KEY,
    descripcion VARCHAR(200),
    CONSTRAINT fk_minijuego FOREIGN KEY(nombre) REFERENCES JUEGO.MINIJUEGO(nombre)
);

CREATE TABLE JUEGO.OBJETO(
    nombre VARCHAR(50) PRIMARY KEY,
    precio INTEGER NOT NULL,
    descripcion VARCHAR(200),
    CONSTRAINT precio_pos CHECK ( precio > 0 )
);

CREATE TABLE JUEGO.CASILLA(
    numero INTEGER PRIMARY KEY,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE JUEGO.C_MINI(
    numero INTEGER PRIMARY KEY,
    minijuego VARCHAR(50) NOT NULL,
    CONSTRAINT fk_minijuego FOREIGN KEY(minijuego) REFERENCES JUEGO.MINIJUEGO_DINERO(nombre),
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE JUEGO.C_OBJ(
    numero INTEGER PRIMARY KEY,
    objeto VARCHAR(50) NOT NULL,
    CONSTRAINT fk_objeto FOREIGN KEY(objeto) REFERENCES JUEGO.OBJETO(nombre),
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

CREATE TABLE JUEGO.C_MOV(
    numero INTEGER PRIMARY KEY,
    movimiento INTEGER NOT NULL,
    CONSTRAINT numero_correcto CHECK ( numero > 0 and numero < 72 )
);

/* ESQUEMA PARTIDAS */
CREATE TABLE PARTIDAS.PARTIDA_ACTIVA(
    id INTEGER PRIMARY KEY, 
    hay_barrera BOOLEAN[],
    turno INTEGER,
    minijuego VARCHAR(50),
    ult_resultado INTEGER[],
    CONSTRAINT fk_minijuego FOREIGN KEY(minijuego) REFERENCES JUEGO.MINIJUEGO(nombre),
    CONSTRAINT turno_positivo CHECK ( turno > 0 )
);

CREATE TABLE PARTIDAS.JUGANDO(
    nombre_jugador VARCHAR(50),
    id_partida INTEGER,
    personaje VARCHAR(50),
    dinero INTEGER NOT NULL,
    casilla INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    CONSTRAINT fk_partida FOREIGN KEY(id_partida) REFERENCES PARTIDAS.PARTIDA_ACTIVA(id) ON DELETE CASCADE,
    CONSTRAINT fk_personaje FOREIGN KEY(personaje) REFERENCES JUEGO.PERSONAJE(nombre),
    CONSTRAINT fk_jugador FOREIGN KEY(nombre_jugador) REFERENCES USUARIOS.USUARIO(nombre),
    CONSTRAINT dinero_pos CHECK ( dinero >= 0 ),
    CONSTRAINT casilla_pos CHECK ( casilla >= 0 ),
    CONSTRAINT numeroCorrecto CHECK ( numero >= 1  and numero <= 4 ),
    PRIMARY KEY (nombre_jugador, id_partida)
);