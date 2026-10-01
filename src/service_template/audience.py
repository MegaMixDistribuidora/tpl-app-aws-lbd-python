import os
from typing import Literal

from .errors import ForbiddenError

Audience = Literal["store", "admin", "internal"]

_ENV_BY_AUDIENCE: tuple[tuple[Audience, str], ...] = (
    ("store", "STORE_API_ID"),
    ("admin", "ADMIN_API_ID"),
    ("internal", "INTERNAL_API_ID"),
)


def audience(event: dict) -> Audience:
    api_id = (event.get("requestContext") or {}).get("apiId")
    if api_id:
        for name, env_var in _ENV_BY_AUDIENCE:
            if os.environ.get(env_var) == api_id:
                return name
    raise ForbiddenError("Você não tem permissão para esta ação.")
