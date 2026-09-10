import json
import httpx

from backend.config import get_settings


def _ollama_json(prompt: str) -> dict | None:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        return json.loads(payload["response"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _fallback_analysis(question: str, correct_answer: str, student_answer: str) -> dict:
    return {
        "misconception": "The answer does not match the expected concept yet.",
        "explanation": f"The correct answer is {correct_answer}. Review this question carefully: {question}",
        "reteach_method": (
            "Ask the student to explain their thinking, show one concrete example, "
            "then try a similar question again."
        ),
    }


def _fallback_practice_question(question: str, concept: str) -> dict:
    return {
        "question": f"Try one more question about {concept}: {question}",
        "answer": "Use the same concept rule from the previous explanation.",
    }


def analyze_mistake(question, correct_answer, student_answer):
    result = _ollama_json(_analysis_prompt(question, correct_answer, student_answer))
    if not result:
        return _fallback_analysis(question, correct_answer, student_answer)
    return result


def _analysis_prompt(question, correct_answer, student_answer) -> str:
    return f"""
You are an educational AI assistant for VISTA - Vernacular Intelligence for Smart Teaching & Adaptation.

Analyze the student's mistake.

Question:
{question}

Correct answer:
{correct_answer}

Student's answer:
{student_answer}

Return ONLY valid JSON in this exact format:

{{
    "misconception": "What the student misunderstood",
    "explanation": "A simple explanation of the correct concept",
    "reteach_method": "A simple activity or teaching method to help the student"
}}

Keep the language simple and suitable for a school student.
"""

def generate_practice_question(question, concept):
    prompt = f"""
You are an educational AI assistant for VISTA.
Create one simple practice question about {concept}, similar to:
{question}
Return only JSON with keys "question" and "answer".
"""
    result = _ollama_json(prompt)
    if not result:
        return _fallback_practice_question(question, concept)
    return result


def _fallback_worksheet(concept: str, language: str) -> dict:
    return {
        "language": language,
        "worksheet": {
            "title": f"{concept} practice",
            "instructions": "Read the example, complete the activity, and explain your answer.",
            "items": [
                {
                    "prompt": f"Complete one simple activity about {concept}.",
                    "answer": "Teacher review required.",
                }
            ],
        },
        "flashcards": [
            {
                "front": concept,
                "back": "Use the teacher-approved explanation for this concept.",
            }
        ],
    }


def generate_worksheet(concept: str, language: str) -> dict:
    prompt = f"""
You are an educational content author for VISTA.

Create a bilingual worksheet and flashcard set for the concept below.
The learner language is {language}; include both English and the learner language
for every visible text field. Keep it suitable for primary-school FLN learning.

Concept:
{concept}

Return ONLY valid JSON in this exact shape:
{{
  "language": "{language}",
  "worksheet": {{
    "title": {{"en": "short title", "target": "translated title"}},
    "instructions": {{"en": "short instruction", "target": "translated instruction"}},
    "items": [
      {{
        "prompt": {{"en": "question or activity", "target": "translated question or activity"}},
        "answer": {{"en": "answer", "target": "translated answer"}}
      }}
    ]
  }},
  "flashcards": [
    {{
      "front": {{"en": "term or question", "target": "translated term or question"}},
      "back": {{"en": "simple explanation", "target": "translated explanation"}}
    }}
  ]
}}

Include 3 worksheet items and 4 flashcards. Do not invent facts unrelated to the concept.
"""

    return _ollama_json(prompt) or _fallback_worksheet(concept, language)


def generate_personalized_worksheet(
    student_id: str,
    grade_level: int,
    weak_areas: list[dict],
    strengths: list[dict],
    language: str = "hi-IN",
    topic: str | None = None,
) -> dict:
    """Generate a worksheet from measured learner gaps, not a generic topic."""
    focus = topic or ", ".join(item["concept"] for item in weak_areas[:3]) or "foundational learning"
    difficulty = "foundation" if not weak_areas else (
        "support" if max(item["accuracy"] for item in weak_areas) < 50 else "practice"
    )
    if not get_settings().ollama_model:
        return {
            "ai_used": False,
            "ai_status": "Ollama is disabled; using measured-gap curriculum template.",
            "title": f"{focus} Practice",
            "instructions": "Complete each activity. Ask your teacher for help when you are unsure.",
            "difficulty": difficulty,
            "weak_areas": weak_areas,
            "sections": {
                "match": [f"Match two examples from {focus}.", f"Match the key word to its meaning."],
                "fill": [f"Complete one sentence about {focus}.", f"Write the missing word for {focus}."],
                "mcq": [f"Choose the correct answer about {focus}."],
                "oral": f"Explain one example of {focus} in your own words.",
            },
            "flashcards": [[item["concept"], "Review this idea with a teacher."] for item in weak_areas[:3]],
        }

    prompt = f"""
You are VISTA's adaptive worksheet author. Create a printable worksheet for student {student_id}.
Grade: {grade_level}. Learner language: {language}. Difficulty: {difficulty}. Main focus: {focus}.
Weak areas with measured accuracy: {json.dumps(weak_areas, ensure_ascii=False)}
Strengths (reduce repetition): {json.dumps(strengths, ensure_ascii=False)}
Target only the weak areas, scaffold from easy to moderate, and avoid repeating mastered topics.
Return ONLY JSON:
{{
  "ai_used": true,
  "title": "meaningful subject/topic title, never 'FLN Worksheet'",
  "instructions": "short child-friendly instruction",
  "difficulty": "{difficulty}",
  "sections": {{
    "match": ["2-3 activities"],
    "fill": ["2-3 activities"],
    "mcq": ["2-3 activities"],
    "oral": "one speaking activity"
  }},
  "flashcards": [["term", "simple explanation"]]
}}
Use simple, accurate school-level language. Include Hindi and Santali text where appropriate.
"""
    result = _ollama_json(prompt)
    if not result:
        return {
            "ai_used": False,
            "ai_status": "Ollama is unavailable; using measured-gap curriculum template.",
            "title": f"{focus} Practice",
            "instructions": "Complete each activity and ask your teacher for help when unsure.",
            "difficulty": difficulty,
            "weak_areas": weak_areas,
            "sections": {"match": [], "fill": [], "mcq": [], "oral": f"Explain one example of {focus}."},
            "flashcards": [[item["concept"], "Review this idea with a teacher."] for item in weak_areas[:3]],
        }
    result["ai_used"] = True
    result["weak_areas"] = weak_areas
    return result


def copilot_answer(question: str, language_code: str, context: str | None = None) -> dict:
    prompt = f"""
You are VISTA Copilot, a safe primary-school educational tutor.
Answer in simple {"Hindi" if language_code == "hi-IN" else "Santali"}.
Question: {question}
Lesson context: {context or "none"}
Return only JSON: {{"answer":"...", "follow_up":"...", "language_code":"{language_code}"}}
"""
    result = _ollama_json(prompt)
    if not result:
        return {
            "answer": (
                "This question is not in the approved offline lesson content. "
                "Please ask the teacher for help."
            ),
            "ai_used": False,
            "language_code": language_code,
        }
    result["ai_used"] = True
    return result


def make_student_explanation(
    concept: str,
    teacher_text: str,
    student_language: str,
    grade: int
):
    prompt = f"""
You are an educational assistant.

Concept: {concept}
Teacher explanation: {teacher_text}
Student language: {student_language}
Grade: {grade}

Convert the teacher's explanation into a very simple
child-friendly explanation.

Rules:
- Preserve the concept.
- Do not add unsupported facts.
- Use simple language.
- Use one familiar example.
- Keep it short.
"""

def explain_doubt(question: str, subject: str | None, topic: str | None, language_code: str) -> dict:
    context = " / ".join(part for part in [subject, topic] if part)
    prompt = f"""
Answer this primary-school question in simple language: {question}
Subject/topic: {context or "general learning"}
Return only JSON with keys "answer" and "sources".
"""
    result = _ollama_json(prompt)
    if not result:
        return {
            "answer": (
                f"Let's understand this step by step. Your question is: {question}. "
                f"Topic: {context or 'general learning'}. Start with the core idea, use one simple example, "
                "then try a similar question to check understanding."
            ),
            "sources": ["VISTA curriculum database", "Teacher-approved explanation pattern"],
        }

    return result
