"""
seed_sources — Create pre-configured data sources for VOYANT demo + production.

Seeds:
  - Infrastructure sources (PostgreSQL, Redis, Trino, MinIO, Elasticsearch, Milvus, Kafka)
  - XTRIM demo data sources (CSV files with telecom data)
  - Web sources (SearXNG, web scraping targets)

Run: python manage.py seed_sources
"""

from django.core.management.base import BaseCommand

from apps.discovery.models import Source

PRESET_SOURCES = [
    # ── Infrastructure (already running in Docker) ───────────────────────
    {
        "name": "VOYANT PostgreSQL",
        "source_type": "postgresql",
        "connection_config": {
            "host": "voyant_postgres",
            "port": 5432,
            "database": "voyant",
            "user": "voyant",
            "description": "Primary metadata database — jobs, artifacts, sources, audit logs",
        },
        "status": "active",
    },
    {
        "name": "VOYANT Trino (Iceberg)",
        "source_type": "trino",
        "connection_config": {
            "host": "voyant_trino",
            "port": 8080,
            "catalog": "iceberg",
            "description": "Distributed SQL query engine — federated queries across all data",
        },
        "status": "active",
    },
    {
        "name": "VOYANT MinIO (S3)",
        "source_type": "s3",
        "connection_config": {
            "endpoint": "voyant_minio:9000",
            "bucket": "voyant-artifacts",
            "description": "S3-compatible object storage — artifacts, scraped data, exports",
        },
        "status": "active",
    },
    {
        "name": "VOYANT Elasticsearch",
        "source_type": "elasticsearch",
        "connection_config": {
            "host": "voyant_elasticsearch",
            "port": 9200,
            "description": "Full-text search index — DataHub metadata, log analysis",
        },
        "status": "active",
    },
    {
        "name": "VOYANT Milvus (Vector DB)",
        "source_type": "milvus",
        "connection_config": {
            "host": "voyant_milvus",
            "port": 19530,
            "description": "Vector database — semantic search, document embeddings, hybrid RRF",
        },
        "status": "active",
    },
    {
        "name": "VOYANT Kafka",
        "source_type": "kafka",
        "connection_config": {
            "bootstrap_servers": "voyant_kafka:9092",
            "topics": [
                "voyant.jobs",
                "voyant.quality.alerts",
                "voyant.lineage",
                "voyant.audit",
            ],
            "description": "Event streaming — job events, quality alerts, lineage, audit",
        },
        "status": "active",
    },
    {
        "name": "VOYANT Redis",
        "source_type": "redis",
        "connection_config": {
            "host": "voyant_redis",
            "port": 6379,
            "description": "Cache + session store + job queue",
        },
        "status": "active",
    },
    {
        "name": "VOYANT SearXNG",
        "source_type": "search_engine",
        "connection_config": {
            "url": "http://voyant_searxng:8080",
            "description": "Sovereign meta-search engine — 100+ search engines, no tracking",
        },
        "status": "active",
    },
    # ── XTRIM Demo Data (CSV files) ─────────────────────────────────────
    {
        "name": "XTRIM Clientes",
        "source_type": "csv",
        "connection_config": {
            "format": "csv",
            "description": "XTRIM telecom customer records — names, plans, cities, fiber types",
            "demo": True,
            "table_name": "xtrim_clientes",
            "row_count": 15,
            "fields": [
                "id",
                "nombre",
                "email",
                "ciudad",
                "plan",
                "tipo_fibra",
                "estado",
                "fecha_registro",
            ],
        },
        "status": "active",
    },
    {
        "name": "XTRIM Facturas",
        "source_type": "csv",
        "connection_config": {
            "format": "csv",
            "description": "XTRIM billing records — invoices, amounts, payment status",
            "demo": True,
            "table_name": "xtrim_facturas",
            "row_count": 25,
            "fields": [
                "id",
                "cliente_id",
                "monto",
                "fecha_emision",
                "fecha_vencimiento",
                "estado_pago",
                "metodo_pago",
            ],
        },
        "status": "active",
    },
    {
        "name": "XTRIM Servicios",
        "source_type": "csv",
        "connection_config": {
            "format": "csv",
            "description": "XTRIM service catalog — internet plans, streaming bundles, TV packages",
            "demo": True,
            "table_name": "xtrim_servicios",
            "row_count": 20,
            "fields": [
                "id",
                "nombre",
                "tipo",
                "precio",
                "velocidad_mbps",
                "incluye_streaming",
            ],
        },
        "status": "active",
    },
    {
        "name": "XTRIM Tickets Soporte",
        "source_type": "csv",
        "connection_config": {
            "format": "csv",
            "description": "XTRIM support tickets — issues, resolution times, SLA compliance",
            "demo": True,
            "table_name": "xtrim_tickets",
            "row_count": 15,
            "fields": [
                "id",
                "cliente_id",
                "tipo_problema",
                "descripcion",
                "estado",
                "tiempo_resolucion_min",
                "agente",
            ],
        },
        "status": "active",
    },
    # ── Knowledge Sources (indexed in Milvus) ────────────────────────────
    {
        "name": "XTRIM Knowledge Base",
        "source_type": "vector_knowledge",
        "connection_config": {
            "description": (
                "XTRIM telecom knowledge — commercial guide,"
                " support procedures, billing policies,"
                " call center manual"
            ),
            "documents": 4,
            "vector_db": "milvus",
            "collection": "voyant_documents",
            "categories": [
                "planes",
                "soporte",
                "cobranza",
                "callcenter",
                "cobertura",
                "streaming",
            ],
        },
        "status": "active",
    },
    # ── Web Sources (scraping targets) ───────────────────────────────────
    {
        "name": "xtrim.com.ec",
        "source_type": "web",
        "connection_config": {
            "url": "https://xtrim.com.ec",
            "description": "XTRIM official website — plans, pricing, coverage, support",
            "engine": "playwright",
        },
        "status": "active",
    },
]


class Command(BaseCommand):
    help = "Seed pre-configured data sources for VOYANT demo and production"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default="default",
            help="Tenant ID for the sources (default: 'default')",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing sources before seeding",
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant"]

        if options["clear"]:
            count = Source.objects.filter(tenant_id=tenant_id).count()
            Source.objects.filter(tenant_id=tenant_id).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {count} existing sources for tenant '{tenant_id}'"
                )
            )

        created = 0
        skipped = 0

        for source_data in PRESET_SOURCES:
            name = source_data["name"]
            if Source.objects.filter(tenant_id=tenant_id, name=name).exists():
                skipped += 1
                continue

            Source.objects.create(
                tenant_id=tenant_id,
                name=name,
                source_type=source_data["source_type"],
                connection_config=source_data["connection_config"],
                status=source_data.get("status", "pending"),
            )
            created += 1
            self.stdout.write(f"  ✅ {name} [{source_data['source_type']}]")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} sources ({skipped} already existed)")
        )
        total = Source.objects.filter(tenant_id=tenant_id).count()
        self.stdout.write(f"Total sources for tenant '{tenant_id}': {total}")
