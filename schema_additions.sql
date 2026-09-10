-- schema_additions.sql
-- Adds the translation-review workflow and worksheet tracking that
-- backend/export_bundle.py reads from. Safe to run multiple times.
-- Run this once against the same database as database_schema.sql.

CREATE TABLE IF NOT EXISTS translations (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
    draft_text TEXT NOT NULL,
    reviewed_text TEXT,
    audio_filename VARCHAR(200),
    review_status VARCHAR(20) NOT NULL DEFAULT 'draft',   -- 'draft' | 'approved'
    reviewed_by VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_translation_concept_lang UNIQUE (concept_id, language_code),
    CONSTRAINT ck_translation_review_status CHECK (review_status IN ('draft', 'approved'))
);

CREATE TABLE IF NOT EXISTS worksheets (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
    worksheet_type VARCHAR(20) NOT NULL DEFAULT 'worksheet',  -- 'worksheet' | 'flashcard'
    file_path VARCHAR(255) NOT NULL,
    review_status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_worksheet_review_status CHECK (review_status IN ('draft', 'approved'))
);

CREATE INDEX IF NOT EXISTS ix_translations_lang_status ON translations(language_code, review_status);
CREATE INDEX IF NOT EXISTS ix_worksheets_lang_status ON worksheets(language_code, review_status);
