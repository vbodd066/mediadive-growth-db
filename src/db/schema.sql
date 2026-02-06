-- =========================================
-- MediaDive Growth Database Schema  v2
-- =========================================
-- Mirrors the real MediaDive REST API structure.
-- Run via:  python -m src.db.init_db

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────
-- Media identity + metadata
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS media (
    media_id          TEXT PRIMARY KEY,          -- can be int-like ("1") or alphanumeric ("1a")
    media_name        TEXT NOT NULL,
    is_complex        BOOLEAN NOT NULL DEFAULT 0,
    source            TEXT,
    link              TEXT,
    min_pH            REAL,
    max_pH            REAL,
    reference         TEXT,
    description       TEXT,
    fetched_detail    BOOLEAN NOT NULL DEFAULT 0 -- 1 once /medium/:id has been fetched
);

-- ─────────────────────────────────────────
-- Ingredients (compounds) — master list
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id     INTEGER PRIMARY KEY,
    ingredient_name   TEXT NOT NULL,
    chebi_id          INTEGER,
    cas_rn            TEXT,
    kegg_compound     TEXT,
    pubchem_id        TEXT,
    brenda_ligand     TEXT,
    metacyc_id        TEXT,
    zvg               INTEGER,
    is_complex        BOOLEAN NOT NULL DEFAULT 0,
    molar_mass        REAL,
    formula           TEXT,
    density           REAL
);

-- ─────────────────────────────────────────
-- Solutions — reusable sub-recipes
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS solutions (
    solution_id       INTEGER PRIMARY KEY,
    solution_name     TEXT NOT NULL,
    volume_ml         REAL
);

-- Which solutions belong to which media
CREATE TABLE IF NOT EXISTS media_solutions (
    media_id          TEXT NOT NULL,
    solution_id       INTEGER NOT NULL,
    PRIMARY KEY (media_id, solution_id),
    FOREIGN KEY (media_id)    REFERENCES media(media_id),
    FOREIGN KEY (solution_id) REFERENCES solutions(solution_id)
);

-- ─────────────────────────────────────────
-- Solution recipes — one row per ingredient line
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS solution_recipe (
    solution_id       INTEGER NOT NULL,
    recipe_order      INTEGER NOT NULL,
    ingredient_id     INTEGER,                   -- FK to ingredients (may be NULL for water / gas)
    ingredient_name   TEXT NOT NULL,              -- denormalized for convenience
    amount            REAL,
    unit              TEXT,
    g_per_l           REAL,
    mmol_per_l        REAL,
    is_optional       BOOLEAN NOT NULL DEFAULT 0,
    condition         TEXT,                       -- e.g. "for solid medium"
    sub_solution_id   INTEGER,                   -- if this line references another solution
    PRIMARY KEY (solution_id, recipe_order),
    FOREIGN KEY (solution_id)     REFERENCES solutions(solution_id),
    FOREIGN KEY (ingredient_id)   REFERENCES ingredients(ingredient_id),
    FOREIGN KEY (sub_solution_id) REFERENCES solutions(solution_id)
);

-- ─────────────────────────────────────────
-- Preparation steps per solution
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS solution_steps (
    solution_id       INTEGER NOT NULL,
    step_order        INTEGER NOT NULL,
    step_text         TEXT NOT NULL,
    PRIMARY KEY (solution_id, step_order),
    FOREIGN KEY (solution_id) REFERENCES solutions(solution_id)
);

-- ─────────────────────────────────────────
-- Medium-level molecular composition
-- (flattened across all solutions, from /medium-composition/:id)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS media_composition (
    media_id          TEXT NOT NULL,
    ingredient_id     INTEGER NOT NULL,
    ingredient_name   TEXT NOT NULL,
    g_per_l           REAL,
    mmol_per_l        REAL,
    is_optional       BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (media_id, ingredient_id),
    FOREIGN KEY (media_id)      REFERENCES media(media_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

-- ─────────────────────────────────────────
-- Strains — one row per culture-collection strain
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strains (
    strain_id         INTEGER PRIMARY KEY,
    species           TEXT,
    ccno              TEXT,                       -- culture collection number (e.g. "DSM 1")
    bacdive_id        INTEGER,
    domain            TEXT                        -- B, A, F, Y, P, PH, AL, etc.
);

-- ─────────────────────────────────────────
-- Strain ↔ media growth observations
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strain_growth (
    strain_id         INTEGER NOT NULL,
    media_id          TEXT NOT NULL,
    growth            BOOLEAN NOT NULL,           -- 1 = grows, 0 = does not
    growth_rate       TEXT,
    growth_quality    TEXT,
    modification      TEXT,
    PRIMARY KEY (strain_id, media_id),
    FOREIGN KEY (strain_id) REFERENCES strains(strain_id),
    FOREIGN KEY (media_id)  REFERENCES media(media_id)
);

-- ─────────────────────────────────────────
-- Genomes — microbial genomic sequences
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS genomes (
    genome_id         TEXT PRIMARY KEY,           -- unique identifier (e.g. "GCF_000001405.40")
    strain_id         INTEGER,                    -- FK to strains (optional, may be NULL)
    organism_name     TEXT NOT NULL,
    organism_type     TEXT NOT NULL,              -- 'bacteria', 'archea', 'fungi', 'protist', 'virus'
    taxid             INTEGER,                    -- NCBI taxonomy ID
    gc_content        REAL,                       -- GC% (0-100)
    sequence_length   INTEGER,                    -- base pairs
    fasta_path        TEXT,                       -- local path to FASTA file (relative to data/raw/genomes/)
    fasta_hash        TEXT,                       -- SHA-256 hash of FASTA content
    fetched_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (strain_id) REFERENCES strains(strain_id)
);

-- ─────────────────────────────────────────
-- Genome embeddings — pre-computed features
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS genome_embeddings (
    genome_id         TEXT PRIMARY KEY,
    embedding_model   TEXT NOT NULL,              -- e.g. 'kmer_128', 'prottrans_t5', 'genomic_features'
    embedding         BLOB,                       -- binary-encoded numpy array (pickle or msgpack)
    embedding_dim     INTEGER NOT NULL,
    computed_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (genome_id) REFERENCES genomes(genome_id)
);

-- ─────────────────────────────────────────
-- Genome ↔ media growth observations
-- (supplements strain_growth with genomic data)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS genome_growth (
    genome_id         TEXT NOT NULL,
    media_id          TEXT NOT NULL,
    growth            BOOLEAN NOT NULL,           -- 1 = grows, 0 = does not
    growth_rate       TEXT,
    confidence        REAL,                       -- confidence score [0-1]
    source            TEXT,                       -- e.g. 'literature', 'experiment', 'in_silico'
    PRIMARY KEY (genome_id, media_id),
    FOREIGN KEY (genome_id) REFERENCES genomes(genome_id),
    FOREIGN KEY (media_id)  REFERENCES media(media_id)
);

-- ─────────────────────────────────────────
-- Ingest progress tracking
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingest_log (
    task              TEXT PRIMARY KEY,           -- e.g. "media_list", "medium_detail:123"
    status            TEXT NOT NULL DEFAULT 'pending',  -- pending | done | error
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    error_message     TEXT
);

-- ─────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_media_complex       ON media(is_complex);
CREATE INDEX IF NOT EXISTS idx_media_source        ON media(source);
CREATE INDEX IF NOT EXISTS idx_ingredient_name     ON ingredients(ingredient_name);
CREATE INDEX IF NOT EXISTS idx_ingredient_formula  ON ingredients(formula);
CREATE INDEX IF NOT EXISTS idx_strain_species      ON strains(species);
CREATE INDEX IF NOT EXISTS idx_strain_domain       ON strains(domain);
CREATE INDEX IF NOT EXISTS idx_strain_bacdive      ON strains(bacdive_id);
CREATE INDEX IF NOT EXISTS idx_growth_media        ON strain_growth(media_id);
CREATE INDEX IF NOT EXISTS idx_growth_strain       ON strain_growth(strain_id);
CREATE INDEX IF NOT EXISTS idx_composition_media   ON media_composition(media_id);
CREATE INDEX IF NOT EXISTS idx_solution_recipe_ing ON solution_recipe(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_genome_organism_type ON genomes(organism_type);
CREATE INDEX IF NOT EXISTS idx_genome_taxid       ON genomes(taxid);
CREATE INDEX IF NOT EXISTS idx_genome_strain      ON genomes(strain_id);
CREATE INDEX IF NOT EXISTS idx_genome_emb_model   ON genome_embeddings(embedding_model);
CREATE INDEX IF NOT EXISTS idx_genome_growth_media ON genome_growth(media_id);
CREATE INDEX IF NOT EXISTS idx_genome_growth_genome ON genome_growth(genome_id);
