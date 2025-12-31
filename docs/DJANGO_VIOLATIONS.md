# Django Migration Violations Catalog

Status: Cleared (FastAPI/SQLAlchemy/Alembic removed; Django + Ninja in place).

## Open Violations
- None.

## Notes
- API stack runs on Django + django-ninja (`voyant_app/api.py`, `voyant_project/urls.py`).
- Persistence uses Django ORM and migrations (`voyant_app/models.py`, `voyant_app/migrations/0001_initial.py`).
- Legacy FastAPI/SQLAlchemy/Alembic files and tests were deleted.
