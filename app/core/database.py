"""
Cliente de Supabase reutilizable en todo el backend.

Usamos dos clientes:
- supabase_admin: usa la SERVICE_ROLE_KEY, salta las políticas RLS.
  Úsalo solo para operaciones internas de confianza (ej. tareas de sistema).
- get_supabase_client(): usa la ANON_KEY + el JWT del usuario, respeta RLS.
  Úsalo para casi todo lo que haga un usuario autenticado.
"""
from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

# Cliente admin (bypass RLS) - usar con cuidado
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY,
)


def get_supabase_client(access_token: str | None = None) -> Client:
    """
    Devuelve un cliente de Supabase que respeta Row Level Security (RLS).
    Si se pasa el access_token del usuario, las queries se ejecutan
    con sus permisos (recomendado para casi todos los endpoints).
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    if access_token:
        client.postgrest.auth(access_token)
    return client
