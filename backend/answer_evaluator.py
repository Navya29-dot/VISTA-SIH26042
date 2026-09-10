from difflib import SequenceMatcher
from fractions import Fraction
import re
import unicodedata


NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "half": "1/2",
    "quarter": "1/4",
    "aadha": "1/2",
    "adha": "1/2",
    "pauna": "3/4",
}


def evaluate_answer(student_answer: str, correct_answer: str) -> dict:
    student = _normalize_text(student_answer)
    correct = _normalize_text(correct_answer)

    if not student:
        return {"is_correct": False, "confidence": 0.0, "matching_reason": "No answer was provided."}

    if student == correct:
        return {"is_correct": True, "confidence": 1.0, "matching_reason": "Exact normalized match."}

    student_number = _extract_number(student)
    correct_number = _extract_number(correct)
    if student_number is not None and correct_number is not None:
        is_correct = student_number == correct_number
        return {
            "is_correct": is_correct,
            "confidence": 0.95 if is_correct else 0.2,
            "matching_reason": "Compared the mathematical value after normalization.",
        }

    similarity = SequenceMatcher(None, student, correct).ratio()
    is_close = similarity >= 0.82 and _has_key_terms(student, correct)

    return {
        "is_correct": is_close,
        "confidence": round(similarity, 2),
        "matching_reason": "Compared meaning-bearing words in the learner response.",
    }


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("½", "1/2").replace("¼", "1/4").replace("¾", "3/4")

    for word, replacement in NUMBER_WORDS.items():
        text = re.sub(rf"\b{re.escape(word)}\b", replacement, text)

    text = re.sub(r"(\d+)\s+out\s+of\s+(\d+)", r"\1/\2", text)
    text = re.sub(r"(\d+)\s+by\s+(\d+)", r"\1/\2", text)
    text = re.sub(r"[^a-z0-9%/.\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_number(text: str) -> Fraction | None:
    fraction_match = re.search(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", text)
    if fraction_match and int(fraction_match.group(2)) != 0:
        return Fraction(int(fraction_match.group(1)), int(fraction_match.group(2)))

    percent_match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", text)
    if percent_match:
        return Fraction(percent_match.group(1)) / 100

    number_match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", text)
    if number_match:
        return Fraction(number_match.group(1))

    return None


def _has_key_terms(student: str, correct: str) -> bool:
    stop_words = {"a", "an", "the", "is", "are", "of", "in", "and", "to", "it"}
    correct_terms = {word for word in correct.split() if len(word) > 2 and word not in stop_words}
    student_terms = set(student.split())
    return bool(correct_terms & student_terms)
