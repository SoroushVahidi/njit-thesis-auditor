from njit_auditor.comment_analysis import categorize_comment_text


def test_comment_classifier_known_phrases() -> None:
    assert "margin_or_overflow" in categorize_comment_text("nothing can be in the margins")
    assert "indentation" in categorize_comment_text("delete indent")
    assert "spacing_blank_lines" in categorize_comment_text("delete blank lines")
    assert "capitalization_case" in categorize_comment_text("Use sentence case here")
    assert "punctuation" in categorize_comment_text("add period")
    assert "list_of_tables_figures_toc" in categorize_comment_text("List of Tables is incorrect")
    assert "table_format" in categorize_comment_text("Table title format")


def test_unknown_comment_maps_to_unclear() -> None:
    categories = categorize_comment_text("this note has no matching keyword")
    assert categories == ["unclear_or_other"]
