# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

OLMT (Offline Land Model Testbed) is a collection of Python scripts that automate ELM and CLM/CTSM simulations on top of E3SM/CIME. It is **not** a Python package — every script is a standalone top-level executable invoked via `python ./script.py …`. There is no `setup.py`, no module hierarchy, and scripts import each other by name from the repo root (e.g. `import netcdf4_functions as nffun`). Run them from the repo root.

OLMT does not run the model itself; it generates and submits CIME cases. A working clone of an E3SM (or CESM/CTSM) source tree must exist separately and be passed via `--model_root`, along with an inputdata tree via `--ccsm_input`.

## Common commands

Lint (matches CI in `.github/workflows/ruff.yml`):
```
ruff check .
```
Config lives in `ruff.toml` (only `E712` is ignored).

Install runtime deps:
```
pip install -r requirements.txt
```
`mpi4py` is only needed when running `manage_ensemble.py`; the single-site path does not require MPI.

There is **no `pytest` test suite**. The integration test is the docker-based site-fullrun matrix in `.github/workflows/site-full-run.ci.yml`, which runs `site_fullrun.py` end-to-end against `NGEE-Arctic/E3SM@develop` inside `rfiorella/model-containers:e3sm-openmpi-dev-latest` for three forcing configurations (gswp3, era5, era5-daymet4). To reproduce a CI failure locally, run the same docker invocation that the workflow builds in its `Run … test for site` step.

## High-level architecture

### The three-phase BGC simulation pattern

OLMT's central abstraction is the standard ELM BGC three-case sequence (see `README.md`):

1. **ad_spinup** — accelerated decomposition spinup
2. **final spinup** — equilibrate biomass/nutrient pools
3. **transient** — 1850–present with prescribed forcing/land use/CO2

`site_fullrun.py` and `global_fullrun.py` orchestrate this sequence. Flags `--noad`, `--nofnsp`, `--notrans` skip individual phases. `--eco2_file` adds parallel aCO2/eCO2 transient cases.

### Script layering (which script calls which)

```
site_fullrun.py / global_fullrun.py    ← user entry point
   │
   ├── makepointdata.py                ← builds domain/surface/landuse NetCDF subsets
   ├── runcase.py                      ← does create_newcase + xmlchange + namelist + build + (optional) submit for ONE case
   └── case_copy.py                    ← clones an already-built case for additional sites (avoids rebuilding)
```

`site_fullrun.py` builds the **first** site by shelling out to `runcase.py` for each of the three phases. For every additional site (`--site` accepting a comma-list, or `all`), it calls `case_copy.py` to clone the first site's run directory and patch it, which is significantly faster than re-running `runcase.py`. The `firstsite` / `*_case_firstsite` variables in `site_fullrun.py` track this.

`runcase.py` is the largest script (~3300 lines) and is where CIME interaction lives: building the `create_newcase` command, writing `user_nl_*` namelists, applying `--srcmods_loc` source modifications, and (for ensemble runs) generating PBS submission scripts. Its top-level docstring (around line 87) lists the seven steps it performs.

Every shell-out goes through `runcase.runcmd()`, which logs commands to JSON (`--options_log_json`) and post-processes stderr to detect a CIME quirk where `case.submit` swallows exceptions as warnings (search for `"Exception from "`).

### Ensembles and UQ

Ensemble work uses a separate set of scripts driven by MPI:

- `manage_ensemble.py` — MPI master that distributes parameter samples (`--ens_file`) across ranks, drives per-member runs via `ensemble_run.py`, and post-processes against `--postproc_file`.
- `ensemble_run.py` / `ensemble_copy.py` — single ensemble member execution; require a pre-built parent case (single-point, MPI-serial only).
- `MCMC.py`, `model_surrogate.py`, `surrogate_NN.py`, `run_GSA.py` — surrogate modeling and sensitivity workflows. `UQTk_scripts/` holds shell drivers for UQTk-based sensitivity.

Parameter perturbation files use the `parm_list` format: one line per parameter, four whitespace-separated fields `name pft min max`. Examples in `examples/parm_list*`. Post-processing variable specs use the `postproc_vars` format documented in the header of `examples/postproc_vars_example`.

### Site metadata

`inputdata/PTCLM/<sitegroup>_sitedata.txt` is the lookup table that maps site codes (`--site`) to lat/lon/PFT/year ranges. `--sitegroup` picks the file (default `AmeriFlux`; `NGEEArctic` is used by CI). Adding a new site means appending a row here (and to the matching `_pftdata.txt` / `_soildata.txt`).

### Met forcing flags

The forcing-source flags in `site_fullrun.py` (`--cruncep`, `--cruncepv8`, `--era5`, `--gswp3`, `--gswp3_w5e5`, `--princeton`, `--crujra`, `--trendy25`) are mutually-exclusive selectors that do two things: they hard-code the spinup met cycle to 1901–1920 and they pick a per-source `endyear_trans` (the latest year of available forcing). When adding a new forcing source, both branches in `site_fullrun.py` (around line 814) need updating, and `runcase.py` needs the matching cpl_bypass / DATM logic.

### Source modifications

`srcmods_era5cb/src.elm/` ships an `lnd_import_export.F90` override needed for the ERA5 + cpl_bypass path. The CI workflow only passes `--srcmods_loc` for the ERA5 cases — this is intentional. Other src mods are expected to live outside the repo.

## Conventions worth knowing

- **Argument parsing uses `optparse`**, not `argparse`. `optparse` is deprecated in stdlib but is consistent across all scripts; do not "modernise" one script in isolation.
- **NetCDF I/O has two helpers**: `netcdf_functions.py` (legacy, scipy/Scientific fallback) and `netcdf4_functions.py` (preferred, used by newer scripts as `nffun`). Use `netcdf4_functions` for new code.
- **`run.*`, `scripts/`, `temp/`, `plots/`, `mcsamples*.txt`** are runtime outputs and gitignored — don't commit them.
- **`./temp/` is per-invocation, not shared.** `site_fullrun.py`, `global_fullrun.py`, `runcase.py`, `makepointdata.py`, and `case_copy.py` each accept `--tempdir <path>`; when omitted they default to `./temp/run_<pid>_<ms>/`. Top-level fullrun scripts compute one tempdir at startup and forward it to every child shell-out. This isolates concurrent OLMT invocations from each other (previously they shared `./temp/clm_params.nc` etc. and would corrupt each other's staging). When debugging, look one directory deeper than the legacy `./temp/`.
- **Commit message style** (from `git log`): short imperative subject, no Conventional Commits prefix. Match the existing tone.
- **CI base branch is `develop`**, not `main`. PRs target `develop`.
