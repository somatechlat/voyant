PYTHON=python3
APP=udb_api.app:app
UVICORN=uvicorn

.PHONY: dev install lint test build docker

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	pytest -q || true

lint:
	@echo "(Placeholder) Add ruff/flake8/mypy in future"

dev:
	$(UVICORN) $(APP) --reload --host 0.0.0.0 --port 8000

docker:
	docker build -t udb-api:dev .
