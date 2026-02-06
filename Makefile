.PHONY: install install-all ingest test lint clean features train

# ── Environment ──────────────────────────────────────────────
install:
	pip install -e ".[ml,viz,dev]"

install-all:
	pip install -e ".[all]"

# ── Data Pipeline ────────────────────────────────────────────
init-db:
	python -m src.db.init_db

ingest:
	python -m scripts.run_ingest

ingest-media:
	python -m scripts.run_ingest --step 1-4

ingest-strains:
	python -m scripts.run_ingest --step 7,8

features:
	python -m scripts.build_features

# ── ML ───────────────────────────────────────────────────────
train:
	python -m scripts.train

# ── Quality ──────────────────────────────────────────────────
test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

lint:
	ruff check src/ tests/ scripts/
	ruff format --check src/ tests/ scripts/

format:
	ruff check --fix src/ tests/ scripts/
	ruff format src/ tests/ scripts/

typecheck:
	mypy src/

# ── Cleanup ──────────────────────────────────────────────────
clean:
	rm -rf data/mediadive.db data/processed/ data/models/ data/raw/api_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
