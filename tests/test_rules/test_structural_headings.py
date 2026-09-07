# """Tests for neutral structural heading helper in pdf_structural_headings.py"""


import pytest

from njit_auditor.utils.pdf_structural_headings import (
    extract_structural_context,
    is_appendix_heading,
    is_chapter_heading,
    is_structural_heading,
    normalize_chapter_number,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("CHAPTER 1 INTRODUCTION", True),
        ("CHAPTER I", True),
        ("CHAPTER 12", True),
        ("CHAPTER 1", True),
        ("CHAPTER 1.", True),
        ("CHAPTER 1A", False),
        ("CHAPTER A", False),
        ("CHAPTER PAGE", False),
        ("APPENDIX A", True),
        ("APPENDIX B", True),
        ("APPENDIX", True),
        ("APPENDIX A.", True),
        ("APPENDIX PAGE", False),
        ("EXPERIMENTAL RESULTS", False),
        ("Chapter 1 Introduction", False),
        ("chapter 1 introduction", False),
        ("Chapter 1", False),  # Not ALL CAPS
        ("CHAPTER  1", False),
        ("CHAPTER PAGE 1", False),
        ("TABLE OF CONTENTS", False),
        ("LIST OF TABLES", False),
        ("LIST OF FIGURES", False),
    ],
)
def test_is_chapter_heading(text, expected):
    assert is_chapter_heading(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("CHAPTER 1 INTRODUCTION", True),
        ("CHAPTER I", True),
        ("CHAPTER 12", True),
        ("CHAPTER 1", True),
        ("CHAPTER 1.", True),
        ("CHAPTER 1A", False),
        ("CHAPTER A", False),
        ("CHAPTER PAGE", False),
        ("APPENDIX A", True),
        ("APPENDIX B", True),
        ("APPENDIX", True),
        ("APPENDIX A.", True),
        ("APPENDIX PAGE", False),
        ("EXPERIMENTAL RESULTS", False),
        ("Chapter 1 Introduction", False),
        ("chapter 1 introduction", False),
        ("Chapter 1", False),  # Not ALL CAPS
        ("CHAPTER PAGE 1", False),
        ("TABLE OF CONTENTS", False),
        ("LIST OF TABLES", False),
        ("LIST OF FIGURES", False),
    ],
)
def test_is_appendix_heading(text, expected):
    assert is_appendix_heading(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("CHAPTER 1 INTRODUCTION", True),
        ("CHAPTER I", True),
        ("CHAPTER 12", True),
        ("CHAPTER 1", True),
        ("CHAPTER 1.", True),
        ("CHAPTER 1A", False),
        ("CHAPTER A", False),
        ("CHAPTER PAGE", False),
        ("APPENDIX A", True),
        ("APPENDIX B", True),
        ("APPENDIX", True),
        ("APPENDIX A.", True),
        ("APPENDIX PAGE", False),
        ("EXPERIMENTAL RESULTS", False),
        ("Chapter 1 Introduction", False),
        ("chapter 1 introduction", False),
        ("CHAPTER PAGE 1", False),
        ("TABLE OF CONTENTS", False),
        ("LIST OF TABLES", False),
        ("LIST OF FIGURES", False),
    ],
)
def test_is_structural_heading(text, expected):
    assert is_structural_heading(text) == expected


def test_normalize_chapter_number():
    assert normalize_chapter_number("CHAPTER 1 INTRODUCTION") == "1"
    assert normalize_chapter_number("CHAPTER I") == "I"
    assert normalize_chapter_number("CHAPTER 1") == "1"
    assert normalize_chapter_number("CHAPTER 1.") == "1"
    assert normalize_chapter_number("CHAPTER A") == "A"
    assert normalize_chapter_number("APPENDIX A") == "A"
    assert normalize_chapter_number("APPENDIX B") == "B"
    assert normalize_chapter_number("APPENDIX") == ""
    assert normalize_chapter_number("CHAPTER PAGE 1") == "PAGE"


def test_extract_structural_context():
    assert extract_structural_context("CHAPTER 1 INTRODUCTION") == ("CHAPTER", "1")
    assert extract_structural_context("CHAPTER I") == ("CHAPTER", "I")
    assert extract_structural_context("CHAPTER 1") == ("CHAPTER", "1")
    assert extract_structural_context("CHAPTER 1.") == ("CHAPTER", "1")
    assert extract_structural_context("APPENDIX A") == ("APPENDIX", "A")
    assert extract_structural_context("APPENDIX B") == ("APPENDIX", "B")
    assert extract_structural_context("EXPERIMENTAL RESULTS") == ("", "")
    assert extract_structural_context("CHAPTER PAGE 1") == ("", "")
