# R036 Post-Recovery Validation Package QA

Fresh live-count gate passed before package generation.

## Counts
- Philip: 9
- Muyeed: 71
- Anthony: 0
- Praneeth: 0
- Patrick: 16
- Youra: 0
- Sebastian: 0

- Total: 96

## Clusters
### by_dissertation
- Philip: 9
- Muyeed: 71
- Patrick: 16

### by_section_type
- Table of Contents: 56
- List of Figures: 37
- List of Tables: 3

### by_ratio_band
- <1.2: 9
- 1.5-1.59: 26
- 1.2-1.29: 33
- 1.3-1.39: 19
- 1.4-1.49: 9

### by_structural_category
- same_level_peer_unwrapped: 40
- structural_heading_transition_previous_wrapped: 1
- same_level_peer_both_wrapped: 18
- hierarchy_level_change_unwrapped: 15
- same_level_peer_next_wrapped: 11
- hierarchy_level_change_next_wrapped: 2
- same_level_peer_previous_wrapped: 9

### by_visual_obviousness
- visually obvious tight spacing: 42
- borderline near 1.6: 26
- moderate: 28

### by_split_number_recovery
- not_affected: 24
- affected: 72

## Selected Examples
- 1. dissertation=Muyeed, page=10, section=Table of Contents, ratio=1.24, transition=same-level entries (level 2 (X.X)), represents=33
- 2. dissertation=Muyeed, page=10, section=Table of Contents, ratio=1.24, transition=level 3 (X.X.X) -> level 2 (X.X), represents=33
- 3. dissertation=Muyeed, page=12, section=Table of Contents, ratio=1.24, transition=level 3 (X.X.X) -> level 2 (X.X), represents=33
- 4. dissertation=Muyeed, page=17, section=List of Tables, ratio=1.46, transition=same-level entries (table entry), represents=16
- 5. dissertation=Muyeed, page=17, section=List of Tables, ratio=1.46, transition=same-level entries (table entry) [next entry wraps], represents=16
- 6. dissertation=Muyeed, page=20, section=List of Figures, ratio=1.51, transition=same-level entries (figure entry), represents=16
- 7. dissertation=Philip, page=13, section=Table of Contents, ratio=1.00, transition=same-level entries (appendix level 2 (A.N)), represents=4
- 8. dissertation=Philip, page=13, section=Table of Contents, ratio=1.00, transition=same-level entries (appendix level 2 (A.N)), represents=4
- 9. dissertation=Philip, page=15, section=List of Figures, ratio=1.56, transition=same-level entries (figure entry) [previous entry wraps, next entry wraps], represents=5
- 10. dissertation=Patrick, page=11, section=List of Figures, ratio=1.55, transition=same-level entries (figure entry) [next entry wraps], represents=8
- 11. dissertation=Patrick, page=12, section=List of Figures, ratio=1.42, transition=same-level entries (figure entry) [next entry wraps], represents=4
- 12. dissertation=Patrick, page=12, section=List of Figures, ratio=1.51, transition=same-level entries (figure entry) [previous entry wraps, next entry wraps], represents=2

## Manual QA Checklist

Each selected example was visually inspected against the generated highlighted PDF before commit for logical pair, hierarchy, wrap flags, page metadata, ratio, highlight placement, parser-artifact exclusion, and parent-to-first-child exemption.
