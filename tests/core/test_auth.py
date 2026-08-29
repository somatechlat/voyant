import pytest
from ninja.errors import HttpError

from apps.core.security.auth import KeycloakAuth


@pytest.mark.django_db
class TestKeycloakAuthIntegration:
    """
    Integration tests for KeycloakAuth using a real Keycloak instance.
    """

    def test_keycloak_jwks_fetch(self):
        import os
        auth = KeycloakAuth()
        # Use Docker-internal URL when inside a container, host URL otherwise
        if os.path.exists("/.dockerenv"):
            auth.server_url = "http://voyant_keycloak:8080"
        else:
            auth.server_url = "http://localhost:45180"
        auth.realm = "voyant"

        # This will trigger jwks fetch
        jwks = auth._get_jwks()
        assert "keys" in jwks
        assert len(jwks["keys"]) > 0

    def test_invalid_token_rejected(self):
        auth = KeycloakAuth()

        with pytest.raises(HttpError) as exc:
            auth.validate_token("invalid-token")
        assert exc.value.status_code == 401

    # Note: Full token validation requires a real JWT from Keycloak.
    # In a CI/CD environment, we would use a service account to get a token.
    # For now, we verify the JWKS integration which is the core logic.
