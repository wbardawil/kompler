.PHONY: install test lint run clean db-up db-down db-migrate

install:
	pip install -e ".[dev]"
	pip install pdfplumber python-docx openpyxl

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/

run:
	uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

# Database
db-up:
	docker compose up -d

db-down:
	docker compose down

db-migrate:
	alembic upgrade head

db-reset:
	docker compose down -v
	docker compose up -d
	sleep 3
	alembic upgrade head

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist *.egg-info
