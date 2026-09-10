from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    native_name: Mapped[str] = mapped_column(String(80), nullable=False)
    sarvam_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("subject", "grade_level", "name", name="uq_concept_subject_grade_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(80), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, default=5)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_idea: Mapped[str] = mapped_column(Text, nullable=False)
    teacher_note: Mapped[str | None] = mapped_column(Text)

    questions: Mapped[list["Question"]] = relationship(back_populates="concept")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), nullable=False)
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"), default="en-IN")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    easy_explanation: Mapped[str | None] = mapped_column(Text)
    common_mistake: Mapped[str | None] = mapped_column(Text)
    reteach_method: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(40), default="foundation")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    concept: Mapped["Concept"] = relationship(back_populates="questions")
    language: Mapped["Language"] = relationship()
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="question")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    preferred_language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"), default="hi-IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    preferred_language: Mapped["Language"] = relationship()
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="student")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    student_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    language_code: Mapped[str | None] = mapped_column(ForeignKey("languages.code"))
    response_modality: Mapped[str] = mapped_column(String(40), default="text")
    session_id: Mapped[int | None] = mapped_column(ForeignKey("classroom_sessions.id"))
    understanding_status: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column()
    misconception: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    reteach_method: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    student: Mapped["Student | None"] = relationship(back_populates="attempts")
    question: Mapped["Question"] = relationship(back_populates="attempts")
    language: Mapped["Language | None"] = relationship()


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[str | None] = mapped_column(String(80))
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id"))
    teacher_language: Mapped[str] = mapped_column(ForeignKey("languages.code"), default="en-IN", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
