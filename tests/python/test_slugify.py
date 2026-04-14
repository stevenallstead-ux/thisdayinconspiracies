"""Golden tests for scripts/_slug.py.

The ID scheme `${year}-${slugify(title)}` is load-bearing for share URLs.
Every pinned golden below represents a class of input that could silently
break on an implementation change. Breaking a golden means:
  (a) the golden is wrong, or
  (b) the ID scheme just broke every existing share URL.

Treat (b) with the gravity it deserves.
"""
import pytest

from scripts._slug import slugify


class TestBasic:
    def test_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_already_slug(self):
        # Idempotency: slug of a slug is itself
        assert slugify("hello-world") == "hello-world"

    def test_single_word(self):
        assert slugify("MKULTRA") == "mkultra"

    def test_numbers_preserved(self):
        assert slugify("Apollo 11") == "apollo-11"


class TestEdgeCases:
    def test_empty_string(self):
        assert slugify("") == "untitled"

    def test_only_whitespace(self):
        assert slugify("   \t\n  ") == "untitled"

    def test_only_punctuation(self):
        assert slugify("!!!???***") == "untitled"

    def test_empty_with_fallback_year(self):
        assert slugify("", fallback_year=1963) == "untitled-1963"

    def test_non_ascii_only_falls_back(self):
        # CJK input slugifies to nothing; fallback kicks in
        assert slugify("日本語") == "untitled"

    def test_type_error_on_non_str(self):
        with pytest.raises(TypeError):
            slugify(None)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            slugify(123)  # type: ignore[arg-type]


class TestPunctuationAndSpacing:
    def test_em_dash(self):
        # em-dash (U+2014) is non-ASCII; strips out and collapses
        assert slugify("Nikola Tesla — Wardenclyffe") == "nikola-tesla-wardenclyffe"

    def test_en_dash(self):
        assert slugify("1947–1980") == "1947-1980"

    def test_curly_quotes(self):
        assert slugify("Hoover\u2019s File") == "hoover-s-file"

    def test_colon(self):
        assert slugify("Apollo 1: Fire") == "apollo-1-fire"

    def test_multiple_punctuation(self):
        assert slugify("U.S.S.R. — 1957!!") == "u-s-s-r-1957"

    def test_multi_space(self):
        assert slugify("JFK    Assassination") == "jfk-assassination"

    def test_leading_trailing_whitespace(self):
        assert slugify("  Wow! Signal  ") == "wow-signal"

    def test_underscore_treated_as_separator(self):
        assert slugify("operation_paperclip") == "operation-paperclip"


class TestUnicode:
    def test_accented_latin(self):
        # Combining marks are stripped; base letters survive
        assert slugify("Rendlesham Forêt") == "rendlesham-foret"

    def test_german_umlaut(self):
        assert slugify("Zürich Files") == "zurich-files"

    def test_mixed_scripts_keeps_ascii(self):
        # Russian letters drop; "tesla" survives
        assert slugify("Tesla Тесла") == "tesla"

    def test_emoji_dropped(self):
        assert slugify("UFO 🛸 sighting") == "ufo-sighting"

    def test_leading_number(self):
        # Leading digits are fine; the ID prefixes ${year}- anyway
        assert slugify("1969 moon") == "1969-moon"
