"""
Pytest Configuration and Fixtures for Voyant Test Suite.

This module provides global pytest fixtures and hooks that configure the testing
environment for the Voyant application. It sets up Django, provides a test client,
and includes a critical mechanism to guard against unintentional monkeypatching
of core network-related dependencies, ensuring higher fidelity for integration tests.
"""

import inspect
import os
import types
from typing import Any, Dict, List

import django
import pytest
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
django.setup()


@pytest.fixture
def client() -> Client:
    """
    Provides a Django test client instance for making HTTP requests to the application.

    This fixture is automatically available to all test functions that declare it as a parameter.

    Returns:
        django.test.Client: An instance of the Django test client.
    """
    return Client()


# _FORBIDDEN_PREFIXES: A list of fully qualified prefixes for modules or objects
# that are considered core, real dependencies and should not be monkeypatched
# during testing. This ensures that integration tests genuinely interact with
# network or external services, unless explicitly mocked at a higher level.
_FORBIDDEN_PREFIXES = [
    "httpx.",
    "redis.",
    "aiokafka.",
]


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item: Any) -> Any:
    """
    Pytest hook that wraps `pytest_runtest_call` to prevent monkeypatching of
    critical external dependencies.

    This hook intercepts attempts to use the `monkeypatch` fixture's `setattr`
    and `setitem` methods. If a test tries to patch a module or object whose
    fully qualified name starts with one of the `_FORBIDDEN_PREFIXES`, a
    `RuntimeError` is raised. This ensures that tests intended to verify
    real network or external service interactions are not inadvertently
    mocked out.

    Args:
        item (Any): The pytest test item (representing the test function or method).

    Yields:
        Any: The result of the original `pytest_runtest_call`.

    Raises:
        RuntimeError: If an attempt is made to monkeypatch a forbidden core dependency.
    """
    # Retrieve the monkeypatch fixture if it's used by the current test item.
    mp = item.funcargs.get("monkeypatch") if hasattr(item, "funcargs") else None
    if mp:
        original_setattr = mp.setattr
        original_setitem = mp.setitem

        def guarded_setattr(target: Any, name: str, value: Any, *a: Any, **kw: Any) -> Any:
            """
            A wrapper around `monkeypatch.setattr` that checks for forbidden targets.
            """
            fq: Optional[str] = None
            if isinstance(target, types.ModuleType):
                fq = f"{target.__name__}.{name}"
            elif inspect.isclass(target):
                fq = f"{target.__module__}.{target.__name__}.{name}"
            
            if fq and any(fq.startswith(p) for p in _FORBIDDEN_PREFIXES):
                raise RuntimeError(
                    f"Forbidden monkeypatch of core real dependency detected: {fq}. "
                    "Ensure you are testing real network interactions or mock at a different level."
                )
            return original_setattr(target, name, value, *a, **kw)

        def guarded_setitem(mapping: Dict[Any, Any], key: Any, value: Any, *a: Any, **kw: Any) -> Any:
            """
            A wrapper around `monkeypatch.setitem` that checks for forbidden targets.
            """
            # This check is less precise for setitem as 'key' might not be a fqdn,
            # but it attempts to catch top-level module/package name mismatches.
            if isinstance(key, str) and any(key.startswith(p.split(".")[0]) for p in _FORBIDDEN_PREFIXES):
                 raise RuntimeError(
                    f"Forbidden monkeypatch attempt on core real dependency detected affecting: {key}. "
                    "Ensure you are testing real network interactions or mock at a different level."
                )
            return original_setitem(mapping, key, value, *a, **kw)

        # Replace the original methods with their guarded versions.
        # type: ignore comments are used to suppress mypy warnings about modifying built-in methods.
        mp.setattr = guarded_setattr  # type: ignore
        mp.setitem = guarded_setitem  # type: ignore
    yield
