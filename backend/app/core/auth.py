from hmac import compare_digest

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


async def require_admin(request: Request) -> None:
    expected = request.app.state.settings.admin_token
    if not expected:
        return
    credentials: HTTPAuthorizationCredentials | None = await bearer(request)
    if credentials is None or not compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid administrator token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
