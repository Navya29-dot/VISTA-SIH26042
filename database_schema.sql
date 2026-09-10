CREATE TABLE IF NOT EXISTS languages (
    code VARCHAR(16) PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    native_name VARCHAR(80) NOT NULL,
    sarvam_supported BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS concepts (
    id SERIAL PRIMARY KEY,
    subject VARCHAR(80) NOT NULL,
    grade_level INTEGER NOT NULL DEFAULT 5,
    name VARCHAR(120) NOT NULL,
    key_idea TEXT NOT NULL,
    teacher_note TEXT,
    CONSTRAINT uq_concept_subject_grade_name UNIQUE (subject, grade_level, name)
);

CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language_code VARCHAR(16) NOT NULL DEFAULT 'en-IN' REFERENCES languages(code),
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    easy_explanation TEXT,
    common_mistake TEXT,
    reteach_method TEXT,
    difficulty VARCHAR(40) NOT NULL DEFAULT 'foundation',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(80) NOT NULL UNIQUE,
    preferred_language_code VARCHAR(16) NOT NULL DEFAULT 'hi-IN' REFERENCES languages(code),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    language_code VARCHAR(16) REFERENCES languages(code),
    response_modality VARCHAR(40) NOT NULL DEFAULT 'text',
    misconception TEXT,
    explanation TEXT,
    reteach_method TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classroom_sessions (
    id SERIAL PRIMARY KEY,
    teacher_id VARCHAR(80),
    concept_id INTEGER REFERENCES concepts(id),
    teacher_language VARCHAR(16) NOT NULL DEFAULT 'en-IN',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS translations (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
    draft_text TEXT NOT NULL,
    reviewed_text TEXT,
    audio_filename VARCHAR(200),
    review_status VARCHAR(20) NOT NULL DEFAULT 'draft',
    reviewed_by VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_translation_concept_lang UNIQUE (concept_id, language_code),
    CONSTRAINT ck_translation_review_status CHECK (review_status IN ('draft', 'approved'))
);

CREATE TABLE IF NOT EXISTS worksheets (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language_code VARCHAR(16) NOT NULL REFERENCES languages(code),
    worksheet_type VARCHAR(20) NOT NULL DEFAULT 'worksheet',
    file_path VARCHAR(255) NOT NULL,
    review_status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_worksheet_review_status CHECK (review_status IN ('draft', 'approved'))
);

ALTER TABLE attempts
ADD COLUMN IF NOT EXISTS session_id INTEGER
REFERENCES classroom_sessions(id);

ALTER TABLE attempts
ADD COLUMN IF NOT EXISTS understanding_status VARCHAR(30);

ALTER TABLE attempts
ADD COLUMN IF NOT EXISTS confidence FLOAT;

CREATE INDEX IF NOT EXISTS ix_questions_id ON questions(id);
CREATE INDEX IF NOT EXISTS ix_students_external_id ON students(external_id);
CREATE INDEX IF NOT EXISTS ix_attempts_created_at ON attempts(created_at);
