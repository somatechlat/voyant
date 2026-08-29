"""
Security test conftest — adversarial payloads and test helpers.
"""

import pytest


SQL_INJECTION_PAYLOADS = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "UNION SELECT * FROM secrets",
    "1; DELETE FROM voyant_jobs WHERE 1=1",
    "admin'--",
    "1' WAITFOR DELAY '0:0:5'--",
    "1' UNION SELECT username,password FROM users--",
    "'; EXEC xp_cmdshell('dir')--",
    "1' AND 1=CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))--",
    "1; INSERT INTO users VALUES('hacker','pass123')--",
]

SSRF_PAYLOADS = [
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1:8080/admin",
    "http://[::1]:8080/",
    "http://0177.0.0.1/",
    "http://0x7f.0x0.0x0.0x1/",
    "file:///etc/passwd",
    "gopher://127.0.0.1:25/",
    "dict://127.0.0.1:6379/",
    "http://10.0.0.1/internal",
    "http://172.16.0.1/secret",
]


@pytest.fixture(params=SQL_INJECTION_PAYLOADS)
def sql_injection(request):
    return request.param


@pytest.fixture(params=SSRF_PAYLOADS)
def ssrf_payload(request):
    return request.param
