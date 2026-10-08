# Ruff 0.16 upgrade — deferred-lint remediation plan

## Background

CI previously pinned ruff to `0.15.17`, under which the codebase was clean.
Ruff `0.16.0` shipped a large expansion of its **default** rule set — the
number of enabled rules for this repo's config went from ~58 to ~413 — so the
same `ruff.toml` now surfaces **321 findings** under `0.16.5`.

This upgrade (branch `ruff-016-upgrade`):

1. Bumped the CI pin in `.github/workflows/ruff.yml` to `0.16.5`.
2. Applied the **164 safe, auto-fixable** findings (`ruff check --fix`):
   import sorting (`I001`), redundant `range(0, …)` starts (`PIE808`),
   `.format`/f-string modernizations (`UP032`), `.keys()` membership tests
   (`SIM118`), invalid escape sequences (`W605`), and similar mechanical edits.
   These changes are behavior-preserving.
3. Added the **14 remaining non-auto-fixable rules** to the `ignore` list in
   `ruff.toml` so CI stays green while they are addressed incrementally.

This document tracks those deferred rules. **Goal: retire entries from the
`ignore` list over time.** Each phase below should be its own follow-up PR.

## Deferred findings (161 total)

| Rule | Count | Description | Auto-fix | Risk to fix |
|------|------:|-------------|----------|-------------|
| `SIM115`  | 98 | `open()` without a context manager | none | medium — manual `with` refactor, must preserve handle lifetime |
| `UP031`   | 22 | printf-style `%` string formatting | unsafe | low/medium — convert to f-strings; watch tuple/format edge cases |
| `EXE002`  |  9 | file is executable but has no shebang | none | low — add shebang or drop exec bit |
| `PLW1510` |  7 | `subprocess.run` without `check=` | none | **high — behavioral**; adding `check=True` can raise where it didn't |
| `RUF046`  |  6 | unnecessary `int()` cast | unsafe | low — verify the value is already `int` |
| `SIM102`  |  4 | collapsible nested `if` | none | low — readability only |
| `BLE001`  |  3 | blind `except Exception` | none | low/medium — may want narrower exception types |
| `B008`    |  3 | function call in argument default | none | medium — evaluated once at def time; confirm intent |
| `EXE001`  |  3 | shebang present but file not executable | none | low — add exec bit or drop shebang |
| `C419`    |  2 | unnecessary comprehension in `any()`/`all()` | unsafe | low |
| `PLC0206` |  1 | dict iterated by key without `.items()` | none | low |
| `PERF402` |  1 | manual list copy in a loop | none | low |
| `B006`    |  1 | mutable default argument | none | medium — classic footgun; confirm no shared-state reliance |
| `B018`    |  1 | useless expression | none | low — likely a dead statement or a missing assignment |

### Concentration by file

`runcase.py` (50), `site_fullrun.py` (21), `manage_ensemble.py` (15),
`global_fullrun.py` (10), `plotcase.py` (9), `makepointdata.py` (8),
`case_copy.py` (8), `ensemble_run.py` (7), `ensemble_copy.py` (6); the
remainder scattered across `surrogate_NN.py`, `model_surrogate.py`,
`compare_cases.py`, `netcdf*_functions.py`, and `metdata_tools/*`.

## Phased remediation

Each phase: remove the rule(s) from `ignore` in `ruff.toml`, apply fixes,
run `ruff check .` clean, and sanity-run an affected script path.

### Phase 1 — low-risk cosmetic (no behavior change)
Rules: `SIM102`, `C419`, `PLC0206`, `PERF402`, `B018`.
Small, mechanical, ~9 findings. `B018` should be inspected individually — a
"useless expression" is often a bug (a missing assignment or call).

### Phase 2 — string modernization
Rule: `UP031` (22). Convert `%`-formatting to f-strings. `ruff check
--fix --unsafe-fixes --select UP031` does most of the work; review each diff
because `%` on a single non-tuple value and `%`-with-dict have edge cases.

### Phase 3 — casts and defaults
Rules: `RUF046` (6), `B008` (3), `B006` (1). `RUF046` is mechanical once the
operand type is confirmed. `B006`/`B008` need a human to confirm the default
was not intentionally shared/deferred; fix by moving the default into the body
(`x=None` then `x = x or default`).

### Phase 4 — exception handling
Rule: `BLE001` (3). Replace blind `except Exception` with the specific
exception type actually expected, or add a justified `# noqa: BLE001` where a
catch-all is genuinely wanted (e.g. top-level CIME shell-out guards).

### Phase 5 — subprocess check (behavioral — do carefully)
Rule: `PLW1510` (7). Adding `check=True` makes a nonzero exit raise
`CalledProcessError`. OLMT already post-processes some `subprocess`/`os.system`
results manually (see `runcase.runcmd()` and its CIME "Exception from …"
handling). For each call, decide: add `check=True`, pass `check=False`
explicitly to document intent, or `# noqa`. **Do not blanket-add `check=True`.**

### Phase 6 — file handles (largest; do last)
Rule: `SIM115` (98). Wrap `open()` in `with` blocks. Most are simple
read/write helpers, but some hold a handle open across a longer scope (e.g.
log/output files written incrementally). Refactor file-by-file, preserving
handle lifetime; verify no handle is used after its `with` block closes. This
is the bulk of the work and warrants its own multi-commit PR.

### Phase 7 — shebang / exec bit hygiene
Rules: `EXE001` (3), `EXE002` (9). OLMT scripts are invoked as
`python ./script.py …`, so the exec bit is not required for normal use. Decide
a repo-wide convention: either (a) give every top-level script a
`#!/usr/bin/env python` shebang **and** the exec bit, or (b) drop shebangs from
non-executable helpers. Apply consistently, then remove both rules.

## Housekeeping note (out of scope for this PR)

Ruff locally scans the untracked `cime_case_dirs/` runtime output tree (it
contains CIME's own `Tools/e3sm_compile_wrap.py`). These dirs are not committed,
so CI's clean checkout is unaffected, but adding `cime_case_dirs/` to
`extend-exclude` in `ruff.toml` (and to `.gitignore` alongside `run.*`,
`scripts/`, `temp/`, `plots/`) would keep local `ruff check .` output clean.
