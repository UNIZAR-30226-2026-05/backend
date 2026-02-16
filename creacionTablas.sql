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
    CONSTRAINT usuarios_diferentes CHECK (usuario1 <> usuario2),
    PRIMARY KEY(usuario1, usuario2)
);

CREATE TABLE USUARIOS.SOLICITUD(
    solicitante VARCHAR(50),
    solicitado VARCHAR(50),
    CONSTRAINT fk_solicitante FOREIGN KEY(solicitante) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
    CONSTRAINT fk_solicitado FOREIGN KEY(solicitado) REFERENCES USUARIOS.USUARIO(nombre) ON DELETE CASCADE,
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
    ruleta BIT NOT NULL,    -- 0 para intercambio, 1 para ruleta
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

/* TRIGGERS */
-- Evitar relaciones de amistad duplicadas en orden inverso
CREATE OR REPLACE FUNCTION usuarios.check_amigos_inversos()
RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM USUARIOS.AMIGOS
        WHERE usuario1 = NEW.usuario2
          AND usuario2 = NEW.usuario1
    ) THEN
        RAISE EXCEPTION
            'La relación de amistad (% , %) ya existe en orden inverso',
            NEW.usuario2, NEW.usuario1;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_amigos_inversos
BEFORE INSERT ON USUARIOS.AMIGOS
FOR EACH ROW
EXECUTE FUNCTION usuarios.check_amigos_inversos();

-- Evitar solicitudes de amistad duplicadas en orden inverso
CREATE OR REPLACE FUNCTION usuarios.check_solicitud_inversa()
RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM USUARIOS.SOLICITUD
        WHERE solicitante = NEW.solicitado
          AND solicitado  = NEW.solicitante
    ) THEN
        RAISE EXCEPTION
            'Ya existe una solicitud inversa entre % y %',
            NEW.solicitado, NEW.solicitante;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_solicitud_inversa
BEFORE INSERT ON USUARIOS.SOLICITUD
FOR EACH ROW
EXECUTE FUNCTION usuarios.check_solicitud_inversa();

-- Eliminar la solicitud pendiente si se acepta la amistad
CREATE OR REPLACE FUNCTION usuarios.eliminar_solicitud_pendiente()
RETURNS trigger AS $$
BEGIN
    DELETE FROM USUARIOS.SOLICITUD
    WHERE (solicitante = NEW.usuario1 AND solicitado = NEW.usuario2)
       OR (solicitante = NEW.usuario2 AND solicitado = NEW.usuario1);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_eliminar_solicitud_pendiente
AFTER INSERT ON USUARIOS.AMIGOS
FOR EACH ROW
EXECUTE FUNCTION usuarios.eliminar_solicitud_pendiente();