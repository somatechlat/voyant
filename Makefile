PYTHON=.venv/bin/python
APP=voyant_project.asgi:application
UVICORN=uvicorn

.PHONY: dev install lint test build docker check

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check apps/
	$(PYTHON) -m ruff format --check apps/

format:
	$(PYTHON) -m ruff check --fix apps/
	$(PYTHON) -m ruff format apps/

check: lint test

dev:
	$(UVICORN) $(APP) --reload --host 0.0.0.0 --port 8000

docker:
	docker build -t voyant-api:dev .
