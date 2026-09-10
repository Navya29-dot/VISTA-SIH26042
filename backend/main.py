import json
from io import BytesIO

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ai import (
    analyze_mistake,
    copilot_answer,
    explain_doubt,
    generate_personalized_worksheet,
    generate_practice_question,
    generate_worksheet,
)
from backend.answer_evaluator import evaluate_answer
from backend.database import Base, engine, get_db
from backend.models import Attempt, ClassroomSession, Concept, Language, Question, Student
from backend.schemas import (
    AnswerRequest,
    ConceptRead,
    LanguageRead,
    ProgressRead,
    QuestionRead,
    SpeechRequest,
    ExplanationRequest,
    OfflineTranslationRequest,
    TranslationApprovalRequest,
    TranslationDraftRequest,
    TranslationRequest,
    PersonalizedWorksheetRequest,
    CopilotRequest,
    TextToSpeechRequest,
)
from backend.indictrans2 import translate as indictrans2_translate
from backend.vosk_offline import transcribe_wav

app = FastAPI(
    title="VISTA API",
    description="Offline vernacular pedagogy engine with SQLite and local language models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://localhost",
        "capacitor://localhost",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartClassRequest(BaseModel):
    teacher_id: str
    concept_id: int = Field(..., gt=0)
    teacher_language: str = "en-IN"


@app.post("/classroom/start")
def start_class(request: StartClassRequest, db: Session = Depends(get_db)):
    concept = db.get(Concept, request.concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    session = ClassroomSession(
        teacher_id=request.teacher_id,
        concept_id=request.concept_id,
        teacher_language=request.teacher_language,
        is_active=True,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "message": "Class started"
    }

class TeacherSpeechRequest(BaseModel):
    session_id: int
    transcript: str
    source_language: str
    target_language: str

class StudentResponseRequest(BaseModel):
    session_id: int
    student_id: int
    question_id: int
    answer: str
    language_code: str
    response_modality: str = "speech"

class WorksheetExportRequest(BaseModel):
    title: str
    level: str
    outcome: str
    sections: dict[str, object]
    flashcards: list[list[str]]


@app.post("/worksheets/personalized")
def personalized_worksheet(
    request: PersonalizedWorksheetRequest,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.external_id == request.student_id).one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found. Submit an answer first.")

    attempts = (
        db.query(Attempt)
        .filter(Attempt.student_id == student.id)
        .order_by(Attempt.created_at.desc())
        .limit(100)
        .all()
    )
    concept_stats: dict[str, dict[str, int | str]] = {}
    for attempt in attempts:
        concept = attempt.question.concept
        if request.topic and request.topic.lower() not in f"{concept.subject} {concept.name}".lower():
            continue
        key = f"{concept.subject} · {concept.name}"
        stats = concept_stats.setdefault(key, {"concept": key, "total": 0, "correct": 0})
        stats["total"] = int(stats["total"]) + 1
        stats["correct"] = int(stats["correct"]) + int(attempt.is_correct)

    measured = [
        {
            **stats,
            "accuracy": round(int(stats["correct"]) / int(stats["total"]) * 100, 1),
        }
        for stats in concept_stats.values()
    ]
    weak_areas = sorted((item for item in measured if item["accuracy"] < 75), key=lambda item: item["accuracy"])
    strengths = sorted((item for item in measured if item["accuracy"] >= 75), key=lambda item: item["accuracy"], reverse=True)
    generated = generate_personalized_worksheet(
        student_id=request.student_id,
        grade_level=request.grade_level,
        weak_areas=weak_areas,
        strengths=strengths,
        language=request.language_code,
        topic=request.topic,
    )
    return {
        "student_id": request.student_id,
        "attempts_considered": len(attempts),
        "weak_areas": weak_areas,
        "strengths": strengths,
        "worksheet": generated,
    }


@app.post("/copilot")
def ask_copilot(request: CopilotRequest):
    if request.language_code not in {"hi-IN", "sat", "sat-IN"}:
        raise HTTPException(status_code=400, detail="Copilot supports Hindi (hi-IN) and Santali (sat).")
    return copilot_answer(request.question, request.language_code, request.context)


@app.post("/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    raise HTTPException(
        status_code=501,
        detail="Offline TTS uses bundled approved recordings or the Android device voice.",
    )

@app.post("/worksheets/export/docx")
def export_worksheet_docx(request: WorksheetExportRequest):
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="DOCX export requires python-docx.") from exc

    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    normal = document.styles["Normal"]
    normal.font.name = "Nirmala UI"
    normal.font.size = Pt(10)
    heading = document.add_heading(f"{request.level} · {request.title}", level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    outcome = document.add_paragraph(request.outcome)
    outcome.paragraph_format.space_after = Pt(8)
    sections = request.sections
    prompts = (
        ("1 · Match", sections.get("match", [])),
        ("2 · Fill in", sections.get("fill", [])),
        ("3 · Choose", sections.get("mcq", [])),
        ("4 · Say it aloud", [sections.get("oral", "")]),
    )
    for label, items in prompts:
        document.add_heading(label, level=2)
        for item in items:
            paragraph = document.add_paragraph(str(item), style="List Bullet")
            paragraph.paragraph_format.keep_together = True
    document.add_heading("Teacher check", level=2)
    document.add_paragraph("Mark Understood, Unsure, or Needs help after the oral response.")
    document.add_heading("Flashcards", level=2)
    for card in request.flashcards:
        document.add_paragraph(" · ".join(str(value) for value in card), style="List Bullet")

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=vista-worksheet.docx"},
    )

@app.post("/classroom/translate")
def classroom_translate(request: TeacherSpeechRequest):

    translated = translate_text(
        text=request.transcript,
        source_language=request.source_language,
        target_language=request.target_language,
    )

    return {
        "original": request.transcript,
        "translated": translated,
        "source_language": request.source_language,
        "target_language": request.target_language,
    }

@app.on_event("startup")
def create_tables() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        raise RuntimeError(
            "VISTA could not initialize its local SQLite database. "
            "Check that the data directory is writable."
        ) from exc


@app.get("/")
def home():
    return {
        "message": "Welcome to VISTA - Vernacular Intelligence for Smart Teaching & Adaptation!",
        "database": "Local SQLite",
        "language_engine": "Local IndicTrans2",
        "offline": True,
    }


@app.get("/languages", response_model=list[LanguageRead])
def list_languages(db: Session = Depends(get_db)):
    return db.query(Language).filter(Language.is_active.is_(True)).order_by(Language.name).all()


@app.get("/concepts", response_model=list[ConceptRead])
def list_concepts(subject: str | None = None, grade_level: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Concept)
    if subject:
        query = query.filter(Concept.subject.ilike(subject))
    if grade_level:
        query = query.filter(Concept.grade_level == grade_level)
    return query.order_by(Concept.subject, Concept.name).all()


@app.get("/question/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.get("/questions", response_model=list[QuestionRead])
def list_questions(
    concept_id: int | None = None,
    language_code: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Question).filter(Question.is_active.is_(True))
    if concept_id:
        query = query.filter(Question.concept_id == concept_id)
    if language_code:
        query = query.filter(Question.language_code == language_code)
    return query.order_by(Question.id).all()


@app.post("/answer")
def check_answer(data: AnswerRequest, db: Session = Depends(get_db)):
    question = db.get(Question, data.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    student = _get_or_create_student(db, data.student_id, data.language_code)
    evaluation = evaluate_answer(data.answer, question.correct_answer)
    is_correct = evaluation["is_correct"]

    attempt = Attempt(
        student_id=student.id if student else None,
        question_id=question.id,
        student_answer=data.answer,
        is_correct=is_correct,
        language_code=data.language_code or (student.preferred_language_code if student else question.language_code),
        response_modality=data.response_modality,
    )

    if is_correct:
        attempt.explanation = evaluation["matching_reason"]
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return {
            "correct": True,
            "attempt_id": attempt.id,
            "message": "Correct answer!",
            "confidence": evaluation["confidence"],
            "matching_reason": evaluation["matching_reason"],
        }

    ai_analysis = analyze_mistake(question.question_text, question.correct_answer, data.answer)
    practice_question = generate_practice_question(question.question_text, question.concept.name)

    attempt.misconception = ai_analysis.get("misconception")
    attempt.explanation = ai_analysis.get("explanation")
    attempt.reteach_method = ai_analysis.get("reteach_method")
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "correct": False,
        "attempt_id": attempt.id,
        "confidence": evaluation["confidence"],
        "matching_reason": evaluation["matching_reason"],
        **ai_analysis,
        "practice_question": practice_question,
    }


@app.get("/attempts")
def get_attempts(student_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Attempt).order_by(Attempt.created_at.desc())
    if student_id:
        query = query.join(Student).filter(Student.external_id == student_id)
    return [
        {
            "id": attempt.id,
            "student_id": attempt.student.external_id if attempt.student else None,
            "question_id": attempt.question_id,
            "student_answer": attempt.student_answer,
            "correct": attempt.is_correct,
            "concept": attempt.question.concept.name,
            "language_code": attempt.language_code,
            "response_modality": attempt.response_modality,
            "misconception": attempt.misconception,
            "explanation": attempt.explanation,
            "reteach_method": attempt.reteach_method,
            "created_at": attempt.created_at,
        }
        for attempt in query.limit(100).all()
    ]


@app.get("/progress", response_model=ProgressRead)
def get_progress(student_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Attempt)
    if student_id:
        query = query.join(Student).filter(Student.external_id == student_id)

    attempts = query.all()
    total_attempts = len(attempts)
    correct_attempts = sum(1 for attempt in attempts if attempt.is_correct)
    wrong_attempts = total_attempts - correct_attempts
    accuracy = (correct_attempts / total_attempts) * 100 if total_attempts else 0

    weak_concepts: dict[str, int] = {}
    for attempt in attempts:
        if not attempt.is_correct:
            concept_name = attempt.question.concept.name
            weak_concepts[concept_name] = weak_concepts.get(concept_name, 0) + 1

    possible_misconceptions = [
        {
            "concept": concept,
            "wrong_attempts": count,
            "message": "Student may need help with this concept.",
        }
        for concept, count in weak_concepts.items()
        if count >= 2
    ]

    return {
        "total_attempts": total_attempts,
        "correct": correct_attempts,
        "wrong": wrong_attempts,
        "accuracy": round(accuracy, 2),
        "possible_misconceptions": possible_misconceptions,
    }


@app.post("/translate")
def translate_text(
    data: TranslationRequest,
    db: Session = Depends(get_db),
):
    _ensure_language_exists(db, data.source_language_code)
    _ensure_language_exists(db, data.target_language_code)
    return indictrans2_translate(
        text=data.text,
        source_language_code=data.source_language_code,
        target_language_code=data.target_language_code,
    )


@app.post("/translate/offline")
def translate_offline(data: OfflineTranslationRequest):
    return indictrans2_translate(
        text=data.text,
        source_language_code=data.source_language_code,
        target_language_code=data.target_language_code,
    )


@app.post("/translations/draft")
def create_translation_draft(
    data: TranslationDraftRequest,
    db: Session = Depends(get_db),
):
    concept = db.get(Concept, data.concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    _ensure_language_exists(db, data.language_code)

    generated = generate_worksheet(
        concept=f"{concept.name}: {concept.key_idea}",
        language=data.language_code,
    )
    draft_text = json.dumps(generated, ensure_ascii=False)
    existing = db.execute(
        text(
            "SELECT id FROM translations "
            "WHERE concept_id = :concept_id AND language_code = :language_code"
        ),
        {"concept_id": data.concept_id, "language_code": data.language_code},
    ).scalar_one_or_none()

    if existing:
        translation_id = existing
        db.execute(
            text(
                "UPDATE translations SET draft_text = :draft_text, "
                "review_status = 'draft', reviewed_text = NULL, reviewed_by = NULL "
                "WHERE id = :id"
            ),
            {"draft_text": draft_text, "id": translation_id},
        )
    else:
        translation_id = db.execute(
            text(
                "INSERT INTO translations "
                "(concept_id, language_code, draft_text, review_status) "
                "VALUES (:concept_id, :language_code, :draft_text, 'draft') "
                "RETURNING id"
            ),
            {
                "concept_id": data.concept_id,
                "language_code": data.language_code,
                "draft_text": draft_text,
            },
        ).scalar_one()
    db.commit()
    return {
        "translation_id": translation_id,
        "concept_id": data.concept_id,
        "language_code": data.language_code,
        "review_status": "draft",
        "draft": generated,
    }


@app.post("/translations/approve")
def approve_translation(
    data: TranslationApprovalRequest,
    db: Session = Depends(get_db),
):
    translation = db.execute(
        text(
            "SELECT id, concept_id, language_code FROM translations WHERE id = :id"
        ),
        {"id": data.translation_id},
    ).mappings().one_or_none()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation draft not found")

    db.execute(
        text(
            "UPDATE translations SET reviewed_text = :reviewed_text, "
            "reviewed_by = :reviewed_by, audio_filename = :audio_filename, "
            "review_status = 'approved' WHERE id = :id"
        ),
        {
            "reviewed_text": data.reviewed_text,
            "reviewed_by": data.reviewed_by,
            "audio_filename": data.audio_filename,
            "id": data.translation_id,
        },
    )
    db.commit()
    return {
        "translation_id": translation["id"],
        "concept_id": translation["concept_id"],
        "language_code": translation["language_code"],
        "review_status": "approved",
        "audio_filename": data.audio_filename,
    }


@app.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    language_code: str = Form("unknown"),
    mode: str = Form("transcribe"),
    db: Session = Depends(get_db),
):
    if language_code != "unknown":
        _ensure_language_exists(db, language_code)
    return await transcribe_wav(file=file, language_code=language_code)


@app.post("/speech-to-text/offline")
async def speech_to_text_offline(
    file: UploadFile = File(...),
    language_code: str = Form("hi-IN"),
):
    return await transcribe_wav(file, language_code=language_code)


@app.post("/voice-bridge/offline")
async def offline_voice_bridge(
    file: UploadFile = File(...),
    source_language_code: str = Form("hi-IN"),
    target_language_code: str = Form("sat"),
):
    if source_language_code not in {"hi-IN", "en-IN"}:
        raise HTTPException(status_code=400, detail="Voice bridge supports hi-IN and en-IN.")
    transcription = await transcribe_wav(file, language_code=source_language_code)
    transcript = str(transcription["text"])
    if not transcript:
        return {
            "transcript": "",
            "translated_text": "",
            "matched": False,
            "message": "No speech was recognized.",
            "offline": True,
        }
    translation = indictrans2_translate(
        text=transcript,
        source_language_code=source_language_code,
        target_language_code=target_language_code,
    )
    return {
        "transcript": transcript,
        "translated_text": translation["translated_text"],
        "source_language_code": source_language_code,
        "target_language_code": target_language_code,
        "transcription_engine": "vosk",
        "translation_engine": "indictrans2",
        "matched": True,
        "offline": True,
    }


@app.post("/language-support")
def language_support(data: SpeechRequest, db: Session = Depends(get_db)):
    _ensure_language_exists(db, data.language_code)
    return {"supported": True, "language_code": data.language_code}


@app.post("/explain")
def explain_student_doubt(data: ExplanationRequest):
    return explain_doubt(
        question=data.question,
        subject=data.subject,
        topic=data.topic,
        language_code=data.language_code,
    )


def _ensure_language_exists(db: Session, language_code: str) -> None:
    language = db.get(Language, language_code)
    if not language or not language.is_active:
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {language_code}")


def _get_or_create_student(db: Session, external_id: str | None, language_code: str | None) -> Student | None:
    if not external_id:
        return None

    student = db.query(Student).filter(Student.external_id == external_id).one_or_none()
    if student:
        if language_code and student.preferred_language_code != language_code:
            _ensure_language_exists(db, language_code)
            student.preferred_language_code = language_code
            db.add(student)
            db.commit()
            db.refresh(student)
        return student

    preferred_language_code = language_code or "hi-IN"
    _ensure_language_exists(db, preferred_language_code)
    student = Student(external_id=external_id, preferred_language_code=preferred_language_code)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@app.post("/classroom/understand")
def understand_student(
    request: StudentResponseRequest,
    db: Session = Depends(get_db)
):
    question = (
        db.query(Question)
        .filter(Question.id == request.question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    analysis = analyze_mistake(
        question.question_text,
        question.correct_answer,
        request.answer
    )

    is_correct = (
        request.answer.strip().lower()
        == question.correct_answer.strip().lower()
    )

    if is_correct:
        status = "understood"
    else:
        status = "needs_help"

    attempt = Attempt(
        student_id=request.student_id,
        question_id=request.question_id,
        student_answer=request.answer,
        is_correct=is_correct,
        language_code=request.language_code,
        response_modality=request.response_modality,
        misconception=analysis.get("misconception"),
        explanation=analysis.get("explanation"),
        reteach_method=analysis.get("reteach_method"),
        session_id=request.session_id,
        understanding_status=status,
        confidence=0.90 if is_correct else 0.82,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "student_id": request.student_id,
        "status": status,
        "misconception": analysis.get("misconception"),
        "explanation": analysis.get("explanation"),
        "reteach_method": analysis.get("reteach_method"),
    }
async def send_class_update(session_id: int, data: dict):
    websocket = connected_teachers.get(session_id)

    if websocket:
        await websocket.send_json(data)

@app.post("/classroom/help")
def request_help(
    student_id: int,
    session_id: int,
    concept_id: int
):
    return {
        "student_id": student_id,
        "session_id": session_id,
        "status": "needs_help"
    }
  
connected_teachers = {}

@app.websocket("/ws/classroom/{session_id}")
async def classroom_socket(websocket: WebSocket, session_id: int):
    await websocket.accept()

    connected_teachers[session_id] = websocket

    try:
        while True:
            await websocket.receive_text()

    except Exception:
        connected_teachers.pop(session_id, None)
class ReteachRequest(BaseModel):
    concept: str
    misconception: str
    language_code: str
    grade: int


@app.post("/classroom/reteach")
def reteach(request: ReteachRequest):

    prompt = f"""
You are an adaptive primary-school teacher.

Concept:
{request.concept}

Student misconception:
{request.misconception}

Language:
{request.language_code}

Grade:
{request.grade}

Create a NEW explanation.

Do not repeat the previous explanation.

Use:
1. One concrete example
2. One visual idea
3. One very easy question
"""

    # call your existing LLM here

    return {
        "method": "visual + concrete example",
        "message": "New teaching explanation generated."
    }
