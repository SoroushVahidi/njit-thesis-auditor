from pathlib import Path

from njit_auditor.latex_loader import load_tex_project


def test_recursive_input_include_loading(tmp_path: Path) -> None:
    main = tmp_path / "main.tex"
    chapter = tmp_path / "chapter1.tex"
    sections = tmp_path / "sections"
    sections.mkdir()
    sub = sections / "sub.tex"

    main.write_text("\\input{chapter1}\n\\include{sections/sub}\n", encoding="utf-8")
    chapter.write_text("Chapter file.\n\\input{sections/sub}\n", encoding="utf-8")
    sub.write_text("Sub file.\n", encoding="utf-8")

    project = load_tex_project(main)
    paths = {f.path for f in project.files}
    assert main.resolve() in paths
    assert chapter.resolve() in paths
    assert sub.resolve() in paths
    assert len(paths) == 3
