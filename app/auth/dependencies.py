"""
Dependencias de autenticación para proteger endpoints.

Supabase Auth emite un JWT cuando el usuario inicia sesión desde el frontend.
El frontend debe enviar ese token en el header:
    Authorization: Bearer <token>

Esta dependencia lo valida y devuelve los datos del usuario autenticado.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: str, email: str | None, access_token: str):
        self.id = user_id
        self.email = email
        self.access_token = access_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin usuario")

    return CurrentUser(user_id=user_id, email=email, access_token=token)
