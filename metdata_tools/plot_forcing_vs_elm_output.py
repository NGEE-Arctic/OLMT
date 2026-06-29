#!/usr/bin/env python3
"""Plot forcing meteorology against corresponding ELM history output fields.

This script compares input forcing variables from met forcing NetCDF files
against the corresponding ELM history variables for each land gridcell.

If expected output variables are missing, the script prints explicit OLMT
`site_fullrun.py` guidance for adding them to transient history output.

This script requires `met_forcing_year` to exist in the output file. That field
must be generated first with `calc_met_forcing_year.py`.
"""

from __future__ import annotations

import argparse
import glob
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
    """Build precipitation output signal from required RAIN + SNOW fields."""
    rain_name = candidates[0] if len(candidates) > 0 else "RAIN"
    snow_name = candidates[1] if len(candidates) > 1 else "SNOW"

    has_rain = rain_name in ds_out
    has_snow = snow_name in ds_out

    if not (has_rain and has_snow):
        missing = []
        if not has_rain:
            missing.append(rain_name)
        if not has_snow:
            missing.append(snow_name)
        raise KeyError(
            "PRECTmms mapping requires both RAIN and SNOW in output dataset; "
            f"missing: {', '.join(missing)}."
        )

    arr = ds_out[rain_name] + ds_out[snow_name]
    arr.attrs["units"] = ds_out[rain_name].attrs.get("units", "")
    arr.attrs["long_name"] = "RAIN + SNOW"
    return arr


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
    # PSRF forcing corresponds to surface pressure, but output naming can vary by config.
    # Use PBOT first when present; otherwise fall back to PSRF.
    MappingRule("PSRF", ("PBOT", "PSRF"), "Surface pressure", build_single_output),
    MappingRule("WIND", ("WIND",), "Wind speed", build_single_output),
    # PRECTmms in forcing is total precipitation rate; build output as RAIN + SNOW.
    MappingRule("PRECTmms", ("RAIN", "SNOW"), "Precipitation (RAIN+SNOW)", build_precip_output),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--forcing-dir",
        help=(
            "Required. Directory containing forcing NetCDF files. "
            "No default is applied."
        ),
    )
    parser.add_argument(
        "--output-file",
        help=(
            "Required. ELM history output NetCDF file to compare against forcing. "
            "No default is applied."
        ),
    )
    parser.add_argument(
        "--start-date",
        default="",
        help=(
            "Optional. Start date (inclusive), format YYYY-MM-DD. "
            "If omitted (empty string), the script uses the first timestamp in --output-file."
        ),
    )
    parser.add_argument(
        "--end-date",
        default="",
        help=(
            "Optional. End date (inclusive), format YYYY-MM-DD. "
            "If omitted, the script uses the last timestamp in --output-file."
        ),
    )
    parser.add_argument(
        "--fig-dir",
        default="forcing_vs_output_figures",
        help=(
            "Optional. Directory for generated PNG figures. "
            "Default is './forcing_vs_output_figures' relative to the current "
            "invocation working directory."
        ),
    )
    parser.add_argument(
        "--vars",
        default="",
        help=(
            "Optional comma-separated forcing variable subset "
            "(for example: TBOT,QBOT,PRECTmms). "
            "If omitted, the script processes all supported variables: "
            "TBOT, QBOT, FSDS, FLDS, PSRF, WIND, PRECTmms."
        ),
    )
    parser.add_argument(
        "--forcing-time-mode",
        choices=("native", "average_to_output"),
        default="native",
        help=(
            "How to represent forcing in time. 'native' plots forcing at its native "
            "timestep (after year-shift alignment). 'average_to_output' averages forcing "
            "within each output-time interval and plots at output timestamps."
        ),
    )
    return parser.parse_args()


def standardize_time_dimension_name(ds: xr.Dataset) -> xr.Dataset:
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
    ds = standardize_time_dimension_name(ds)
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


def forcing_file_path(forcing_dir: str, forcing_var: str) -> str | None:
    pattern = os.path.join(forcing_dir, f"*_{forcing_var}_*.nc")
    matches = sorted(glob.glob(pattern))

    if len(matches) > 1:
        found = ", ".join(matches)
        raise RuntimeError(
            f"Expected exactly one forcing file for '{forcing_var}' with pattern '{pattern}', "
            f"but found {len(matches)}: {found}"
        )
    if not matches:
        return None
    return matches[0]


def prepare_forcing_series(ds_force: xr.Dataset, forcing_var: str) -> xr.DataArray:
    """Return forcing variable as-is; cell selection is handled later per gridcell."""
    return ds_force[forcing_var]


def forcing_series_for_gridcell(arr: xr.DataArray, grid_index: int) -> xr.DataArray:
    """Return 1D forcing series for one gridcell without spatial averaging."""
    non_time_dims = [dim for dim in arr.dims if dim != "time"]
    if not non_time_dims:
        return arr

    stacked = arr.stack(forcing_cell=non_time_dims)
    return stacked.isel(forcing_cell=grid_index)


def count_forcing_cells(arr: xr.DataArray) -> int:
    """Count forcing gridcells implied by all non-time dimensions."""
    non_time_dims = [dim for dim in arr.dims if dim != "time"]
    if not non_time_dims:
        return 1

    n = 1
    for dim in non_time_dims:
        n *= int(arr.sizes[dim])
    return n


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
) -> tuple[np.ndarray, np.ndarray]:
    """Return unmodified 1D values with required time-coordinate x-axis."""
    if "time" not in arr.dims and len(arr.dims) == 1:
        arr = arr.rename({arr.dims[0]: "time"})

    vals = np.atleast_1d(np.asarray(arr.values).squeeze())
    vals = pd.to_numeric(pd.Series(vals), errors="coerce").to_numpy(dtype=float)

    if "time" in arr.coords:
        tvals = np.atleast_1d(np.asarray(arr["time"].values).squeeze())
        xvals = time_to_decimal_year(tvals)
    else:
        raise ValueError(
            "Time coordinate is required for plotting. "
            f"Available coords: {tuple(arr.coords)}"
        )

    if xvals.size != vals.size:
        n = min(xvals.size, vals.size)
        xvals = xvals[:n]
        vals = vals[:n]

    mask = np.isfinite(vals)
    return xvals[mask], vals[mask]


def average_series_to_target_intervals(
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Average source series into trailing intervals ending at target timestamps.

    This assumes target timestamps represent end-of-interval output writes.
    """
    if source_x.size == 0 or source_y.size == 0 or target_x.size == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    sx = np.asarray(source_x, dtype=float)
    sy = np.asarray(source_y, dtype=float)
    tx = np.asarray(target_x, dtype=float)

    finite = np.isfinite(sx) & np.isfinite(sy)
    sx = sx[finite]
    sy = sy[finite]
    if sx.size == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    order = np.argsort(sx)
    sx = sx[order]
    sy = sy[order]

    if tx.size == 1:
        return np.array([tx[0]], dtype=float), np.array([float(np.mean(sy))], dtype=float)

    # Build trailing bin edges so bin i is (edge_i, target_i], matching
    # end-stamped output convention and avoiding half-step centering lag.
    edges = np.empty(tx.size + 1, dtype=float)
    edges[1:] = tx
    edges[0] = tx[0] - (tx[1] - tx[0])

    out_y = np.full(tx.shape, np.nan, dtype=float)
    for i in range(tx.size):
        if i == 0:
            in_bin = (sx >= edges[i]) & (sx <= edges[i + 1])
        else:
            in_bin = (sx > edges[i]) & (sx <= edges[i + 1])
        if np.any(in_bin):
            out_y[i] = float(np.mean(sy[in_bin]))

    keep = np.isfinite(out_y)
    return tx[keep], out_y[keep]


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


def derive_output_interval(output_native_x: np.ndarray) -> float:
    """Estimate one output interval in decimal-year units from output timestamps."""
    if output_native_x.size < 2:
        return 0.0
    x = np.asarray(output_native_x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return 0.0
    dx = np.diff(x)
    dx = dx[np.isfinite(dx) & (dx > 0.0)]
    if dx.size == 0:
        return 0.0
    return float(np.median(dx))


def main() -> None:
    args = parse_args()
    os.makedirs(args.fig_dir, exist_ok=True)
    forcing_year_var = "met_forcing_year"

    selected_vars = None
    if args.vars.strip():
        selected_vars = {v.strip() for v in args.vars.split(",") if v.strip()}

    ds_out = xr.open_dataset(args.output_file, decode_times=False)
    ds_out = standardize_time_dimension_name(ds_out)
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
    output_interval_shift = derive_output_interval(output_native_x) * 1.5
    output_interval_shift_days = output_interval_shift * 365.25

    output_window = overlap_interval(output_native_x, output_native_x)
    output_left, output_right = (None, None)
    if output_window is not None:
        output_left, output_right = output_window

    missing_output: set[str] = set()

    for rule in MAPPING_RULES:
        if selected_vars is not None and rule.forcing_var not in selected_vars:
            continue

        fpath = forcing_file_path(args.forcing_dir, rule.forcing_var)
        if fpath is None:
            print(
                f"Skipping {rule.forcing_var}: no forcing file found matching pattern "
                f"*_{rule.forcing_var}_*.nc"
            )
            continue

        ds_force = xr.open_dataset(fpath, decode_times=False)
        ds_force = decode_time_and_slice(ds_force, start_date, end_date)

        forcing_arr = prepare_forcing_series(ds_force, rule.forcing_var)
        if "time" not in forcing_arr.dims:
            print(
                f"Skipping {rule.forcing_var}: expected forcing variable to include "
                f"'time' dim, found {forcing_arr.dims}"
            )
            continue

        try:
            output_arr = rule.output_builder(ds_out, rule.output_candidates)
            output_name = output_arr.name if output_arr.name else "+".join(rule.output_candidates)
        except KeyError:
            missing_output.update(rule.output_candidates)
            print(
                f"Skipping {rule.forcing_var}: missing output variable(s) "
                f"{','.join(rule.output_candidates)}"
            )
            continue

        forcing_units = forcing_arr.attrs.get("units", "")
        output_units = output_arr.attrs.get("units", "")

        if "lndgrid" not in output_arr.dims:
            print(
                f"Skipping {rule.forcing_var}: expected output variable {output_name} "
                f"to include lndgrid dim, found {output_arr.dims}"
            )
            continue

        ngrid = output_arr.sizes["lndgrid"]
        forcing_cells = count_forcing_cells(forcing_arr)
        if forcing_cells not in (1, ngrid):
            print(
                f"Skipping {rule.forcing_var}: forcing has {forcing_cells} cell(s) "
                f"across non-time dims {tuple(d for d in forcing_arr.dims if d != 'time')}, "
                f"but output has {ngrid} lndgrid cell(s)."
            )
            continue

        plotted = 0
        forcing_time_error = False
        for ig in range(ngrid):
            out_g = output_arr.isel(lndgrid=ig)
            force_g = forcing_series_for_gridcell(forcing_arr, 0 if forcing_cells == 1 else ig)

            output_x, output_y = series_for_plot(out_g)
            if output_y.size == 0:
                continue

            try:
                forcing_x, forcing_y = series_for_plot(force_g)
            except ValueError as exc:
                print(f"Skipping {rule.forcing_var}: {exc}")
                plotted = 0
                forcing_time_error = True
                break

            forcing_x = forcing_x + forcing_time_shift
            if forcing_y.size == 0:
                continue

            if args.forcing_time_mode == "average_to_output":
                forcing_x, forcing_y = average_series_to_target_intervals(
                    forcing_x,
                    forcing_y,
                    output_x,
                )
                if forcing_y.size == 0:
                    continue

            forcing_x = forcing_x + output_interval_shift

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

        if forcing_time_error:
            continue

        if plotted == 0:
            print(f"No valid overlapping samples to plot for {rule.forcing_var} vs {output_name}.")
        else:
            print(
                f"Plotted {plotted} gridcell(s) for {rule.forcing_var} vs {output_name} "
                f"(forcing mode: {args.forcing_time_mode}; shifted by {forcing_time_shift:+.6f} years "
                f"+ 1.5x output interval {output_interval_shift_days:+.3f} days)."
            )

    print_missing_guidance(missing_output)


if __name__ == "__main__":
    main()
