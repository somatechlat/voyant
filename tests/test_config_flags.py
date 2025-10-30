from udb_api.config import get_settings


def test_feature_flags_env(monkeypatch):
    monkeypatch.setenv("UDB_ENABLE_QUALITY", "0")
    monkeypatch.setenv("UDB_ENABLE_CHARTS", "0")
    monkeypatch.setenv("UDB_ENABLE_UNSTRUCTURED", "1")
    # Clear cached settings
    from udb_api.config import get_settings as gs
    gs.cache_clear()  # type: ignore
    s = get_settings()
    assert s.enable_quality is False
    assert s.enable_charts is False
    assert s.enable_unstructured is True
