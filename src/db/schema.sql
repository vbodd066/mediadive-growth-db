-- =========================================
-- MediaDive Growth Database Schema
-- =========================================

-- -------------------------
-- Media identity + metadata
-- -------------------------
DROP TABLE IF EXISTS media;

CREATE TABLE media (
    media_id TEXT PRIMARY KEY,
    media_name TEXT NOT NULL,
    media_type TEXT CHECK (media_type IN ('defined', 'complex')),
    source TEXT,
    min_pH REAL,
    max_pH REAL,
    composition_missing BOOLEAN DEFAULT FALSE
);

-- -------------------------
-- Ingredient ontology
-- -------------------------
DROP TABLE IF EXISTS ingredients;

CREATE TABLE ingredients (
    ingredient_id INTEGER PRIMARY KEY,
    ingredient_name TEXT NOT NULL,
    ingredient_class TEXT,
    formula TEXT,
    kegg_id TEXT
);

-- -----------------------------------
-- Media ↔ ingredient composition
-- -----------------------------------
DROP TABLE IF EXISTS media_ingredients;

CREATE TABLE media_ingredients (
    media_id TEXT NOT NULL,
    ingredient_id INTEGER NOT NULL,
    concentration_value REAL,
    concentration_unit TEXT,
    concentration_missing BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (media_id, ingredient_id),
    FOREIGN KEY (media_id) REFERENCES media(media_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

-- -----------------------------------
-- Strain ↔ media growth observations
-- -----------------------------------
DROP TABLE IF EXISTS strain_growth;

CREATE TABLE strain_growth (
    strain_id INTEGER NOT NULL,
    media_id TEXT NOT NULL,
    growth_observed BOOLEAN NOT NULL,
    PRIMARY KEY (strain_id, media_id),
    FOREIGN KEY (media_id) REFERENCES media(media_id)
);

-- -----------------------------------
-- Helpful indexes (optional but smart)
-- -----------------------------------
CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
CREATE INDEX IF NOT EXISTS idx_media_source ON media(source);
CREATE INDEX IF NOT EXISTS idx_ingredient_name ON ingredients(ingredient_name);
