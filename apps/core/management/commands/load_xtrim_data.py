"""
load_xtrim_data — Load XTRIM telecom demo data into PostgreSQL.

Creates xtrim_clientes, xtrim_facturas, xtrim_servicios, xtrim_tickets tables
and loads data from CSV files. Queryable via Trino immediately after.

Run: python manage.py load_xtrim_data
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

CSV_DIR = Path("/tmp/xtrim_data")
HOST_CSV_DIR = Path(
    "/Users/macbookpro201916i964gb1tb/Documents"
    "/Clientes/2026/XTRIM/demo_RFP/demo_assets/sample_data"
)

TABLE_DEFS = {
    "xtrim_clientes": """
        CREATE TABLE IF NOT EXISTS xtrim_clientes (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(200),
            cedula VARCHAR(20),
            plan VARCHAR(100),
            estado VARCHAR(50),
            ciudad VARCHAR(100),
            direccion TEXT,
            telefono VARCHAR(30),
            email VARCHAR(200),
            monto_mensual NUMERIC(10,2),
            fecha_activacion DATE,
            zona VARCHAR(50)
        )
    """,
    "xtrim_facturas": """
        CREATE TABLE IF NOT EXISTS xtrim_facturas (
            id INTEGER PRIMARY KEY,
            cliente_id INTEGER,
            monto NUMERIC(10,2),
            fecha_emision DATE,
            fecha_vencimiento DATE,
            estado VARCHAR(50),
            concepto VARCHAR(200),
            periodo VARCHAR(50)
        )
    """,
    "xtrim_servicios": """
        CREATE TABLE IF NOT EXISTS xtrim_servicios (
            id INTEGER PRIMARY KEY,
            cliente_id INTEGER,
            tipo VARCHAR(100),
            velocidad VARCHAR(50),
            estado VARCHAR(50),
            nodo_red VARCHAR(100),
            fecha_activacion DATE,
            precio_mensual NUMERIC(10,2)
        )
    """,
    "xtrim_tickets": """
        CREATE TABLE IF NOT EXISTS xtrim_tickets (
            id INTEGER PRIMARY KEY,
            cliente_id INTEGER,
            servicio_id INTEGER,
            descripcion TEXT,
            prioridad VARCHAR(20),
            estado VARCHAR(50),
            tipo VARCHAR(100),
            sla_horas INTEGER,
            fecha_creacion TIMESTAMP,
            fecha_resolucion TIMESTAMP,
            agente_asignado VARCHAR(100)
        )
    """,
}

CSV_FILES = {
    "xtrim_clientes": "clientes.csv",
    "xtrim_facturas": "facturas.csv",
    "xtrim_servicios": "servicios.csv",
    "xtrim_tickets": "tickets.csv",
}


class Command(BaseCommand):
    help = "Load XTRIM demo data into PostgreSQL (queryable via Trino)"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for table, ddl in TABLE_DEFS.items():
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                cursor.execute(ddl)
                self.stdout.write(f"  Created table: {table}")

        total_rows = 0
        for table, csv_file in CSV_FILES.items():
            path = CSV_DIR / csv_file
            if not path.exists():
                path = HOST_CSV_DIR / csv_file
            if not path.exists():
                self.stdout.write(self.style.WARNING(f"  CSV not found: {csv_file}"))
                continue

            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                continue

            columns = list(rows[0].keys())
            placeholders = ", ".join(["%s"] * len(columns))
            col_names = ", ".join(columns)
            insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

            with connection.cursor() as cursor:
                for row in rows:
                    values = []
                    for col in columns:
                        val = row.get(col, "")
                        if val == "" or val is None:
                            values.append(None)
                        else:
                            values.append(val)
                    cursor.execute(insert_sql, values)

            total_rows += len(rows)
            self.stdout.write(f"  Loaded {len(rows)} rows into {table}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {total_rows} total rows loaded into 4 XTRIM tables."
            )
        )
        self.stdout.write(
            "Queryable via Trino: SELECT * FROM postgresql.public.xtrim_clientes LIMIT 10"
        )
