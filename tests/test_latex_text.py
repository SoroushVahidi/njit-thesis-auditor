from njit_auditor.latex_text import strip_latex_to_text


def test_strip_latex_to_text_preserves_words_in_macros() -> None:
    text = strip_latex_to_text(r"This is \textit{research} and \emph{analysis}.")
    lower = text.lower()
    assert "research" in lower
    assert "analysis" in lower


def test_strip_latex_to_text_handles_malformed_input() -> None:
    text = strip_latex_to_text(r"\textit{broken {latex")
    assert isinstance(text, str)
