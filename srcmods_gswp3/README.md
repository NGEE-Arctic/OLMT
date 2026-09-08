# GSWP3 Source Modifications

This directory contains source modifications to fix GSWP3 forcing data download paths.

## Problem

E3SM's DATM namelist definition (`components/data_comps/datm/cime_config/namelist_definition_datm.xml`) contains outdated directory paths for GSWP3v1 forcing data:
- Expected: `Solar`, `Precip`, `TPHWL`
- Actual server: `Solar3Hrly`, `Precip3Hrly`, `TPHWL3Hrly`

This causes `check_input_data --download` to fail with 404 errors when trying to download from the E3SM inputdata server at `https://web.lcrc.anl.gov/public/e3sm/inputdata/`.

## Solution

The `namelist_definition_datm.xml` file in this directory is a copy of the E3SM version with corrected paths that include the "3Hrly" suffix.

## Usage

Add `--srcmods_loc` flag when running OLMT scripts with `--gswp3`:

```bash
python global_fullrun.py --gswp3 --srcmods_loc /path/to/OLMT/srcmods_gswp3 [other options...]
```

Or for site runs:

```bash
python site_fullrun.py --gswp3 --srcmods_loc /path/to/OLMT/srcmods_gswp3 [other options...]
```

## Files Modified

- `data_comps/datm/cime_config/namelist_definition_datm.xml` (lines 562-564)
  - Changed: `/Solar` → `/Solar3Hrly`
  - Changed: `/Precip` → `/Precip3Hrly`
  - Changed: `/TPHWL` → `/TPHWL3Hrly`
