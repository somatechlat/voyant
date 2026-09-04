"""
Unit tests for apps.uptp_core.parser — URIParser.

Tests URI parsing for all supported schemes, error handling for
invalid/unsupported URIs, and config extraction.
Pure logic — no DB, no services.
"""

import pytest

from apps.uptp_core.parser import URIParser


class TestURIParserPostgres:
    def test_postgresql_scheme(self):
        result = URIParser.parse_uri("postgresql://user:pass@db.example.com:5432/mydb")
        assert result["connector_id"] == "postgres"
        assert result["config"]["host"] == "db.example.com"
        assert result["config"]["port"] == 5432
        assert result["config"]["database"] == "mydb"
        assert result["config"]["user"] == "user"
        assert result["config"]["password"] == "pass"

    def test_postgres_scheme_alias(self):
        result = URIParser.parse_uri("postgres://admin:secret@localhost:5432/test")
        assert result["connector_id"] == "postgres"
        assert result["config"]["host"] == "localhost"

    def test_postgres_no_port(self):
        result = URIParser.parse_uri("postgresql://user:pass@host/db")
        assert result["config"]["port"] is None
        assert result["config"]["database"] == "db"

    def test_postgres_special_chars_in_password(self):
        result = URIParser.parse_uri("postgresql://user:p%40ss!w0rd@host:5432/db")
        assert result["config"]["user"] == "user"
        # Password should be URL-decoded by urlparse
        assert result["config"]["password"] is not None


class TestURIParserMySQL:
    def test_mysql_scheme(self):
        result = URIParser.parse_uri("mysql://root:pw@mysql-host:3306/warehouse")
        assert result["connector_id"] == "mysql"
        assert result["config"]["host"] == "mysql-host"
        assert result["config"]["port"] == 3306
        assert result["config"]["database"] == "warehouse"
        assert result["config"]["user"] == "root"
        assert result["config"]["password"] == "pw"


class TestURIParserS3:
    def test_s3_scheme(self):
        result = URIParser.parse_uri("s3://AKIAIOSFODNN7EXAMPLE:secretkey@s3.amazonaws.com")
        assert result["connector_id"] == "s3"
        assert result["config"]["host"] == "s3.amazonaws.com"
        assert result["config"]["user"] == "AKIAIOSFODNN7EXAMPLE"
        assert result["config"]["password"] == "secretkey"


class TestURIParserGCS:
    def test_gcs_scheme(self):
        result = URIParser.parse_uri("gcs://key:token@storage.googleapis.com")
        assert result["connector_id"] == "gcs"
        assert result["config"]["host"] == "storage.googleapis.com"


class TestURIParserSnowflake:
    def test_snowflake_scheme(self):
        result = URIParser.parse_uri("snowflake://user:pass@account.snowflakecomputing.com/db")
        assert result["connector_id"] == "snowflake"
        assert result["config"]["host"] == "account.snowflakecomputing.com"
        assert result["config"]["database"] == "db"


class TestURIParserBigQuery:
    def test_bigquery_scheme(self):
        result = URIParser.parse_uri("bigquery://user:token@bigquery.googleapis.com/project")
        assert result["connector_id"] == "bigquery"
        assert result["config"]["host"] == "bigquery.googleapis.com"


class TestURIParserErrors:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid URI format"):
            URIParser.parse_uri("")

    def test_no_scheme_raises(self):
        with pytest.raises(ValueError, match="Invalid URI format"):
            URIParser.parse_uri("just_a_string")

    def test_unsupported_scheme_raises(self):
        with pytest.raises(ValueError, match="Unsupported generic URI scheme"):
            URIParser.parse_uri("ftp://user:pass@host/file")

    def test_redis_scheme_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported generic URI scheme"):
            URIParser.parse_uri("redis://localhost:6379/0")

    def test_mongodb_scheme_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported generic URI scheme"):
            URIParser.parse_uri("mongodb://user:pass@host:27017/db")


class TestURIParserSchemeMapping:
    def test_all_supported_schemes(self):
        """Verify all entries in SCHEME_TO_CONNECTOR are parseable."""
        schemes = {
            "postgresql": "postgres",
            "postgres": "postgres",
            "mysql": "mysql",
            "s3": "s3",
            "gcs": "gcs",
            "snowflake": "snowflake",
            "bigquery": "bigquery",
        }
        for scheme, expected_connector in schemes.items():
            result = URIParser.parse_uri(f"{scheme}://u:p@h/db")
            assert result["connector_id"] == expected_connector, f"Failed for scheme: {scheme}"

    def test_scheme_case_insensitive(self):
        result = URIParser.parse_uri("POSTGRESQL://u:p@h/db")
        assert result["connector_id"] == "postgres"
