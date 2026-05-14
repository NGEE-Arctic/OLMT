#!/usr/bin/env python3
"""Plot forcing meteorology against corresponding ELM history output fields.

This script compares input forcing variables from GSWP3 forcing NetCDF files
against the corresponding ELM history variables for each land gridcell.

If expected output variables are missing, the script prints explicit OLMT
`site_fullrun.py` guidance for adding them to transient history output.

This script requires `met_forcing_year` to exist in the output file. That field
must be generated first with `calc_met_forcing_year.py`.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


@dataclass(frozen=True)
class MappingRule:
    forcing_var: str
    output_candidates: tuple[str, ...]
    description: str
    output_builder: Callable[[xr.Dataset, tuple[str, ...]], xr.DataArray]


def build_precip_output(ds_out: xr.Dataset, candidates: tuple[str, ...]) -> xr.DataArray:
    """Build precipitation output signal from RAIN + SNOW when available."""
    rain_name = candidates[0] if len(candidates) > 0 else "RAIN"
    snow_name = candidates[1] if len(candidates) > 1 else "SNOW"

    has_rain = rain_name in ds_out
    has_snow = snow_name in ds_out

    if has_rain and has_snow:
        arr = ds_out[rain_name] + ds_out[snow_name]
        arr.attrs["units"] = ds_out[rain_name].attrs.get("units", "")
        arr.attrs["long_name"] = "RAIN + SNOW"
        return arr
    if has_rain:
        return ds_out[rain_name]
    if has_snow:
        return ds_out[snow_name]

    raise KeyError("Neither RAIN nor SNOW exists in output dataset.")


def build_single_output(ds_out: xr.Dataset, candidates: tuple[str, ...]) -> xr.DataArray:
    """Return first available candidate variable in output dataset."""
    for name in candidates:
        if name in ds_out:
            return ds_out[name]
    raise KeyError(f"None of {candidates} found in output dataset.")


MAPPING_RULES: tuple[MappingRule, ...] = (
    MappingRule("TBOT", ("TBOT",), "Air temperature", build_single_output),
    MappingRule("QBOT", ("QBOT",), "Specific humidity", build_single_output),
    MappingRule("FSDS", ("FSDS",), "Downward shortwave radiation", build_single_output),
    MappingRule("FLDS", ("FLDS",), "Downward longwave radiation", build_single_output),
    MappingRule("PSRF", ("PBOT", "PSRF"), "Surface pressure", build_single_output),
    MappingRule("WIND", ("WIND",), "Wind speed", build_single_output),
    MappingRule("PRECTmms", ("RAIN", "SNOW"), "Precipitation (RAIN+SNOW)", build_precip_output),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--forcing-dir",
        default="/Users/mhoffman/Documents/PROJECTS/NGEE-Arctic/repos/field-to-model-inputdata/E3SM/atm/datm7/gswp3/kg",
        help="Directory containing GSWP3 forcing NetCDF files.",
    )
    parser.add_argument(
        "--output-file",
        default="/Users/mhoffman/Documents/PROJECTS/NGEE-Arctic/output/AK-SP-K64G_ICB1850CNPRDCTCBC/run/AK-SP-K64G_ICB1850CNPRDCTCBC.elm.h0.0001-01-01-00000.nc",
        help="ELM history output NetCDF file.",
    )
    parser.add_argument(
        "--start-date",
        default="",
        help="Start date (inclusive), format YYYY-MM-DD.",
    )
    parser.add_argument(
        "--end-date",
        default="",
        help="End date (inclusive), format YYYY-MM-DD.",
    )
    parser.add_argument(
        "--fig-dir",
        default=os.path.join(os.path.dirname(__file__), "forcing_vs_output_figures"),
        help="Directory to save generated PNG figures.",
    )
    parser.add_argument(
        "--vars",
        default="",
        help="Optional comma-separated forcing variable subset (e.g., TBOT,QBOT,PRECTmms).",
    )
    return parser.parse_args()


def standardize_time_dimension(ds: xr.Dataset) -> xr.Dataset:
    """Normalize dataset time dimension to `time` when possible."""
    if "time" in ds.dims or "time" in ds.coords:
        return ds

    if "DTIME" in ds.dims or "DTIME" in ds.coords or "DTIME" in ds.variables:
        if "DTIME" in ds.variables and "DTIME" not in ds.coords:
            ds = ds.set_coords("DTIME")
        return ds.rename({"DTIME": "time"})

    for dim in ds.dims:
        if "time" in dim.lower():
            return ds.rename({dim: "time"})

    return ds


def decode_time_and_slice(ds: xr.Dataset, start_date: str, end_date: str) -> xr.Dataset:
    """Decode times and select a date window if possible."""
    ds = standardize_time_dimension(ds)
    ds = xr.decode_cf(ds)
    if "time" not in ds.coords:
        return ds

    if not start_date or not end_date:
        return ds

    try:
        sliced = ds.sel(time=slice(start_date, end_date))
        if sliced.sizes.get("time", 0) == 0:
            return ds
        return sliced
    except Exception:
        return ds


def forcing_file_path(forcing_dir: str, forcing_var: str) -> str:
    return os.path.join(forcing_dir, f"GSWP3_{forcing_var}_1901-2014_z14.nc")


def normalize_units(unit_str: str) -> str:
    cleaned = (unit_str or "").strip()
    return cleaned.replace("^", "")


def units_compatible(forcing_units: str, output_units: str) -> bool:
    fu = normalize_units(forcing_units)
    ou = normalize_units(output_units)
    compatible_pairs = {
        ("W/m2", "W/m2"),
        ("W/m2", "W/m2"),
        ("W/m2", "W/m^2"),
        ("W/m^2", "W/m2"),
        ("Pa", "Pa"),
        ("K", "K"),
        ("kg/kg", "kg/kg"),
        ("m/s", "m/s"),
        ("mm/s", "mm/s"),
    }
    if fu == ou:
        return True
    return (fu, ou) in compatible_pairs


def prepare_forcing_series(ds_force: xr.Dataset, forcing_var: str) -> xr.DataArray:
    """Collapse forcing variable to a 1D time series by averaging spatial dimensions."""
    arr = ds_force[forcing_var]
    if "time" not in arr.dims:
        for dim in arr.dims:
            if "time" in dim.lower():
                arr = arr.rename({dim: "time"})
                break

    for dim in list(arr.dims):
        if dim != "time":
            arr = arr.mean(dim=dim)

    if "time" not in arr.dims and len(arr.dims) == 1:
        arr = arr.rename({arr.dims[0]: "time"})

    return arr


def time_to_decimal_year(time_values: np.ndarray) -> np.ndarray:
    """Convert datetime-like values (including cftime) to decimal year."""
    dec = np.empty(len(time_values), dtype=float)
    for i, t in enumerate(time_values):
        year = getattr(t, "year", None)
        if year is None:
            ts = pd.Timestamp(t)
            year = ts.year
            doy = ts.dayofyear
            hour = ts.hour
            minute = ts.minute
            second = ts.second
            microsecond = ts.microsecond
            days_in_year = 366 if ts.is_leap_year else 365
        else:
            doy = getattr(t, "dayofyr", None)
            if doy is None:
                doy = t.timetuple().tm_yday
            hour = getattr(t, "hour", 0)
            minute = getattr(t, "minute", 0)
            second = getattr(t, "second", 0)
            microsecond = getattr(t, "microsecond", 0)
            days_in_year = 366 if getattr(t, "is_leap_year", lambda: False)() else 365

        frac_day = (hour + minute / 60.0 + second / 3600.0 + microsecond / 3.6e9) / 24.0
        dec[i] = year + ((doy - 1) + frac_day) / days_in_year

    return dec


def overlap_interval(x1: np.ndarray, x2: np.ndarray) -> tuple[float, float] | None:
    """Return overlap interval [left, right] for two finite x arrays."""
    if x1.size == 0 or x2.size == 0:
        return None
    x1f = x1[np.isfinite(x1)]
    x2f = x2[np.isfinite(x2)]
    if x1f.size == 0 or x2f.size == 0:
        return None
    left = max(float(np.min(x1f)), float(np.min(x2f)))
    right = min(float(np.max(x1f)), float(np.max(x2f)))
    if left <= right:
        return (left, right)
    return None


def series_for_plot(
    arr: xr.DataArray,
    x_values: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Return unmodified 1D values with time x-axis when available.

    x_values can be supplied to override the computed x-axis for time values.
    """
    if "time" not in arr.dims and len(arr.dims) == 1:
        arr = arr.rename({arr.dims[0]: "time"})

    vals = np.atleast_1d(np.asarray(arr.values).squeeze())
    vals = pd.to_numeric(pd.Series(vals), errors="coerce").to_numpy(dtype=float)

    if x_values is not None:
        xvals = np.atleast_1d(np.asarray(x_values).squeeze())
        axis_mode = "explicit_mapped_decimal_year"
    elif "time" in arr.coords:
        tvals = np.atleast_1d(np.asarray(arr["time"].values).squeeze())
        xvals = time_to_decimal_year(tvals)
        axis_mode = "native_time_decimal_year"
    else:
        xvals = np.arange(vals.size)
        axis_mode = "native_index"

    if xvals.size != vals.size:
        n = min(xvals.size, vals.size)
        xvals = xvals[:n]
        vals = vals[:n]

    mask = np.isfinite(vals)
    return xvals[mask], vals[mask], axis_mode


def print_missing_guidance(missing_output: set[str]) -> None:
    if not missing_output:
        return

    suggested = [
        "TBOT",
        "QBOT",
        "FSDS",
        "FLDS",
        "PBOT",
        "WIND",
        "RAIN",
        "SNOW",
    ]
    needed = [v for v in suggested if v in missing_output]
    if not needed:
        return

    varlist = ",".join(needed)
    print("\nMissing output fields detected.")
    print("To include them via OLMT, add to transient history var list.")
    print("Example:")
    print(f"  --trans_varlist \"{varlist}\"")
    print("Notes:")
    print("  - In forcing, PSRF corresponds to PBOT on ELM history output.")
    print("  - If comparing PRECTmms, include both RAIN and SNOW.")
    print("  - Internally, OLMT writes hist_empty_htapes=.true. and hist_fincl1 from --trans_varlist.")


def build_output_mapped_decimal_year(ds_out: xr.Dataset, forcing_year_var: str) -> np.ndarray:
    """Build decimal-year x-axis using met_forcing_year + output intra-year fraction."""
    if forcing_year_var not in ds_out:
        raise KeyError(
            f"Required variable '{forcing_year_var}' not found in output file. "
            "Run calc_met_forcing_year.py first."
        )
    if "time" not in ds_out.coords:
        raise KeyError("Output file has no decodable time coordinate.")

    dec_time = time_to_decimal_year(np.asarray(ds_out["time"].values))
    year_frac = dec_time - np.floor(dec_time)

    forcing_year = np.asarray(ds_out[forcing_year_var].values).squeeze()
    if forcing_year.ndim != 1:
        raise ValueError(
            f"Expected '{forcing_year_var}' to be 1D over time, got shape {forcing_year.shape}."
        )
    if forcing_year.size != year_frac.size:
        raise ValueError(
            f"Length mismatch between '{forcing_year_var}' ({forcing_year.size}) and time ({year_frac.size})."
        )

    forcing_year = pd.to_numeric(pd.Series(forcing_year), errors="coerce").to_numpy(dtype=float)
    return forcing_year + year_frac


def build_output_native_decimal_year(ds_out: xr.Dataset) -> np.ndarray:
    """Build decimal-year x-axis directly from output file time coordinate."""
    if "time" not in ds_out.coords:
        raise KeyError("Output file has no decodable time coordinate.")
    return time_to_decimal_year(np.asarray(ds_out["time"].values))


def derive_forcing_time_shift(
    output_native_x: np.ndarray,
    output_mapped_x: np.ndarray,
) -> float:
    """Derive a constant shift so forcing-year axis overlays output-year axis."""
    if output_native_x.size == 0 or output_mapped_x.size == 0:
        return 0.0
    n = min(output_native_x.size, output_mapped_x.size)
    delta = output_native_x[:n] - output_mapped_x[:n]
    delta = delta[np.isfinite(delta)]
    if delta.size == 0:
        return 0.0
    return float(np.median(delta))


def main() -> None:
    args = parse_args()
    os.makedirs(args.fig_dir, exist_ok=True)
    forcing_year_var = "met_forcing_year"

    selected_vars = None
    if args.vars.strip():
        selected_vars = {v.strip() for v in args.vars.split(",") if v.strip()}

    ds_out = xr.open_dataset(args.output_file, decode_times=False)
    ds_out = standardize_time_dimension(ds_out)
    ds_out = xr.decode_cf(ds_out)

    start_date = args.start_date
    end_date = args.end_date
    if (not start_date or not end_date) and "time" in ds_out.coords and ds_out.sizes.get("time", 0) > 0:
        time_vals = ds_out["time"].values
        start_date = str(time_vals[0])[:10]
        end_date = str(time_vals[-1])[:10]
        print(f"Using output-file time bounds as defaults: {start_date} to {end_date}")

    ds_out = decode_time_and_slice(ds_out, start_date, end_date)

    if forcing_year_var not in ds_out:
        raise SystemExit(
            "Required field 'met_forcing_year' is missing from output file. "
            "Run metdata_tools/calc_met_forcing_year.py --output-file <elm_output.nc> first."
        )

    output_mapped_x = build_output_mapped_decimal_year(ds_out, forcing_year_var)
    output_native_x = build_output_native_decimal_year(ds_out)
    forcing_time_shift = derive_forcing_time_shift(output_native_x, output_mapped_x)

    output_window = overlap_interval(output_native_x, output_native_x)
    output_left, output_right = (None, None)
    if output_window is not None:
        output_left, output_right = output_window

    report_rows: list[dict[str, object]] = []
    missing_output: set[str] = set()

    for rule in MAPPING_RULES:
        if selected_vars is not None and rule.forcing_var not in selected_vars:
            continue

        fpath = forcing_file_path(args.forcing_dir, rule.forcing_var)
        if not os.path.exists(fpath):
            report_rows.append(
                {
                    "forcing_var": rule.forcing_var,
                    "output_var": "",
                    "status": "forcing_file_missing",
                    "forcing_units": "",
                    "output_units": "",
                    "units_match": False,
                    "alignment": "",
                    "note": f"Missing forcing file: {fpath}",
                }
            )
            continue

        ds_force = xr.open_dataset(fpath, decode_times=False)
        ds_force = decode_time_and_slice(ds_force, start_date, end_date)

        forcing_arr = prepare_forcing_series(ds_force, rule.forcing_var)

        try:
            output_arr = rule.output_builder(ds_out, rule.output_candidates)
            output_name = output_arr.name if output_arr.name else "+".join(rule.output_candidates)
        except KeyError:
            missing_output.update(rule.output_candidates)
            report_rows.append(
                {
                    "forcing_var": rule.forcing_var,
                    "output_var": ",".join(rule.output_candidates),
                    "status": "missing_output_variable",
                    "forcing_units": forcing_arr.attrs.get("units", ""),
                    "output_units": "",
                    "units_match": False,
                    "alignment": "",
                    "note": "No candidate output variable found.",
                }
            )
            continue

        forcing_units = forcing_arr.attrs.get("units", "")
        output_units = output_arr.attrs.get("units", "")
        match = units_compatible(forcing_units, output_units)

        if "lndgrid" not in output_arr.dims:
            report_rows.append(
                {
                    "forcing_var": rule.forcing_var,
                    "output_var": output_name,
                    "status": "invalid_output_dims",
                    "forcing_units": forcing_units,
                    "output_units": output_units,
                    "units_match": match,
                    "alignment": "",
                    "note": f"Expected lndgrid dim, found {output_arr.dims}",
                }
            )
            continue

        ngrid = output_arr.sizes["lndgrid"]
        plotted = 0
        forcing_x, forcing_y, forcing_axis_mode = series_for_plot(forcing_arr)
        forcing_x = forcing_x + forcing_time_shift
        forcing_axis_mode = f"{forcing_axis_mode}_shifted"
        if forcing_y.size == 0:
            report_rows.append(
                {
                    "forcing_var": rule.forcing_var,
                    "output_var": output_name,
                    "status": "no_valid_forcing_data",
                    "forcing_units": forcing_units,
                    "output_units": output_units,
                    "units_match": match,
                    "alignment": "",
                    "note": "No finite forcing samples after filtering.",
                }
            )
            continue

        for ig in range(ngrid):
            out_g = output_arr.isel(lndgrid=ig)
            output_x, output_y, output_axis_mode = series_for_plot(
                out_g,
                x_values=output_native_x,
            )
            if output_y.size == 0:
                continue

            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(forcing_x, forcing_y, label=f"forcing:{rule.forcing_var}", lw=1.6, color="k")
            ax.plot(output_x, output_y, label=f"output:{output_name} (grid {ig})", lw=1.2)
            if output_left is not None and output_right is not None:
                if output_right > output_left:
                    ax.set_xlim(output_left, output_right)
                else:
                    pad = 1.0 / 365.0
                    ax.set_xlim(output_left - pad, output_right + pad)

            ax.set_title(f"{rule.description} | gridcell {ig}")
            ax.set_xlabel("Time (decimal year)")
            ax.set_ylabel(f"forcing [{forcing_units}] vs output [{output_units}]")
            ax.grid(True, alpha=0.35)
            ax.legend(loc="best")
            plt.tight_layout()

            png_name = f"{rule.forcing_var}_vs_{output_name}_grid{ig:03d}.png"
            fig.savefig(os.path.join(args.fig_dir, png_name), dpi=150)
            plt.close(fig)
            plotted += 1

        status = "plotted" if plotted > 0 else "no_overlap_after_alignment"
        alignment_mode = f"forcing:{forcing_axis_mode}|output:{output_axis_mode}"
        note = (
            "No downsampling or truncation. Output is shown on native output-file "
            "time range, and forcing time is shifted using met_forcing_year-derived "
            f"offset ({forcing_time_shift:+.6f} years)."
        )

        report_rows.append(
            {
                "forcing_var": rule.forcing_var,
                "output_var": output_name,
                "status": status,
                "forcing_units": forcing_units,
                "output_units": output_units,
                "units_match": match,
                "alignment": alignment_mode,
                "note": note,
                "n_gridcells_plotted": plotted,
            }
        )

    report_path = os.path.join(args.fig_dir, "forcing_output_mapping_report.csv")
    report = pd.DataFrame(report_rows)
    report.to_csv(report_path, index=False)

    print(f"Saved report: {report_path}")
    if not report.empty:
        print(report[["forcing_var", "output_var", "status", "units_match", "alignment", "note"]].to_string(index=False))

    print_missing_guidance(missing_output)


if __name__ == "__main__":
    main()
