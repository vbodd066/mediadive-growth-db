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

# ── New: Organism data ingestion ──────────────────────────────
ingest-bacteria-bacdive:
	python -m scripts.ingest_all_organisms --bacteria

ingest-fungi-ncbi:
	python -m scripts.ingest_all_organisms --fungi

ingest-protists-ncbi:
	python -m scripts.ingest_all_organisms --protists

ingest-all-organisms:
	python -m scripts.ingest_all_organisms --all --apply-curated

ingest-with-conditions:
	python -m scripts.ingest_all_organisms --all --enrich-conditions --apply-curated

# ── New: MediaDive-NCBI Integration ───────────────────────────
integrate-mediadive-ncbi:
	python -m scripts.integrate_mediadive_ncbi --full

integrate-link-species:
	python -m scripts.integrate_mediadive_ncbi --link-species

integrate-propagate:
	python -m scripts.integrate_mediadive_ncbi --propagate

integrate-stats:
	python -m scripts.integrate_mediadive_ncbi --stats --verbose

features:
	python -m scripts.build_features

# ── ML ───────────────────────────────────────────────────────
train:
	python -m scripts.train

train-cvae:
	python -m scripts.train_cvae --organism bacteria --epochs 100

train-cvae-all:
	python -m scripts.train_cvae --compute-embeddings --all-organisms --epochs 100

build-genome-embeddings:
	python -m scripts.train_cvae --compute-embeddings

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
