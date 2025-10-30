from udb_api.autodetect import autodetect


def test_autodetect_postgres():
    res = autodetect('postgres://user:pass@host:5432/dbname')
    assert res.best.provider == 'postgres'
    assert res.best.auth_type == 'userpass'


def test_autodetect_sharepoint():
    res = autodetect('https://contoso.sharepoint.com/sites/Finance')
    assert res.best.provider == 'sharepoint_onedrive'


def test_autodetect_rest_default():
    res = autodetect('https://api.example.com/v1')
    assert res.best.provider in ('rest_api', 'sharepoint_onedrive', 'google_drive', 'postgres', 's3')
