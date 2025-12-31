import inspect
import os
import types

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
django.setup()

from django.test import Client


@pytest.fixture
def client():
    return Client()

# Core modules / symbols we forbid patching for network realism
_FORBIDDEN_PREFIXES = [
    "httpx.",
    "redis.",
    "aiokafka.",
]

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item):
    # Capture monkeypatch fixture (if used) and inspect its setattribute/setitem usage
    mp = item.funcargs.get("monkeypatch") if hasattr(item, "funcargs") else None
    if mp:
        original_setattr = mp.setattr
        original_setitem = mp.setitem

        def guarded_setattr(target, name, value, *a, **kw):
            fq = None
            if isinstance(target, types.ModuleType):
                fq = f"{target.__name__}.{name}"
            elif inspect.isclass(target):
                fq = f"{target.__module__}.{target.__name__}.{name}"
            if fq and any(fq.startswith(p) for p in _FORBIDDEN_PREFIXES):
                raise RuntimeError(f"Forbidden monkeypatch of core real dependency: {fq}")
            return original_setattr(target, name, value, *a, **kw)

        def guarded_setitem(mapping, key, value, *a, **kw):
            if any(str(key).startswith(p.split('.')[0]) for p in _FORBIDDEN_PREFIXES):
                raise RuntimeError(f"Forbidden monkeypatch attempt affecting: {key}")
            return original_setitem(mapping, key, value, *a, **kw)

        mp.setattr = guarded_setattr  # type: ignore
        mp.setitem = guarded_setitem  # type: ignore
    yield
