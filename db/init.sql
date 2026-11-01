-- Corre una sola vez, la primera vez que el contenedor de PostgreSQL arranca
-- con un volumen vacío.

-- Dataset crudo de comentarios etiquetados (sintéticos).
-- La limpieza se hace en el script de entrenamiento, no acá.
CREATE TABLE IF NOT EXISTS comentarios (
    id         INTEGER PRIMARY KEY,
    texto      TEXT NOT NULL,
    clase      TEXT NOT NULL CHECK (clase IN
               ('Pedido', 'Pregunta', 'PagoEnvio', 'Objecion', 'Otros')),
    producto   TEXT,
    estilo     TEXT,                                -- forma de escribir (abreviatura, emoji, mayus, etc.)
    origen     TEXT NOT NULL DEFAULT 'sintetico'   -- 'sintetico' | 'manual' | 'live-real'
);

-- Una fila por cada corrida de entrenamiento: qué se entrenó y qué tan bien.
CREATE TABLE IF NOT EXISTS entrenamientos (
    id              SERIAL PRIMARY KEY,
    version         TEXT NOT NULL UNIQUE,
    fecha           TIMESTAMPTZ NOT NULL DEFAULT now(),
    modelo          TEXT NOT NULL,
    configuracion   JSONB NOT NULL,
    cv_f1_macro     DOUBLE PRECISION NOT NULL,
    test_f1_macro   DOUBLE PRECISION NOT NULL,
    test_accuracy   DOUBLE PRECISION NOT NULL,
    n_entrenamiento INTEGER NOT NULL,
    n_prueba        INTEGER NOT NULL
);

-- Cada predicción atendida por la API (análisis individual, carga de archivo o live).
CREATE TABLE IF NOT EXISTS predicciones (
    id             SERIAL PRIMARY KEY,
    fecha          TIMESTAMPTZ NOT NULL DEFAULT now(),
    texto          TEXT NOT NULL,
    clase          TEXT NOT NULL,
    probabilidad   DOUBLE PRECISION NOT NULL,
    probabilidades JSONB NOT NULL,
    version_modelo TEXT NOT NULL,
    origen         TEXT NOT NULL CHECK (origen IN ('individual', 'lote', 'live', 'demo'))
);

CREATE INDEX IF NOT EXISTS predicciones_fecha_idx ON predicciones (fecha DESC);
CREATE INDEX IF NOT EXISTS predicciones_origen_idx ON predicciones (origen);

-- Sesiones de live: una por cada vez que el usuario arranca a analizar.
CREATE TABLE IF NOT EXISTS live_sesiones (
    id             SERIAL PRIMARY KEY,
    usuario_tiktok TEXT NOT NULL,
    modo           TEXT NOT NULL CHECK (modo IN ('real', 'demo')),
    iniciada       TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminada      TIMESTAMPTZ,
    total_comentarios INTEGER DEFAULT 0
);

-- Comentarios de un live, con su clasificación.
CREATE TABLE IF NOT EXISTS live_comentarios (
    id             SERIAL PRIMARY KEY,
    sesion_id      INTEGER NOT NULL REFERENCES live_sesiones(id) ON DELETE CASCADE,
    fecha          TIMESTAMPTZ NOT NULL DEFAULT now(),
    texto          TEXT NOT NULL,
    clase          TEXT NOT NULL,
    probabilidad   DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS live_comentarios_sesion_idx ON live_comentarios (sesion_id, fecha);
