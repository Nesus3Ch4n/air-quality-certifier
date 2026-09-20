-- ============================================================
--  Migración: Certificador de Calidad del Aire Cali
--  Tabla: air_quality_readings
--
--  Ejecutar en: Supabase → SQL Editor → New query
--  Proyecto: vuxwfhaunnyidbcstln
-- ============================================================

-- 1. Extensión para UUIDs (ya viene activa en Supabase, pero por si acaso)
create extension if not exists "pgcrypto";

-- 2. Tabla principal
create table if not exists public.air_quality_readings (
    -- Identificador
    id              uuid        primary key default gen_random_uuid(),

    -- Origen del dato
    station         text        not null,           -- "la_flora" | "canaveralejo"
    recorded_at     timestamptz,                    -- timestamp original de la estación

    -- Contaminantes (µg/m³ o unidades indicadas)
    pm10            numeric(10,4),                  -- Material particulado PM10 (µg/m³)
    so2             numeric(10,4),                  -- Dióxido de azufre (µg/m³)
    no2             numeric(10,4),                  -- Dióxido de nitrógeno (µg/m³)
    co              numeric(10,4),                  -- Monóxido de carbono (µg/m³)
    o3              numeric(10,4),                  -- Ozono (µg/m³)
    h2s             numeric(10,4),                  -- Ácido sulfhídrico (µg/m³)

    -- Variables meteorológicas
    wind_speed      numeric(8,4),                   -- Velocidad del viento (m/s)
    wind_dir        numeric(8,4),                   -- Dirección del viento (grados)
    temperature     numeric(8,4),                   -- Temperatura (°C)
    humidity        numeric(8,4),                   -- Humedad relativa (%)
    radiation       numeric(10,4),                  -- Radiación solar (W/m²)
    rain            numeric(8,4),                   -- Lluvia acumulada (mm)

    -- Clasificación IQCA (Resolución 2254/2017 – MADS Colombia)
    iqca_category       text,                       -- "Buena" | "Aceptable" | "Dañina a grupos sensibles" | ...
    iqca_color          text,                       -- "Verde" | "Amarillo" | "Naranja" | "Rojo" | "Morado" | "Marrón"
    iqca_color_hex      text,                       -- "#00E400" | "#FFFF00" | etc.
    iqca_index          integer check (iqca_index between 0 and 500),
    iqca_health_message text,                       -- Mensaje oficial de salud pública

    -- Integridad y trazabilidad
    sha256_hash     text        not null unique,    -- SHA-256 del registro (evita duplicados)

    -- Anclaje on-chain en Ethereum / HashKey Chain
    tx_hash         text,                           -- Hash de la transacción blockchain
    block_number    bigint,                         -- Bloque en que quedó confirmado
    chain_id        integer,                        -- ID de la red (177 = HashKey mainnet, 133 = testnet)

    -- Auditoría
    created_at      timestamptz default now()
);

-- 3. Índices para las consultas más frecuentes
create index if not exists idx_aqr_station
    on public.air_quality_readings (station);

create index if not exists idx_aqr_recorded_at
    on public.air_quality_readings (recorded_at desc);

create index if not exists idx_aqr_iqca_category
    on public.air_quality_readings (iqca_category);

create index if not exists idx_aqr_created_at
    on public.air_quality_readings (created_at desc);

-- 4. Row Level Security — todos pueden leer (datos públicos de calidad del aire),
--    nadie puede escribir desde el cliente (solo el backend con service_role_key)
alter table public.air_quality_readings enable row level security;

-- Política: lectura pública (cualquier usuario autenticado o anónimo puede leer)
create policy "Lectura pública de lecturas de calidad del aire"
    on public.air_quality_readings
    for select
    using (true);

-- No hay política de INSERT/UPDATE/DELETE para el rol anon → solo el backend
-- (usando service_role_key) puede escribir. Esto es correcto y seguro.

-- 5. Comentarios de tabla y columnas (documentación en el dashboard de Supabase)
comment on table public.air_quality_readings is
    'Lecturas de calidad del aire de las estaciones DAGMA Cali, certificadas con hash SHA-256 y ancladas on-chain en HashKey Chain.';

comment on column public.air_quality_readings.sha256_hash is
    'Hash SHA-256 determinístico del registro original. Permite verificar integridad: cualquier alteración del dato cambia el hash.';

comment on column public.air_quality_readings.tx_hash is
    'Hash de la transacción en Ethereum/HashKey Chain donde quedó certificado el hash. NULL si se usó modo DRY_RUN.';

comment on column public.air_quality_readings.iqca_index is
    'Índice numérico IQCA (0-500) según Resolución 2254/2017, MADS Colombia. Calculado por interpolación lineal sobre PM10.';
