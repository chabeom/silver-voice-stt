import re


def cleanup_fillers(text: str) -> str:
    text = re.sub(r"\b(음|어|아|그)\s+\1\b", r"\1", text)
    text = re.sub(r"(음\s*){2,}", "음 ", text)
    return text.strip()


def normalize_date_and_spacing(text: str) -> str:
    text = re.sub(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", r"\1년 \2월 \3일", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_phone_numbers(text: str) -> str:
    digits_only = re.sub(r"(?<!\d)(01\d)(\d{3,4})(\d{4})(?!\d)", r"\1-\2-\3", text)
    return digits_only


def normalize_numbers(text: str) -> str:
    return re.sub(r"(\d)\s+(?=\d)", r"\1", text)


def normalize_korean_text(text: str) -> str:
    normalized = cleanup_fillers(text)
    normalized = normalize_numbers(normalized)
    normalized = normalize_date_and_spacing(normalized)
    normalized = normalize_phone_numbers(normalized)
    try:
        from pykospacing import Spacing  # type: ignore

        normalized = Spacing()(normalized)
    except Exception:
        normalized = normalized
    return normalized.strip()

