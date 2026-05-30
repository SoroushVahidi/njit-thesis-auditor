import json
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path("data/processed/evaluation_data_manifest.json")
GITIGNORE_PATH = Path(".gitignore")

REQUIRED_CATEGORIES = (
    "guideline_rule_sources",
    "processed_rule_sources",
    "ef_commented_dissertations",
    "clean_no_feedback_baselines",
    "rule_matrix_files",
    "original_archive_only_materials",
    "generated_and_private_paths",
)

REQUIRED_PRIVACY_FIELDS = (
    "contains_real_student_data",
    "body_text_must_not_be_quoted",
    "raw_generated_outputs_gitignored",
)

NON_EXTRACTABLE_COMMENT_STATUSES = frozenset({"flattened", "compressed_flattened"})


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _entry_paths(entry: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("path", "archive_member_name", "parent_archive"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def _all_category_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    categories = manifest["categories"]
    entries: list[dict[str, Any]] = []
    for category in REQUIRED_CATEGORIES:
        entries.extend(categories[category])
    return entries


def _manifest_contains_substring(manifest: dict[str, Any], needle: str) -> bool:
    return any(
        needle in path
        for entry in _all_category_entries(manifest)
        for path in _entry_paths(entry)
    )


def test_manifest_is_valid_json_with_required_top_level_fields() -> None:
    manifest = _load_manifest()
    assert manifest["schema_version"] == 1
    assert isinstance(manifest["generated_for_commit"], str)
    assert manifest["generated_for_commit"]
    assert isinstance(manifest["privacy_policy"], dict)
    assert isinstance(manifest["categories"], dict)


def test_manifest_includes_required_categories() -> None:
    manifest = _load_manifest()
    categories = manifest["categories"]
    for category in REQUIRED_CATEGORIES:
        assert category in categories
        assert isinstance(categories[category], list)


def test_manifest_privacy_policy_fields() -> None:
    privacy_policy = _load_manifest()["privacy_policy"]
    for field in REQUIRED_PRIVACY_FIELDS:
        assert field in privacy_policy
        assert privacy_policy[field] is True


def test_manifest_sample_counts_match_category_fields() -> None:
    manifest = _load_manifest()
    categories = manifest["categories"]
    sample_counts = manifest["sample_counts"]

    ef_pdfs = categories["ef_commented_dissertations"]
    clean_baselines = categories["clean_no_feedback_baselines"]

    computed = {
        "guideline_rule_sources": len(categories["guideline_rule_sources"]),
        "processed_rule_sources": len(categories["processed_rule_sources"]),
        "ef_commented_dissertation_pdfs_tracked": sum(
            1
            for entry in ef_pdfs
            if entry.get("file_type") == "PDF"
            and entry.get("tracked_status") == "tracked"
        ),
        "ef_commented_dissertation_pdfs_referenced_not_standalone": sum(
            1
            for entry in ef_pdfs
            if entry.get("tracked_status") == "referenced_not_standalone_tracked"
        ),
        "extractable_comment_pdfs": sum(
            1 for entry in ef_pdfs if entry.get("comment_status") == "extractable"
        ),
        "flattened_or_nonextractable_comment_pdfs": sum(
            1
            for entry in ef_pdfs
            if entry.get("comment_status") in NON_EXTRACTABLE_COMMENT_STATUSES
            and entry.get("file_type") == "PDF"
        ),
        "clean_no_feedback_archives_tracked": sum(
            1
            for entry in clean_baselines
            if entry.get("file_type") == "ZIP"
            and entry.get("tracked_status") == "tracked"
        ),
        "clean_no_feedback_pdfs_archive_contained": sum(
            1
            for entry in clean_baselines
            if entry.get("file_type") == "PDF"
            and entry.get("tracked_status") == "archive-contained"
        ),
        "rule_matrix_files": len(categories["rule_matrix_files"]),
        "original_archive_only_materials": len(
            categories["original_archive_only_materials"]
        ),
        "generated_and_private_gitignored_paths": len(
            categories["generated_and_private_paths"]
        ),
    }

    expected_counts = {
        "guideline_rule_sources": 8,
        "processed_rule_sources": 2,
        "ef_commented_dissertation_pdfs_tracked": 4,
        "ef_commented_dissertation_pdfs_referenced_not_standalone": 1,
        "extractable_comment_pdfs": 2,
        "flattened_or_nonextractable_comment_pdfs": 2,
        "clean_no_feedback_archives_tracked": 1,
        "clean_no_feedback_pdfs_archive_contained": 1,
        "rule_matrix_files": 1,
        "original_archive_only_materials": 12,
        "generated_and_private_gitignored_paths": 2,
    }

    assert computed == expected_counts
    assert sample_counts == expected_counts


def test_manifest_contains_required_known_entries() -> None:
    manifest = _load_manifest()
    required_needles = (
        "data/processed/rules/njit_rule_inventory.json",
        "data/processed/rules/project_added_rules.json",
        "250218 Cibaku Elson First Review.pdf",
        "Yin_Haotian_Second_R_with_EF_Feedback.pdf",
        "260415 Yin H _2nd_review with EF Comments.pdf",
        "Yin_H_4th_Review_with_EF_comments_compressed.pdf",
        "260330_YESNO_audit_logic_matrix.xlsx",
        "Dissertations with no Feedback -20260529T012213Z-3-001.zip",
        "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf",
        "data/evaluation/generated/",
        "data/evaluation/private/",
    )
    for needle in required_needles:
        assert _manifest_contains_substring(manifest, needle)


def test_gitignore_excludes_generated_and_private_evaluation_paths() -> None:
    gitignore = GITIGNORE_PATH.read_text(encoding="utf-8")
    assert "data/evaluation/generated/" in gitignore
    assert "data/evaluation/private/" in gitignore


def test_sebastian_fine_clean_pdf_is_not_standalone_tracked() -> None:
    manifest = _load_manifest()
    sebastian_pdf = "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf"

    standalone_tracked_paths = [
        entry.get("path")
        for entry in _all_category_entries(manifest)
        if entry.get("tracked_status") == "tracked"
        and isinstance(entry.get("path"), str)
        and sebastian_pdf in entry["path"]
    ]
    assert standalone_tracked_paths == []

    archive_contained = [
        entry
        for entry in manifest["categories"]["clean_no_feedback_baselines"]
        if entry.get("tracked_status") == "archive-contained"
        and sebastian_pdf in str(entry.get("archive_member_name", ""))
    ]
    assert len(archive_contained) == 1


def test_only_extractable_pdfs_are_marked_for_ef_overlap() -> None:
    manifest = _load_manifest()
    ef_pdfs = manifest["categories"]["ef_commented_dissertations"]

    for entry in ef_pdfs:
        if entry.get("file_type") != "PDF":
            continue
        comment_status = entry.get("comment_status")
        used_in_ef_overlap = entry.get("used_in_ef_overlap")
        if comment_status == "extractable":
            assert used_in_ef_overlap is True
        elif comment_status in NON_EXTRACTABLE_COMMENT_STATUSES:
            assert used_in_ef_overlap is False
        else:
            assert used_in_ef_overlap is False

    overlap_entries = [
        entry
        for entry in ef_pdfs
        if entry.get("used_in_ef_overlap") is True
    ]
    assert len(overlap_entries) == 2
    assert all(entry.get("comment_status") == "extractable" for entry in overlap_entries)
