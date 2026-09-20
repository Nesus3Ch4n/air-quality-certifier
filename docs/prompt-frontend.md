# Prompt — Frontend Aire Cierto (v0.dev / Next.js)

> Copia y pega esto directamente en v0.dev o en el chat de tu herramienta de generación de UI.

---

## Prompt

Construye una aplicación web completa en **Next.js 14 (App Router) + Tailwind CSS** llamada **"Aire Cierto"** — un sistema público de certificación criptográfica de datos ambientales de Cali, Colombia.

### Identidad visual
- Nombre: **Aire Cierto**
- Tagline: *"Datos del aire, verificables por cualquiera"*
- Paleta: fondo oscuro (slate-900 / slate-950), acentos en verde esmeralda (#00E400) y blanco
- Tipografía limpia, moderna, estilo dashboard cívico / govtech
- Totalmente responsiva (mobile-first)

---

### Páginas y componentes

#### 1. Landing / Home (`/`)

Hero section con:
- Logo + nombre "Aire Cierto" con tagline
- Frase: *"Cada lectura de calidad del aire del DAGMA Cali queda firmada criptográficamente y anclada en blockchain. Nadie puede alterar un dato sin que el hash lo delate."*
- Botón CTA: **"Ver lecturas certificadas"** → scroll a la sección de datos
- Tres tarjetas de valor:
  - 📡 **Fuente oficial** — Datos directos de las estaciones DAGMA Cali
  - 🔒 **Hash SHA-256** — Huella digital inmutable por cada lectura
  - ⛓ **Anclado en blockchain** — HashKey Chain, verificable por cualquiera

#### 2. Dashboard de lecturas (`#lecturas`)

Tabla/grid de las últimas lecturas certificadas con columnas:
- Estación (`la_flora` / `canaveralejo`)
- Fecha y hora de la lectura
- PM10 (µg/m³)
- Categoría IQCA con **badge de color** según el estándar colombiano:
  - 🟢 Verde — Buena (0–50)
  - 🟡 Amarillo — Aceptable (51–100)
  - 🟠 Naranja — Dañina a grupos sensibles (101–150)
  - 🔴 Rojo — Dañina (151–200)
  - 🟣 Morado — Muy dañina (201–300)
  - 🟤 Marrón — Peligrosa (301–500)
- SHA-256 (truncado a 16 chars + botón copiar)
- TX Hash blockchain (truncado, link a explorador si existe)

Filtros:
- Por estación (dropdown)
- Por categoría IQCA (dropdown)

Botón: **"Ingestar lecturas frescas"** → llama al endpoint de ingest

#### 3. Verificador de integridad (`#verificar`)

Sección con:
- Input de texto: *"Pega aquí un hash SHA-256"*
- Botón **"Verificar en blockchain"**
- Resultado visual:
  - ✅ Verde: *"Hash certificado en blockchain — Bloque #XXXXX, TX: 0x..."*
  - ❌ Rojo: *"Hash no encontrado en el contrato"*
  - ⚠️ Gris: *"Modo DRY_RUN — blockchain no conectado"*

#### 4. Stats bar (fija en header o footer)

Muestra en tiempo real:
- Total de lecturas en base de datos
- Total certificadas on-chain
- Modo blockchain: `🟢 Live` o `🟡 DRY_RUN`
- Normativa: `Resolución 2254/2017 — MADS Colombia`

---

### Integración con el backend

**Base URL**: configurable via variable de entorno `NEXT_PUBLIC_API_URL`
(en desarrollo: `http://localhost:8000`, en producción: `https://tu-backend.vercel.app`)

Todos los fetch van a esta API FastAPI. Usar `async/await` con manejo de errores.

#### Endpoints a consumir:

```
GET  {API_URL}/air-quality/
     Query params: estacion?, categoria?, limite=50
     → Array de AirQualityRecord (lecturas certificadas de Supabase)

GET  {API_URL}/air-quality/ingest
     Query params: estacion=la_flora, limite=20, anclar=true
     → Array de AirQualityRecord recién ingestados y guardados

GET  {API_URL}/air-quality/verify/{sha256_hash}
     → { certified: bool|null, mode: "live"|"dry_run", tx_hash?, block_number?, chain_id? }

GET  {API_URL}/air-quality/stats
     → { total_in_database: int, total_certified_onchain: int|null,
         blockchain_mode: "live"|"dry_run", contract_address?: string,
         iqca_norm: string }

GET  {API_URL}/health
     → { status: "ok" }
```

#### Modelo de dato `AirQualityRecord`:

```typescript
interface AirQualityRecord {
  id?: string
  station: string              // "la_flora" | "canaveralejo"
  recorded_at: string | null   // ISO datetime
  pm10: number | null
  so2: number | null
  no2: number | null
  co: number | null
  o3: number | null
  h2s: number | null
  wind_speed: number | null
  wind_dir: number | null
  temperature: number | null
  humidity: number | null
  radiation: number | null
  rain: number | null
  iqca_category: string        // "Buena" | "Aceptable" | "Dañina a grupos sensibles" | "Dañina" | "Muy dañina" | "Peligrosa" | "Sin dato"
  iqca_color: string           // "Verde" | "Amarillo" | "Naranja" | "Rojo" | "Morado" | "Marrón" | "Gris"
  iqca_color_hex: string       // "#00E400" | "#FFFF00" | "#FF7E00" | "#FF0000" | "#8F3F97" | "#7E0023" | "#AAAAAA"
  iqca_index: number | null    // 0–500
  iqca_health_message: string
  sha256_hash: string          // 64 chars hex
  tx_hash: string | null       // hash de tx en blockchain
  block_number: number | null
  chain_id: number | null      // 133 = HashKey testnet, 177 = HashKey mainnet
  created_at: string | null
}
```

---

### Comportamiento UX

- **Loading states**: skeleton loaders mientras carga la tabla
- **Error handling**: toast o banner rojo si el backend no responde
- **Auto-refresh**: las stats se actualizan cada 30 segundos
- **Copiar hash**: botón de copiar al portapapeles en cada hash SHA-256
- **Link a explorador**: si `tx_hash` existe, enlaza a `https://testnet.hashscan.io/transaction/{tx_hash}` (testnet) o `https://hashscan.io/transaction/{tx_hash}` (chain_id=177)
- **Tooltip en IQCA**: al hover sobre el badge de categoría, muestra el mensaje oficial de salud (`iqca_health_message`)

---

### Variables de entorno necesarias

Crear archivo `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Notas adicionales

- No usar autenticación — la app es totalmente pública (los datos son abiertos)
- No instalar Supabase JS en el frontend — todo va a través del backend FastAPI
- Usar `fetch` nativo o SWR para los datos
- El nombre del proyecto en `package.json` debe ser `aire-cierto-frontend`
