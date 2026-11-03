-- ============================================================================
--  Base de datos: sistema de análisis de resultados electorales
--  Motor: PostgreSQL 14+
--  Versión: 1.0 (modelo entregado para la prueba técnica)
--
--  IMPORTANTE PARA EL CANDIDATO:
--  Este es el modelo que actualmente está en producción. Fue construido de
--  forma acelerada durante la elección anterior. Debes cargar la información
--  sobre ESTE modelo tal como está, y por separado documentar qué mejorarías
--  y por qué (ver sección 3.1 del enunciado).
--  No modifiques este archivo: propón los cambios en docs/MEJORAS_MODELO.md
--  y, si quieres, en un script aparte (sql/99_propuesta_mejoras.sql).
-- ============================================================================

DROP SCHEMA IF EXISTS electoral CASCADE;
CREATE SCHEMA electoral;

SET search_path TO electoral, public;

-- ----------------------------------------------------------------------------
-- 1. Centros de votación
-- ----------------------------------------------------------------------------
CREATE TABLE electoral.centros_votacion (
    id_centro                SERIAL PRIMARY KEY,
    codigo_centro_votacion   VARCHAR(50),
    nombre_centro            VARCHAR(255),
    direccion                VARCHAR(255),
    codigo_departamento      VARCHAR(50),
    nombre_departamento      VARCHAR(255),
    codigo_municipio         VARCHAR(50),
    nombre_municipio         VARCHAR(255),
    zona                     VARCHAR(50),
    area                     VARCHAR(50),
    latitud                  VARCHAR(50),
    longitud                 VARCHAR(50),
    cantidad_mesas           VARCHAR(50),
    capacidad_maxima         VARCHAR(50),
    anio_vigencia            VARCHAR(50),
    fechaCarga               VARCHAR(50)
);

COMMENT ON TABLE electoral.centros_votacion IS
    'Catálogo de centros de votación utilizados en las elecciones.';

-- ----------------------------------------------------------------------------
-- 2. Mesas de votación
-- ----------------------------------------------------------------------------
CREATE TABLE electoral.mesas_votacion (
    id_mesa                  SERIAL PRIMARY KEY,
    codigo_mesa              VARCHAR(50),
    codigo_centro_votacion   VARCHAR(50),
    numero_mesa              VARCHAR(50),
    fechaCarga               VARCHAR(50)
);

COMMENT ON TABLE electoral.mesas_votacion IS
    'Mesas asociadas a cada centro de votación.';

-- ----------------------------------------------------------------------------
-- 3. Resultados de elecciones (una fila por partido y por mesa)
-- ----------------------------------------------------------------------------
CREATE TABLE electoral.resultados_elecciones (
    id_resultado             SERIAL PRIMARY KEY,
    anio_eleccion            VARCHAR(50),
    tipo_eleccion            VARCHAR(50),
    vuelta                   VARCHAR(50),
    codigo_departamento      VARCHAR(50),
    nombre_departamento      VARCHAR(255),
    codigo_municipio         VARCHAR(50),
    nombre_municipio         VARCHAR(255),
    codigo_centro_votacion   VARCHAR(50),
    codigo_mesa              VARCHAR(50),
    partido                  VARCHAR(255),
    candidato                VARCHAR(255),
    votos_validos            VARCHAR(50),
    votos_nulos              VARCHAR(50),
    votos_en_blanco          VARCHAR(50),
    total_empadronados_mesa  VARCHAR(50),
    total_votantes_mesa      VARCHAR(50),
    fechaCarga               VARCHAR(50)
);

COMMENT ON TABLE electoral.resultados_elecciones IS
    'Resultados históricos por mesa y partido. Incluye los totales de la mesa
     repetidos en cada fila de partido.';

-- ----------------------------------------------------------------------------
-- 4. Empadronados (fuente viva, se actualiza diariamente)
-- ----------------------------------------------------------------------------
CREATE TABLE electoral.empadronados (
    id_empadronado                  VARCHAR(50) PRIMARY KEY,
    codigo_centro_votacion          VARCHAR(50),
    codigo_mesa                     VARCHAR(50),
    rango_edad                      VARCHAR(50),
    sexo                            VARCHAR(50),
    codigo_departamento_residencia  VARCHAR(50),
    codigo_municipio_residencia     VARCHAR(50),
    estado_registro                 VARCHAR(50),
    fecha_inscripcion               VARCHAR(50),
    fecha_ultima_actualizacion      VARCHAR(50),
    created_at                      TIMESTAMP DEFAULT now()
);

COMMENT ON TABLE electoral.empadronados IS
    'Padrón electoral vigente. Se sobrescribe con la información del día.';

-- ----------------------------------------------------------------------------
-- 5. Bitácora de cargas
-- ----------------------------------------------------------------------------
CREATE TABLE electoral.carga_log (
    id_log        SERIAL PRIMARY KEY,
    proceso       VARCHAR(255),
    observacion   VARCHAR(255),
    fecha         VARCHAR(50)
);

COMMENT ON TABLE electoral.carga_log IS
    'Registro libre de las ejecuciones de carga.';
