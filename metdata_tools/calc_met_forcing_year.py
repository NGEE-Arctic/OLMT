#!/usr/bin/env python3
"""Annotate ELM output with per-timestep forcing years.

This script mirrors the CPL_BYPASS year-indexing behavior in
`lnd_import_export.F90` and writes a required field named `met_forcing_year`
into an existing ELM output NetCDF file (in place).
"""

import argparse
import re
import sys
from typing import Any, Dict, Optional, Tuple

try:
    import netCDF4 as nc
except Exception:
    nc = None


def fortran_mod(a: int, p: int) -> int:
    """Fortran MOD(a, p): a - INT(a/p) * p, where INT truncates toward zero."""
    return a - int(a / p) * p


def parse_lnd_in(lnd_in_path: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    with open(lnd_in_path, "r", encoding="utf-8") as f:
        text = f.read()

    match = re.search(r"metdata_type\s*=\s*'([^']+)'", text, flags=re.IGNORECASE)
    if match:
        result["metdata_type"] = match.group(1).strip()

    match = re.search(r"metdata_bypass\s*=\s*'([^']+)'", text, flags=re.IGNORECASE)
    if match:
        result["metdata_bypass"] = match.group(1).strip()

    return result


def read_year_attrs(nc_path: str) -> Tuple[int, int]:
    if nc is None:
        raise RuntimeError("netCDF4 is not installed, cannot read start_year/end_year.")

    ds = nc.Dataset(nc_path, "r")
    try:
        start_year = int(ds.variables["start_year"][:].squeeze())
        end_year = int(ds.variables["end_year"][:].squeeze())
    finally:
        ds.close()

    return start_year, end_year


def metsource_from_metdata_type(metdata_type: str) -> int:
    t = metdata_type.lower()
    if "qian" in t:
        return 0
    if "cru" in t:
        return 1
    if "site" in t:
        return 2
    if "princeton" in t:
        return 3
    if "gswp3" in t:
        return 4
    if "cpl" in t:
        return 5
    if "era5" in t:
        return 6
    raise ValueError(f"Unsupported metdata_type: {metdata_type}")


def infer_met_year_ranges(
    metdata_type: str,
    site_metadata_file: Optional[str] = None,
    era5_metadata_file: Optional[str] = None,
) -> Tuple[int, int, int, int]:
    """
    Infer met year control values following lnd_import_export.F90 logic.

    Returns:
      (metsource, startyear_met, endyear_met_spinup, endyear_met_trans)
    """
    t = metdata_type.lower()
    metsource = metsource_from_metdata_type(metdata_type)

    # Defaults used before source-specific overrides.
    startyear_met = 1901
    endyear_met_spinup = 1920
    endyear_met_trans = 1920

    if metsource == 0:  # qian
        startyear_met = 1948
        endyear_met_spinup = 1972
        endyear_met_trans = 2004
    elif metsource == 1:  # cru/cruncep/crujra variants
        endyear_met_trans = 2016
    elif metsource == 2:  # site
        if not site_metadata_file:
            raise ValueError(
                "site met source requires --site-metadata-file (all_hourly.nc)."
            )
        startyear_met, endyear_met_spinup = read_year_attrs(site_metadata_file)
        endyear_met_trans = endyear_met_spinup
    elif metsource == 3:  # princeton
        endyear_met_trans = 2012
    elif metsource == 4:  # gswp3
        endyear_met_trans = 2014
    elif metsource == 5:  # cpl
        startyear_met = 566
        endyear_met_spinup = 590
        endyear_met_trans = 590
    elif metsource == 6:  # era5
        startyear_met = 1950
        endyear_met_spinup = 1970
        endyear_met_trans = 2025
        # Flexible ERA5 files can provide start/end years from metadata.
        if era5_metadata_file:
            startyear_met, endyear_met_trans = read_year_attrs(era5_metadata_file)
            endyear_met_spinup = min(endyear_met_trans, 1970)

    # livneh/daymet flags override start/spinup period in the Fortran logic.
    use_livneh = "livneh" in t
    use_daymet = "daymet" in t

    if use_livneh:
        startyear_met = 1950
        endyear_met_spinup = 1969
    elif use_daymet:
        startyear_met = 1980
        endyear_met_spinup = endyear_met_trans

    return metsource, startyear_met, endyear_met_spinup, endyear_met_trans


def forcing_year_for_sim_year(
    sim_year: int,
    metsource: int,
    startyear_met: int,
    endyear_met_spinup: int,
    endyear_met_trans: int,
) -> int:
    """Map simulation year to forcing-file year using CPL_BYPASS rules.

    Important: this returns the actual year represented by the forcing files
    (for example 1901-1920), not the intermediate model-aligned year used to
    compute index offsets in the Fortran code.
    """
    nyears_spinup = endyear_met_spinup - startyear_met + 1
    if nyears_spinup <= 0:
        raise ValueError("Invalid met range: spinup cycle length is non-positive.")

    mystart = startyear_met
    while mystart > 1850:
        mystart -= nyears_spinup
    if metsource == 5:
        mystart = 1850

    offset = 1850 - mystart

    def _spin_cycle_year(expr: int) -> int:
        # This mirrors tindex year-block logic in Fortran, then converts to an
        # actual forcing-file year by wrapping back into [startyear_met, endyear_met_spinup].
        year_block = fortran_mod(expr, nyears_spinup) + offset
        forcing_idx = year_block % nyears_spinup
        return startyear_met + forcing_idx

    if sim_year < 1850:
        return _spin_cycle_year(sim_year - 1)

    if sim_year <= endyear_met_spinup:
        return _spin_cycle_year(sim_year - 1850)

    if sim_year <= endyear_met_trans:
        return sim_year

    # After transient period, wrap over the trailing spinup-length window.
    last_window_start = endyear_met_trans - nyears_spinup + 1
    return last_window_start + ((sim_year - (endyear_met_trans + 1)) % nyears_spinup)


def phase_for_year(sim_year: int, endyear_met_spinup: int, endyear_met_trans: int) -> str:
    if sim_year < 1850:
        return "pre1850_spin_cycle"
    if sim_year <= endyear_met_spinup:
        return "spin_cycle"
    if sim_year <= endyear_met_trans:
        return "transient_direct"
    return "post_transient_tail_cycle"


def _detect_time_var_name(ds: Any) -> str:
    if "time" in ds.variables:
        return "time"
    if "DTIME" in ds.variables:
        return "DTIME"
    for var_name, var in ds.variables.items():
        if len(var.dimensions) == 1 and "time" in var_name.lower():
            return var_name
    raise ValueError("Could not detect a time coordinate variable in output file.")


def _extract_simulation_years(ds: Any, time_var_name: str) -> list[int]:
    time_var = ds.variables[time_var_name]
    if not hasattr(time_var, "units"):
        raise ValueError(
            f"Time variable '{time_var_name}' is missing required 'units' attribute."
        )

    calendar = getattr(time_var, "calendar", "standard")
    raw_time = time_var[:]

    try:
        decoded = nc.num2date(raw_time, units=time_var.units, calendar=calendar)
    except Exception as exc:
        raise ValueError(
            f"Failed to decode time variable '{time_var_name}' using units='{time_var.units}' "
            f"and calendar='{calendar}'."
        ) from exc

    years: list[int] = []
    for item in decoded:
        year = getattr(item, "year", None)
        if year is None:
            raise ValueError("Decoded time values do not expose a year field.")
        years.append(int(year))

    return years


def annotate_output_file(
    output_file: str,
    metdata_type: str,
    site_metadata_file: Optional[str] = None,
    era5_metadata_file: Optional[str] = None,
    variable_name: str = "met_forcing_year",
) -> Tuple[int, int, int]:
    if nc is None:
        raise RuntimeError("netCDF4 is required to annotate output files.")

    metsource, startyear_met, endyear_met_spinup, endyear_met_trans = infer_met_year_ranges(
        metdata_type=metdata_type,
        site_metadata_file=site_metadata_file,
        era5_metadata_file=era5_metadata_file,
    )

    ds = nc.Dataset(output_file, "r+")
    try:
        time_var_name = _detect_time_var_name(ds)
        years = _extract_simulation_years(ds, time_var_name)

        if len(years) == 0:
            raise ValueError("Output file has zero timesteps; nothing to annotate.")

        forcing_years = [
            forcing_year_for_sim_year(
                sim_year=y,
                metsource=metsource,
                startyear_met=startyear_met,
                endyear_met_spinup=endyear_met_spinup,
                endyear_met_trans=endyear_met_trans,
            )
            for y in years
        ]

        min_forcing = min(forcing_years)
        max_forcing = max(forcing_years)
        if min_forcing < startyear_met or max_forcing > endyear_met_trans:
            raise ValueError(
                "Computed forcing years are outside inferred forcing range: "
                f"computed={min_forcing}..{max_forcing}, "
                f"expected={startyear_met}..{endyear_met_trans}."
            )

        time_dim = ds.variables[time_var_name].dimensions[0]
        if variable_name in ds.variables:
            out_var = ds.variables[variable_name]
            if out_var.dimensions != (time_dim,):
                raise ValueError(
                    f"Existing variable '{variable_name}' has dimensions {out_var.dimensions}; "
                    f"expected ({time_dim},)."
                )
        else:
            out_var = ds.createVariable(variable_name, "i4", (time_dim,))

        out_var[:] = forcing_years
        out_var.long_name = "forcing meteorology year for each model timestep"
        out_var.units = "year"
        out_var.source = "metdata_tools/calc_met_forcing_year.py"
        out_var.metdata_type = metdata_type
        out_var.metsource = int(metsource)
        out_var.startyear_met = int(startyear_met)
        out_var.endyear_met_spinup = int(endyear_met_spinup)
        out_var.endyear_met_trans = int(endyear_met_trans)

        ds.setncattr("met_forcing_year_variable", variable_name)
        ds.setncattr("met_forcing_year_source", "metdata_tools/calc_met_forcing_year.py")
        ds.setncattr("met_forcing_year_metdata_type", metdata_type)
    finally:
        ds.close()

    return len(forcing_years), min_forcing, max_forcing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write per-timestep forcing years into an ELM output NetCDF file "
            "using CPL_BYPASS mapping logic from lnd_import_export.F90."
        )
    )

    src_group = parser.add_mutually_exclusive_group(required=False)
    src_group.add_argument(
        "--metdata-type",
        type=str,
        help="metdata_type (for example: gswp3, era5_daymet4, site)",
    )
    src_group.add_argument(
        "--lnd-in",
        type=str,
        help="Path to lnd_in; metdata_type/metdata_bypass are read from it",
    )

    parser.add_argument(
        "--site-metadata-file",
        type=str,
        default=None,
        help="Path to all_hourly.nc containing start_year/end_year (site forcing)",
    )
    parser.add_argument(
        "--era5-metadata-file",
        type=str,
        default=None,
        help="Path to ERA5 file containing start_year/end_year (optional)",
    )

    parser.add_argument(
        "--output-file",
        type=str,
        required=True,
        help="Path to ELM output NetCDF file to annotate in place.",
    )
    parser.add_argument(
        "--variable-name",
        type=str,
        default="met_forcing_year",
        help="Name of the output variable to write (default: met_forcing_year).",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    metdata_type = args.metdata_type
    if args.lnd_in:
        parsed = parse_lnd_in(args.lnd_in)
        if metdata_type is None:
            metdata_type = parsed.get("metdata_type")

    if not metdata_type:
        print(
            "ERROR: metdata_type not provided and not found in --lnd-in.",
            file=sys.stderr,
        )
        return 2

    try:
        nsteps, forcing_min, forcing_max = annotate_output_file(
            output_file=args.output_file,
            metdata_type=metdata_type,
            site_metadata_file=args.site_metadata_file,
            era5_metadata_file=args.era5_metadata_file,
            variable_name=args.variable_name,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Annotated file: {args.output_file}")
    print(f"Variable: {args.variable_name}")
    print(f"Timesteps annotated: {nsteps}")
    print(f"Forcing year range in annotations: {forcing_min}..{forcing_max}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
