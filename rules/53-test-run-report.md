---
id: "53-test-run-report"
title: "Report every verification run with one fixed, evidence-bearing shape"
scope: quality
authority: mandatory
priority: 80
trigger: always
applies_to: []
gate: "done_report"
---

# Fixed run report

Use this structure after every test-suite run, browser pass, verification sweep, scenario batch, or
dogfooding run. Sections 1 through 3 are mandatory and ordered. Section 4 appears only when the reader
asked to converge on open questions.

```markdown
# Run report — <YYYY-MM-DD> · <scope, one sentence>

1. Result: <one-sentence verdict> — unit N passed / browser M passed / skipped K;
   awaiting decision: J (M3, M6), or awaiting decision: none.
2. Ran: <suite -> file -> count lines, or one compact table; name the environment>.
3. Items:
   **DEFECT**
   M1 ... (FIXED, file/test)
   **TRAP**
   M2 ...
   M3 ... ← DECISION
   **OBSERVATION** — none
   **OPEN**
   M4 ...
   **SIDE-EFFECT**
   M5 ...
4. Open questions: Q1..Qn
```

The five groups mean:

| Label | Content |
|---|---|
| `DEFECT` | A defect found, whether fixed or left, and the protecting file/test |
| `TRAP` | Behavior a future run must know before repeating this one |
| `OBSERVATION` | Deliberately untouched evidence and where it was recorded |
| `OPEN` | An uncovered case and its reason |
| `SIDE-EFFECT` | Repository/configuration/fixture changes made to enable the run |

Nine constraints are invariant:

1. Sections 1–3 always appear in order; an empty value is `— none`, never omitted or renamed.
2. `M1..Mn` numbering is continuous across all five groups and never restarts.
3. All five group labels appear in the stated order, including empty groups; no sixth group exists.
4. A reader decision ends with `← DECISION`; section 1 lists its count and numbers.
5. Section 1 contains observed pass/skip counts; completion wording without counts is invalid.
6. Within a group, order by severity and put decision-bearing entries first.
7. Keep an entry to one line, two at most; link detailed output rather than inlining it.
8. A fixture or data change made for the run is a side effect, not a new report section.
9. Prose follows the report language; structural labels use the complete emitted locale mapping.

Canonical English and Turkish mappings are complete and one-to-one:

| Canonical | `tr` |
|---|---|
| `Run report` | `Koşum raporu` |
| `Result` | `Sonuç` |
| `Ran` | `Koşulan` |
| `Items` | `Maddeler` |
| `DEFECT` | `KUSUR` |
| `TRAP` | `TUZAK` |
| `OBSERVATION` | `GÖZLEM` |
| `OPEN` | `AÇIK` |
| `SIDE-EFFECT` | `YAN-ETKİ` |
| `Open questions` | `Açık sorular` |
| `← DECISION` | `← KARAR` |
| `— none` | `— yok` |
| `local · verification` | `yerel · doğrulama` |
| `unit` | `birim` |
| `browser` | `tarayıcı` |
| `passed` | `başarılı` |
| `skipped` | `atlanan` |
| `awaiting decision` | `karar bekleyen` |
| decision summary `none` | `yok` |

Use the configured primary locale when a complete mapping exists; otherwise use canonical English.
Never invent a partial translation. `done_report` is advisory, but it must preserve this shape and
surface unsupported evidence claims as numbered open/defect entries rather than silently downgrading
them.
