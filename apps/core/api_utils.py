import logging
from typing import Any

from asgiref.sync import async_to_sync
from ninja.errors import HttpError

from admin.common.messages import get_message
from apps.core.config import get_settings
from apps.core.lib.policy import (
    SomaContextError,
    SomaPolicyDenied,
    SomaPolicyUnavailable,
    enforce_policy,
)
from apps.core.security.auth import get_current_user, get_optional_user

settings = get_settings()
logger = logging.getLogger(__name__)


def run_async(func, *args, **kwargs):
    """Run an async function from a sync context."""
    return async_to_sync(func)(*args, **kwargs)


def auth_guard(request):
    """
    Enforce authentication outside local environments.

    In local mode we allow missing tokens for developer ergonomics; in other
    environments we require a valid Keycloak JWT.

    Returns:
        User object or True (to allow access in local mode without token)
    """
    if settings.env == "local":
        user = get_optional_user(request)
        # In local mode, if no token is provided, allow access by returning True
        # Django Ninja accepts True as "authenticated"
        return user if user is not None else True
    return get_current_user(request)


def apply_policy(action: str, prompt: str, metadata: dict[str, Any]) -> None:
    """
    A wrapper to enforce policy checks for an action.

    Raises:
        HttpError: With status 400, 403, or 503 depending on the policy outcome.
    """
    try:
        run_async(enforce_policy, action, prompt, metadata)
    except SomaContextError as exc:
        raise HttpError(400, get_message("ERR_POLICY_INVALID", error=str(exc))) from exc
    except SomaPolicyDenied as exc:
        raise HttpError(
            403, exc.details or {"reason": get_message("ERR_POLICY_DENIED")}  # type: ignore[arg-type]
        ) from exc
    except SomaPolicyUnavailable as exc:
        raise HttpError(
            503, get_message("ERR_POLICY_UNAVAILABLE", error=str(exc))
        ) from exc
