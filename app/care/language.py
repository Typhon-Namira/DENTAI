import re

_COUNTRY_LANGUAGE = (
    ("374", "hy"),
    ("7", "ru"),
    ("98", "fa"),
    ("90", "tr"),
    ("995", "ka"),
    ("994", "az"),
    ("380", "uk"),
    ("375", "ru"),
    ("373", "ro"),
    ("971", "ar"),
    ("966", "ar"),
    ("972", "he"),
    ("49", "de"),
    ("33", "fr"),
    ("39", "it"),
    ("34", "es"),
    ("44", "en"),
    ("1", "en"),
)


def language_for_phone(phone: str | None, default: str = "en") -> str:
    digits = re.sub(r"\D", "", phone or "")
    for prefix, language in _COUNTRY_LANGUAGE:
        if digits.startswith(prefix):
            return language
    return default or "en"


def language_name(code: str) -> str:
    return {
        "hy": "Armenian",
        "ru": "Russian",
        "fa": "Persian",
        "tr": "Turkish",
        "ka": "Georgian",
        "az": "Azerbaijani",
        "uk": "Ukrainian",
        "ro": "Romanian",
        "ar": "Arabic",
        "he": "Hebrew",
        "de": "German",
        "fr": "French",
        "it": "Italian",
        "es": "Spanish",
        "en": "English",
    }.get(code, "English")
