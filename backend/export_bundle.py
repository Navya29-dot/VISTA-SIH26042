"""
backend/export_bundle.py
=================================================================
VISTA offline content package builder  (SIH26042 - Phase 3)

Turns everything that has been AI-drafted and human-APPROVED in
PostgreSQL into one self-contained bundle that can be copied onto a
2 GB RAM / Android 9+ classroom tablet and used with the Wi-Fi and
mobile data switched off.

One run produces:

    dist/
      vista_bundle_sat_20260904_1830.zip
          manifest.json
          content.sqlite
          assets/
              audio/<filename>.mp3
              worksheets/<filename>.png

Why it works this way
----------------------
- No live AI translation ever happens on the tablet. Everything in
  content.sqlite was already reviewed by a human before export, so the
  device only ever plays back / displays fixed content.
- content.sqlite is a *flat, denormalised* copy of the source tables --
  built specifically for fast, simple queries on cheap hardware, not
  for write-heavy transactional use.
- Missing audio/worksheet files are reported loudly, not skipped
  silently -- a silent "translation" with no audio behind it is the
  single easiest bug to ship by accident.

Usage
-----
    python -m backend.export_bundle --language sat
    python -m backend.export_bundle --language sat --out ./dist \\
        --audio-dir ./audio --worksheet-dir ./worksheets

Requires the `translations` and `worksheets` tables described in
schema_additions.sql. Run that file once against your database before
the first export.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine, create_engine

from backend.config import get_settings


# --------------------------------------------------------------------
# 1. Connect to the source PostgreSQL database
# --------------------------------------------------------------------

def get_source_engine(database_url: str | None = None) -> Engine:
    """
    Resolution order for the *source* (Postgres) connection:
      1. database_url argument / --database-url flag
      2. DATABASE_URL environment variable
      3. backend/.env values (including POSTGRES_* and DATABASE_URL)

    This matches the app's configured database instead of falling back to the
    default Docker credentials on port 5432 when the local project .env file is
    the source of truth.
    """
    if database_url:
        return create_engine(database_url)

    env_database_url = os.getenv("DATABASE_URL")
    if env_database_url:
        return create_engine(env_database_url)

    settings = get_settings()
    return create_engine(settings.sqlalchemy_database_url)


# --------------------------------------------------------------------
# 2. Pull approved content for one language
# --------------------------------------------------------------------

FETCH_CONCEPTS_SQL = text("""
    SELECT id, subject, grade_level, name, key_idea, teacher_note
    FROM concepts
    ORDER BY subject, grade_level, name
""")

FETCH_QUESTIONS_SQL = text("""
    SELECT id, concept_id, language_code, question_text, correct_answer,
           easy_explanation, common_mistake, reteach_method, difficulty
    FROM questions
    WHERE language_code = :language_code AND is_active = TRUE
    ORDER BY concept_id, id
""")

FETCH_TRANSLATIONS_SQL = text("""
    SELECT id, concept_id, language_code, reviewed_text, audio_filename
    FROM translations
    WHERE language_code = :language_code AND review_status = 'approved'
    ORDER BY concept_id, id
""")

FETCH_WORKSHEETS_SQL = text("""
    SELECT id, concept_id, language_code, file_path, worksheet_type
    FROM worksheets
    WHERE language_code = :language_code AND review_status = 'approved'
    ORDER BY concept_id, id
""")


def fetch_bundle_rows(engine: Engine, language_code: str) -> dict:
    with engine.connect() as conn:
        concepts = [dict(r._mapping) for r in conn.execute(FETCH_CONCEPTS_SQL)]
        questions = [dict(r._mapping) for r in conn.execute(
            FETCH_QUESTIONS_SQL, {"language_code": language_code})]
        translations = [dict(r._mapping) for r in conn.execute(
            FETCH_TRANSLATIONS_SQL, {"language_code": language_code})]
        worksheets = [dict(r._mapping) for r in conn.execute(
            FETCH_WORKSHEETS_SQL, {"language_code": language_code})]

    return {
        "concepts": concepts,
        "questions": questions,
        "translations": translations,
        "worksheets": worksheets,
    }


# --------------------------------------------------------------------
# 3. Copy referenced audio / worksheet files into the bundle
# --------------------------------------------------------------------

def copy_assets(rows: dict, audio_source_dir: Path, worksheet_source_dir: Path,
                 bundle_dir: Path) -> dict[str, str]:
    """
    Copies every audio/worksheet file the DB references into
    bundle_dir/assets/... and returns {original_filename: bundle_relative_path}
    for build_sqlite() to store as the on-device asset path.
    """
    audio_out = bundle_dir / "assets" / "audio"
    worksheet_out = bundle_dir / "assets" / "worksheets"
    audio_out.mkdir(parents=True, exist_ok=True)
    worksheet_out.mkdir(parents=True, exist_ok=True)

    lookup: dict[str, str] = {}
    missing: list[str] = []

    for t in rows["translations"]:
        filename = t.get("audio_filename")
        if not filename:
            continue
        src = audio_source_dir / filename
        if not src.exists():
            missing.append(f"audio: {src}")
            continue
        dest_rel = f"audio/{filename}"
        shutil.copy2(src, bundle_dir / "assets" / dest_rel)
        lookup[filename] = dest_rel

    for w in rows["worksheets"]:
        filename = Path(w["file_path"]).name
        src = worksheet_source_dir / filename
        if not src.exists():
            missing.append(f"worksheet: {src}")
            continue
        dest_rel = f"worksheets/{filename}"
        shutil.copy2(src, bundle_dir / "assets" / dest_rel)
        lookup[w["file_path"]] = dest_rel

    if missing:
        print("\n[WARNING] These files are referenced in the database but were NOT found on disk:")
        for m in missing:
            print(f"    - {m}")
        print("They will be included WITHOUT audio/image. Fix the path or re-record, then re-export.\n")

    return lookup


# --------------------------------------------------------------------
# 4. Write the mobile-side SQLite database
# --------------------------------------------------------------------

SQLITE_SCHEMA = """
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY,
    subject TEXT NOT NULL,
    grade_level INTEGER NOT NULL,
    name TEXT NOT NULL,
    key_idea TEXT NOT NULL,
    teacher_note TEXT
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL,
    language_code TEXT NOT NULL,
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    easy_explanation TEXT,
    common_mistake TEXT,
    reteach_method TEXT,
    difficulty TEXT NOT NULL
);

CREATE TABLE translations (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL,
    language_code TEXT NOT NULL,
    reviewed_text TEXT NOT NULL,
    audio_asset TEXT              -- relative path under assets/, NULL if not recorded yet
);

CREATE TABLE worksheets (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL,
    language_code TEXT NOT NULL,
    worksheet_type TEXT NOT NULL, -- 'worksheet' or 'flashcard'
    asset_file TEXT NOT NULL      -- relative path under assets/
);

CREATE INDEX ix_questions_concept ON questions(concept_id);
CREATE INDEX ix_translations_concept ON translations(concept_id);
CREATE INDEX ix_worksheets_concept ON worksheets(concept_id);
"""


def build_sqlite(rows: dict, sqlite_path: Path, asset_lookup: dict[str, str]) -> None:
    if sqlite_path.exists():
        sqlite_path.unlink()

    conn = sqlite3.connect(sqlite_path)
    conn.executescript(SQLITE_SCHEMA)

    conn.executemany(
        "INSERT INTO concepts (id, subject, grade_level, name, key_idea, teacher_note) "
        "VALUES (?,?,?,?,?,?)",
        [(c["id"], c["subject"], c["grade_level"], c["name"], c["key_idea"], c["teacher_note"])
         for c in rows["concepts"]],
    )

    conn.executemany(
        "INSERT INTO questions (id, concept_id, language_code, question_text, correct_answer, "
        "easy_explanation, common_mistake, reteach_method, difficulty) VALUES (?,?,?,?,?,?,?,?,?)",
        [(q["id"], q["concept_id"], q["language_code"], q["question_text"], q["correct_answer"],
          q["easy_explanation"], q["common_mistake"], q["reteach_method"], q["difficulty"])
         for q in rows["questions"]],
    )

    conn.executemany(
        "INSERT INTO translations (id, concept_id, language_code, reviewed_text, audio_asset) "
        "VALUES (?,?,?,?,?)",
        [(t["id"], t["concept_id"], t["language_code"], t["reviewed_text"],
          asset_lookup.get(t["audio_filename"])) for t in rows["translations"]],
    )

    conn.executemany(
        "INSERT INTO worksheets (id, concept_id, language_code, worksheet_type, asset_file) "
        "VALUES (?,?,?,?,?)",
        [(w["id"], w["concept_id"], w["language_code"], w["worksheet_type"],
          asset_lookup.get(w["file_path"], "")) for w in rows["worksheets"]],
    )

    conn.commit()
    conn.close()


# --------------------------------------------------------------------
# 5. Manifest + zip
# --------------------------------------------------------------------

def write_manifest(bundle_dir: Path, language_code: str, rows: dict) -> None:
    manifest = {
        "language_code": language_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "concepts": len(rows["concepts"]),
            "questions": len(rows["questions"]),
            "translations": len(rows["translations"]),
            "worksheets": len(rows["worksheets"]),
        },
        "schema_version": 1,
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def zip_bundle(bundle_dir: Path, out_dir: Path, language_code: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_path = out_dir / f"vista_bundle_{language_code}_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(bundle_dir))

    return zip_path


# --------------------------------------------------------------------
# 6. Orchestration
# --------------------------------------------------------------------

def export_bundle(
    language_code: str,
    database_url: str | None,
    audio_dir: Path,
    worksheet_dir: Path,
    out_dir: Path,
    work_dir: Path,
) -> Path:
    print(f"[export] Connecting to source database for language '{language_code}'...")
    engine = get_source_engine(database_url)

    print("[export] Fetching approved content...")
    rows = fetch_bundle_rows(engine, language_code)
    print(
        f"[export]   concepts={len(rows['concepts'])}  questions={len(rows['questions'])}  "
        f"translations={len(rows['translations'])}  worksheets={len(rows['worksheets'])}"
    )

    if not rows["translations"] and not rows["worksheets"]:
        print("[export] WARNING: no approved translations/worksheets found for this language. "
              "Did you set review_status='approved' yet?")

    bundle_dir = work_dir / f"bundle_{language_code}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    print("[export] Copying audio and worksheet assets...")
    asset_lookup = copy_assets(rows, audio_dir, worksheet_dir, bundle_dir)

    print("[export] Building offline SQLite database...")
    build_sqlite(rows, bundle_dir / "content.sqlite", asset_lookup)

    write_manifest(bundle_dir, language_code, rows)

    print("[export] Zipping bundle...")
    zip_path = zip_bundle(bundle_dir, out_dir, language_code)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n[export] Done: {zip_path}  ({size_mb:.1f} MB)")
    print("[export] Copy this single zip file onto the tablet and unzip it into the app's local storage folder.")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the VISTA offline content bundle for one language.")
    parser.add_argument("--language", required=True, help="Language code, e.g. sat (Santali)")
    parser.add_argument("--database-url", default=None, help="Override the source Postgres connection string")
    parser.add_argument("--audio-dir", default="audio", help="Folder containing recorded audio files")
    parser.add_argument("--worksheet-dir", default="worksheets", help="Folder containing rendered worksheet/flashcard images")
    parser.add_argument("--out", default="dist", help="Folder to write the final zip bundle into")
    parser.add_argument("--work-dir", default=".export_tmp", help="Scratch folder used while building the bundle")
    args = parser.parse_args()

    export_bundle(
        language_code=args.language,
        database_url=args.database_url,
        audio_dir=Path(args.audio_dir),
        worksheet_dir=Path(args.worksheet_dir),
        out_dir=Path(args.out),
        work_dir=Path(args.work_dir),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
