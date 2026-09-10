from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question_id: int
    answer: str
    student_id: str | None = None
    language_code: str | None = None
    response_modality: str = "text"


class TranslationRequest(BaseModel):
    text: str = Field(..., max_length=2000)
    source_language_code: str = "en-IN"
    target_language_code: str


class OfflineTranslationRequest(TranslationRequest):
    pass


class TranslationDraftRequest(BaseModel):
    concept_id: int = Field(..., gt=0)
    language_code: str = Field(..., min_length=2, max_length=16)


class TranslationApprovalRequest(BaseModel):
    translation_id: int = Field(..., gt=0)
    reviewed_text: str = Field(..., min_length=1, max_length=20000)
    reviewed_by: str | None = Field(default=None, max_length=120)
    audio_filename: str | None = Field(default=None, max_length=200)


class SpeechRequest(BaseModel):
    language_code: str


class ExplanationRequest(BaseModel):
    question: str
    subject: str | None = None
    topic: str | None = None
    language_code: str = "en-IN"


class PersonalizedWorksheetRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=80)
    grade_level: int = Field(default=1, ge=1, le=12)
    language_code: str = Field(default="hi-IN", min_length=2, max_length=16)
    topic: str | None = Field(default=None, max_length=120)


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    language_code: str = Field(default="hi-IN", min_length=2, max_length=16)
    context: str | None = Field(default=None, max_length=1000)


class TextToSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language_code: str = "sat-IN"


class LanguageRead(BaseModel):
    code: str
    name: str
    native_name: str
    sarvam_supported: bool

    model_config = {"from_attributes": True}


class ConceptRead(BaseModel):
    id: int
    subject: str
    grade_level: int
    name: str
    key_idea: str
    teacher_note: str | None

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    id: int
    concept_id: int
    language_code: str
    question_text: str
    correct_answer: str
    easy_explanation: str | None
    common_mistake: str | None
    reteach_method: str | None
    difficulty: str

    model_config = {"from_attributes": True}


class ProgressRead(BaseModel):
    total_attempts: int
    correct: int
    wrong: int
    accuracy: float
    possible_misconceptions: list[dict]
