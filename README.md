# Boilerplate FastAPI + Supabase + Vercel

Base reutilizable para levantar demos rápido. Clónalo, cámbiale el nombre,
y en minutos tienes API + DB + deploy listos.

## Estructura

```
backend/
├── app/
│   ├── main.py              # entrypoint, CORS, routers
│   ├── core/
│   │   ├── config.py        # variables de entorno (pydantic-settings)
│   │   └── database.py      # clientes de Supabase (admin + user-scoped)
│   ├── auth/
│   │   └── dependencies.py  # verificación de JWT de Supabase Auth
│   ├── models/
│   │   └── item.py          # ejemplo de modelo Pydantic
│   └── routers/
│       ├── health.py        # GET /health
│       └── items.py         # CRUD de ejemplo (copiar/adaptar)
├── requirements.txt
├── vercel.json               # config de deploy serverless
├── .env.example
└── .gitignore
```

## Cómo usarlo para un proyecto nuevo

1. **Clonar y renombrar**
   ```bash
   git clone <este-repo> nombre-del-proyecto
   cd nombre-del-proyecto
   rm -rf .git && git init
   ```

2. **Crear proyecto en Supabase**
   - Ve a supabase.com → New Project (plan free)
   - En Project Settings → API copia: URL, anon key, service_role key
   - En Project Settings → API → JWT Settings copia el JWT Secret
   - Crea tus tablas en el SQL Editor y activa RLS con políticas por `user_id`

3. **Configurar entorno local**
   ```bash
   cd backend
   cp .env.example .env
   # rellena las variables con los datos de Supabase
   python -m venv venv
   source venv/bin/activate  # o venv\Scripts\activate en Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   API corriendo en http://localhost:8000/docs (Swagger autogenerado)

4. **Adaptar el CRUD de ejemplo**
   - Renombra `models/item.py` y `routers/items.py` a la entidad real
     (ej. `product.py`, `client.py`, `task.py`)
   - Ajusta las columnas del modelo a tu tabla real
   - Regístralo en `main.py`

5. **Desplegar en Vercel**
   ```bash
   npm i -g vercel   # una sola vez
   cd backend
   vercel
   ```
   - En el dashboard de Vercel, añade las mismas variables del `.env`
     en Settings → Environment Variables
   - Cada push a `main` en GitHub dispara un deploy automático si conectas
     el repo desde el dashboard de Vercel (Import Git Repository)

6. **Conectar el frontend (v0)**
   - En tu proyecto de v0, apunta las llamadas fetch a la URL de Vercel
     del backend (ej. `https://tu-backend.vercel.app`)
   - Usa el cliente de Supabase Auth en el frontend para el login,
     y envía el `access_token` en el header `Authorization: Bearer <token>`
     en cada llamada a la API

## Notas de seguridad

- `SUPABASE_SERVICE_ROLE_KEY` nunca va en el frontend ni se sube a git.
- Todas las tablas deben tener RLS activado con políticas por `user_id`.
- El CRUD de ejemplo usa el cliente user-scoped (`get_supabase_client`),
  que respeta RLS — es el patrón por defecto para casi todo.
