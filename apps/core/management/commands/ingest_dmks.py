"""
ingest_dmks — Load DMKS business intelligence data into PostgreSQL via VOYANT.

Direct SQLite-to-PostgreSQL transfer. No column renaming — just load the data.

Run: python manage.py ingest_dmks
"""

import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

DMKS_DB = Path(
    "/Users/macbookpro201916i964gb1tb/Documents/Clientes/2026/DMKS/dkms_data.db"
)

# Table mapping: pg_table -> (sqlite_table, limit_or_None)
TABLES = [
    ("dmks_ventas_dashboard", "ventas_dashboard", None),
    ("dmks_ventas_totales", "ventas_ventas_totales", None),
    ("dmks_ventas_desde_2024", "ventas_ventas_totales_desde_2024", None),
    ("dmks_sri_sectorial", "sri_sectorial_data", None),
    ("dmks_empresas_nacionales", "supercias_empresas_nacionales", 50000),
    ("dmks_rankings_empresariales", "supercias_rankings_empresariales", 100000),
    ("dmks_indicadores_sectoriales", "supercias_indicadores_sectoriales", None),
    ("dmks_contratos", "excel_informacionintegrados", None),
    ("dmks_plan_negocios", "excel_plannegocios", None),
]


def normalize_col(name):
    """Normalize column name for PostgreSQL."""
    import unicodedata

    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace spaces and special chars
    result = ascii_name.lower()
    for ch in [" ", "-", "/", "(", ")"]:
        result = result.replace(ch, "_")
    # Remove double underscores
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_")


class Command(BaseCommand):
    help = "Load DMKS business intelligence data into PostgreSQL via VOYANT"

    def handle(self, *args, **options):
        if not DMKS_DB.exists():
            self.stdout.write(self.style.ERROR(f"DMKS database not found: {DMKS_DB}"))
            return

        src_conn = sqlite3.connect(str(DMKS_DB))
        total_rows = 0

        for pg_table, src_table, limit in TABLES:
            # Get source columns
            pragma = src_conn.execute(f"PRAGMA table_info([{src_table}])").fetchall()
            src_cols = [row[1] for row in pragma]
            pg_cols = [normalize_col(c) for c in src_cols]

            # Deduplicate column names
            seen = {}
            deduped = []
            for c in pg_cols:
                if c in seen:
                    seen[c] += 1
                    deduped.append(f"{c}_{seen[c]}")
                else:
                    seen[c] = 0
                    deduped.append(c)
            pg_cols = deduped

            # Create PG table with TEXT columns (simple, works for everything)
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {pg_table}")
                cols_ddl = ", ".join([f'"{c}" TEXT' for c in pg_cols])
                cursor.execute(f"CREATE TABLE {pg_table} ({cols_ddl})")

            # Read from SQLite
            query = f"SELECT * FROM [{src_table}]"
            if limit:
                query += f" LIMIT {limit}"
            rows = src_conn.execute(query).fetchall()

            if not rows:
                self.stdout.write(f"  {src_table}: no data")
                continue

            # Insert into PostgreSQL
            placeholders = ", ".join(["%s"] * len(pg_cols))
            col_names = ", ".join([f'"{c}"' for c in pg_cols])
            insert_sql = f"INSERT INTO {pg_table} ({col_names}) VALUES ({placeholders})"

            with connection.cursor() as cursor:
                batch = []
                for row in rows:
                    values = [None if v is None else str(v) for v in row]
                    batch.append(values)
                    if len(batch) >= 5000:
                        cursor.executemany(insert_sql, batch)
                        batch = []
                if batch:
                    cursor.executemany(insert_sql, batch)

            total_rows += len(rows)
            self.stdout.write(f"  {src_table} -> {pg_table}: {len(rows)} rows")

        src_conn.close()

        # Create summary view
        with connection.cursor() as cursor:
            cursor.execute("DROP VIEW IF EXISTS dmks_resumen")
            cursor.execute("""
                CREATE VIEW dmks_resumen AS
                SELECT 'Empresas Nacionales' as fuente,
                    COUNT(*) as registros
                    FROM dmks_empresas_nacionales
                UNION ALL SELECT 'Rankings Empresariales', COUNT(*) FROM dmks_rankings_empresariales
                UNION ALL SELECT 'Ventas Dashboard', COUNT(*) FROM dmks_ventas_dashboard
                UNION ALL SELECT 'Ventas Totales', COUNT(*) FROM dmks_ventas_totales
                UNION ALL SELECT 'Ventas Desde 2024', COUNT(*) FROM dmks_ventas_desde_2024
                UNION ALL SELECT 'SRI Sectorial', COUNT(*) FROM dmks_sri_sectorial
                UNION ALL SELECT 'Contratos Locales', COUNT(*) FROM dmks_contratos
                UNION ALL SELECT 'Planes de Negocio', COUNT(*) FROM dmks_plan_negocios
                UNION ALL SELECT 'Indicadores Sectoriales',
                    COUNT(*) FROM dmks_indicadores_sectoriales
            """)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"DMKS ingestion complete. {total_rows} total rows loaded into 9 tables."
            )
        )
