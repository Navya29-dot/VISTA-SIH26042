"""
backend/seed_database.py
=================================================================
VISTA database seeder  (Layer 1 -- run this BEFORE export_bundle.py)

This is the file main.py and README_BACKEND.md already call
(`python -m backend.seed_database`), completing the setup they
describe.

What it does, in order:
  1. Applies database_schema.sql and schema_additions.sql -- safe to
     run repeatedly, since every statement in both files is
     IF NOT EXISTS / idempotent.
  2. Inserts a small set of real FLN-style curriculum content
     (languages, concepts, questions) if it isn't already there.
  3. Inserts a couple of translations and worksheets in different
     review states (draft vs approved) so that:
       - You have something to actually show a reviewer approving.
       - backend/export_bundle.py has real approved content to pull
         the moment you run it -- Layer 2 is worthless without this.

Run:
    python -m backend.seed_database

Safe to run multiple times -- every insert is "skip if it already
exists", never a duplicate or an overwrite of reviewed content.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine, create_engine

from backend.config import get_settings
from backend.database import Base
from backend import models  # noqa: F401 - register ORM tables before create_all

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILES = [
    PROJECT_ROOT / "database_schema.sql",
    PROJECT_ROOT / "schema_additions.sql",
]


# --------------------------------------------------------------------
# 1. Connection (same resolution order as export_bundle.py, so both
#    scripts always point at the same database without extra setup)
# --------------------------------------------------------------------

def get_engine(database_url: str | None = None) -> Engine:
    if database_url:
        return create_engine(database_url)

    settings = get_settings()
    return create_engine(settings.sqlalchemy_database_url)


# --------------------------------------------------------------------
# 2. Apply schema files (idempotent -- every statement in them uses
#    IF NOT EXISTS)
# --------------------------------------------------------------------

def apply_schema(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("""CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY, concept_id INTEGER NOT NULL REFERENCES concepts(id),
                language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
                draft_text TEXT NOT NULL, reviewed_text TEXT, audio_filename VARCHAR(200),
                review_status VARCHAR(20) NOT NULL DEFAULT 'draft', reviewed_by VARCHAR(120),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (concept_id, language_code))"""))
            conn.execute(text("""CREATE TABLE IF NOT EXISTS worksheets (
                id INTEGER PRIMARY KEY, concept_id INTEGER NOT NULL REFERENCES concepts(id),
                language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
                worksheet_type VARCHAR(20) NOT NULL DEFAULT 'worksheet',
                file_path VARCHAR(255) NOT NULL, review_status VARCHAR(20) NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))
        return
    for schema_file in SCHEMA_FILES:
        if not schema_file.exists():
            print(f"[seed] WARNING: {schema_file.name} not found next to this script -- skipping.")
            continue
        sql = schema_file.read_text(encoding="utf-8")
        print(f"[seed] Applying {schema_file.name}...")
        with engine.begin() as conn:
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))


# --------------------------------------------------------------------
# 3. Seed curriculum content
# --------------------------------------------------------------------

LANGUAGES = [
    # code,    name,       native_name,  sarvam_supported
    ("hi-IN", "Hindi", "\u0939\u093f\u0902\u0926\u0940", True),
    ("sat", "Santali", "\u1c65\u1c58\u1c5e\u1c62\u1c72\u1c58", False),
]

CONCEPTS = [
    # id, subject, grade_level, name, key_idea, teacher_note
    (1, "Math", 3, "Comparing Fractions",
     "1/2 is greater than 1/4 because the same whole is split into fewer, bigger parts.",
     "Use a roti or pizza cut into halves vs quarters to show this physically."),
    (2, "Math", 2, "Counting to 20",
     "Counting objects one by one up to 20 without skipping or repeating.",
     "Use stones, seeds, or fingers -- anything the child can physically move while counting."),
    (3, "EVS", 3, "Parts of a Plant",
     "A plant has roots, stem, leaves, flowers, and fruit, each with a different job.",
     "Bring an actual small plant or a labelled drawing into class."),
]

QUESTIONS = [
    # id, concept_id, language_code, question_text, correct_answer, easy_explanation,
    # common_mistake, reteach_method, difficulty
    (1, 1, "hi-IN", "Which is greater: 1/2 or 1/4?", "1/2",
     "Half a roti is bigger than a quarter of the same roti.",
     "Thinking a bigger denominator (4) means a bigger number.",
     "Cut two same-size paper circles, one into 2 parts and one into 4, and compare pieces.",
     "foundation"),
    (2, 2, "hi-IN", "Count these stones and write the number.", "14",
     "Count each stone once, moving it aside as you count.",
     "Skipping a stone or counting one twice.",
     "Line the stones up in a row before counting.",
     "foundation"),
]

# Simulates what ai.py's generate_worksheet()/analyze_mistake() Groq calls
# would produce -- one already reviewed and approved, one still a draft,
# so you can see and demo both states.
TRANSLATIONS = [
    # id, concept_id, language_code, draft_text, reviewed_text, audio_filename, review_status
    (1, 1, "sat", "draft santali text for fractions",
     "reviewed santali explanation: adha roti pura se bada hai chauthai se",
     "concept1_fractions_sat.mp3", "approved"),
    (2, 2, "sat", "draft santali text for counting to 20",
     None, "concept2_counting_sat.mp3", "draft"),
]

WORKSHEETS = [
    # id, concept_id, language_code, worksheet_type, file_path, review_status
    (1, 1, "sat", "worksheet", "fractions_worksheet_sat.png", "approved"),
    (2, 1, "sat", "flashcard", "fractions_flashcard_sat.png", "approved"),
    (3, 2, "sat", "worksheet", "counting_worksheet_sat.png", "draft"),
]


def seed_content(engine: Engine) -> None:
    with engine.begin() as conn:
        for code, name, native_name, sarvam in LANGUAGES:
            conn.execute(text(
                "INSERT INTO languages "
                "(code, name, native_name, sarvam_supported, is_active) "
                "VALUES (:code, :name, :native_name, :sarvam, TRUE) "
                "ON CONFLICT (code) DO NOTHING"
            ), {"code": code, "name": name, "native_name": native_name, "sarvam": sarvam})

        for id_, subject, grade, name, key_idea, note in CONCEPTS:
            conn.execute(text(
                "INSERT INTO concepts (id, subject, grade_level, name, key_idea, teacher_note) "
                "VALUES (:id, :subject, :grade, :name, :key_idea, :note) "
                "ON CONFLICT (id) DO NOTHING"
            ), {"id": id_, "subject": subject, "grade": grade, "name": name,
                "key_idea": key_idea, "note": note})

        for (id_, concept_id, lang, q_text, answer, explanation,
             mistake, reteach, difficulty) in QUESTIONS:
            conn.execute(text(
                "INSERT INTO questions (id, concept_id, language_code, question_text, "
                "correct_answer, easy_explanation, common_mistake, reteach_method, "
                "difficulty, is_active) "
                "VALUES (:id, :cid, :lang, :qt, :ans, :exp, :mis, :ret, :diff, TRUE) "
                "ON CONFLICT (id) DO NOTHING"
            ), {"id": id_, "cid": concept_id, "lang": lang, "qt": q_text, "ans": answer,
                "exp": explanation, "mis": mistake, "ret": reteach, "diff": difficulty})

        for (id_, concept_id, lang, draft, reviewed, audio, status) in TRANSLATIONS:
            conn.execute(text(
                "INSERT INTO translations (id, concept_id, language_code, draft_text, "
                "reviewed_text, audio_filename, review_status) "
                "VALUES (:id, :cid, :lang, :draft, :reviewed, :audio, :status) "
                "ON CONFLICT (id) DO NOTHING"
            ), {"id": id_, "cid": concept_id, "lang": lang, "draft": draft,
                "reviewed": reviewed, "audio": audio, "status": status})
            # Postgres SERIAL won't know about our manually-set ids -- keep the
            # sequence ahead so future API-created rows don't collide.
            if engine.dialect.name != "sqlite":
                conn.execute(text(
                    "SELECT setval('translations_id_seq', "
                    "(SELECT COALESCE(MAX(id), 1) FROM translations))"
                ))

        for (id_, concept_id, lang, wtype, path, status) in WORKSHEETS:
            conn.execute(text(
                "INSERT INTO worksheets (id, concept_id, language_code, worksheet_type, "
                "file_path, review_status) VALUES (:id, :cid, :lang, :wtype, :path, :status) "
                "ON CONFLICT (id) DO NOTHING"
            ), {"id": id_, "cid": concept_id, "lang": lang, "wtype": wtype,
                "path": path, "status": status})
            if engine.dialect.name != "sqlite":
                conn.execute(text(
                    "SELECT setval('worksheets_id_seq', "
                    "(SELECT COALESCE(MAX(id), 1) FROM worksheets))"
                ))

        # Keep concepts/questions sequences ahead of our manual ids too.
        if engine.dialect.name != "sqlite":
            conn.execute(text("SELECT setval('concepts_id_seq', (SELECT COALESCE(MAX(id), 1) FROM concepts))"))
            conn.execute(text("SELECT setval('questions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM questions))"))


def print_summary(engine: Engine) -> None:
    with engine.connect() as conn:
        counts = {}
        for table in ["languages", "concepts", "questions", "translations", "worksheets"]:
            counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        approved_t = conn.execute(text(
            "SELECT COUNT(*) FROM translations WHERE review_status = 'approved'"
        )).scalar()
        approved_w = conn.execute(text(
            "SELECT COUNT(*) FROM worksheets WHERE review_status = 'approved'"
        )).scalar()

    print("\n[seed] Database contents:")
    for table, n in counts.items():
        print(f"[seed]   {table:14s} {n}")
    print(f"[seed]   -> {approved_t} translation(s) and {approved_w} worksheet(s) are APPROVED "
          f"and ready for export_bundle.py")


def main() -> int:
    engine = get_engine()
    print("[seed] Applying schema (safe to re-run)...")
    apply_schema(engine)
    print("[seed] Inserting curriculum, translations, and worksheets (safe to re-run)...")
    seed_content(engine)
    print_summary(engine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
