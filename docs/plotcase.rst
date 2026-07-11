plotcase.py
===========

Purpose
-------

``plotcase.py`` is a visualization tool for CIME case outputs from ELM/CLM simulations. It reads model history files, performs temporal averaging, and generates time series plots comparing model output with optional observational data. The script can output both graphical plots (PDF/PNG) and NetCDF files containing the processed data.

Command-line Arguments
----------------------

Case and Run Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``--csmdir <path>``
    Base CESM/E3SM directory containing case run directories (default: ``..``)

``--runnames <names>``
    Comma-delimited list of full case names. Overrides ``--cases``, ``--sites``, and ``--compset``

``--cases <prefixes>``
    Comma-delimited list of case ID prefixes to plot

``--compset <name>``
    Compset to plot (default: ``I20TRCLM45CN``)

``--titles <titles>``
    Comma-delimited list of titles for legend entries. If not specified, uses runnames

``--sites <sites>``
    Site code(s) to plot (default: ``none``)

``--model_name <name>``
    Model name in model output NetCDF files (default: ``elm``)

Variable Selection
~~~~~~~~~~~~~~~~~~

``--varfile <file>``
    File containing list of variables to plot, one per line (default: ``varfile``)

``--vars <variables>``
    Comma-delimited list of variables to plot. Overrides ``--varfile`` and sends plot to screen instead of file

``--index <n>``
    Index (site or PFT) to extract from output arrays (default: 0). Use negative value to average over all sites/PFTs

Temporal Selection and Averaging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``--ystart <year>``
    Beginning model year to plot (default: 1)

``--yend <year>``
    Final model year to plot (default: 9999)

``--ystart_obs <year>``
    Beginning year for observations (default: 0)

``--yend_obs <year>``
    Final year for observations (default: 0)

``--avpd <n>``
    Averaging period in number of output timesteps (default: 1)

``--timezone <hours>``
    Time zone offset relative to UTC (default: 0)

``--hist_mfilt <n>``
    Override hist_mfilt value from lnd_in (default: -999, read from lnd_in)

``--hist_nhtfrq <n>``
    Override hist_nhtfrq value from lnd_in (default: -999, read from lnd_in)

History File Selection
~~~~~~~~~~~~~~~~~~~~~~

``--h1``
    Use h1 history files (default: h0)

``--h2``
    Use h2 history files (default: h0)

``--h3``
    Use h3 history files (default: h0)

``--h4``
    Use h4 history files (default: h0)

Plot Types Supported
--------------------

Default Time Series
~~~~~~~~~~~~~~~~~~~

Default behavior generates time series plots of variables over the specified year range. The script automatically detects output frequency (monthly, daily, hourly, annual) from the lnd_in namelist or history file configuration.

Diurnal Cycle
~~~~~~~~~~~~~

``--diurnal``
    Plot diurnal (24-hour) cycle average

``--dstart <doy>``
    Beginning day-of-year for diurnal average (default: 1)

``--dend <doy>``
    Final day-of-year for diurnal average (default: 365)

Requires hourly output. Averages all days within the specified DOY range across all years.

Seasonal Cycle
~~~~~~~~~~~~~~

``--seasonal``
    Plot seasonal (12-month) cycle average

Averages each calendar month across all years in the specified range.

Spinup Cases
~~~~~~~~~~~~

``--spinup``
    Plot accelerated decomposition (AD) spinup and final spinup together

``--ad_Pinit``
    AD spinup case initialized with P pools (CN mode) but other cases use CNP mode

Plot Configuration
~~~~~~~~~~~~~~~~~~

``--scale_factor <value>``
    Multiply all values by this factor (default: -999, auto-detect). Auto-detection converts gC/m^2/s to g.C/m2/day and mm/s to mm/day

``--ylog``
    Use logarithmic scale for Y axis

``--nperpage <n>``
    Number of plots per page/figure (default: 1)

Observations
~~~~~~~~~~~~

``--obs``
    Plot observations alongside model output. Reads FluxNet-format CSV files from a hardcoded directory (``/home/ac.ricciuto/fluxnet``)

Supported observational variables:

- ``NEE`` (NEE_CUT_REF)
- ``GPP`` / ``FPSN`` (GPP_NT_CUT_REF)
- ``ER`` (RECO_NT_CUT_REF)
- ``EFLX_LH_TOT`` (LE_F_MDS)
- ``FSH`` (H_F_MDS)
- ``TBOT`` (TA_F_MDS)
- ``FSDS`` (SWIN_F_MDS)
- ``WIND`` (WS_F)
- ``RAIN`` (P_F)

Includes uncertainty bars when available.

Output Formats
--------------

Graphics
~~~~~~~~

``--pdf``
    Save plots to PDF files

``--png``
    Save plots to PNG files

``--noplot``
    Disable plot generation (only create NetCDF output)

If neither ``--pdf`` nor ``--png`` is specified and ``--vars`` is used, plots are displayed interactively on screen.

``--outputdir <path>``
    Location for plots directory (default: ``<csmdir>/<runname>/plots/<analysis_type>``)

NetCDF Output
~~~~~~~~~~~~~

The script always generates two NetCDF files in the output directory:

``<case>_<site>_<compset>_model.nc``
    Contains processed model output

``<case>_<site>_<compset>_obs.nc``
    Contains processed observational data (if available)

NetCDF files include:

- Time dimension and coordinate variable (days since start year, noleap calendar)
- Gridcell dimension (one per case plotted)
- Site name, latitude, longitude for each gridcell
- All requested variables with proper units and missing value handling
- Variables converted to CF-compliant units (e.g., gC/m^2/s → kg.C/m2/s)

File Structure
~~~~~~~~~~~~~~

Files are organized as::

    <outputdir>/
        <case>_<site>_<compset>_model.nc
        <case>_<site>_<compset>_obs.nc
        <variable>.pdf  (if --nperpage=1)
        figure1.pdf     (if --nperpage>1)
        figure2.pdf
        ...

Special Variable Handling
-------------------------

``RAIN``
    Automatically adds ``SNOW`` variable to compute total precipitation

Statistics
----------

When observations are available, the script computes and uses:

- RMSE (Root Mean Square Error)
- Bias (mean difference)
- Correlation coefficient

These are calculated internally but not currently written to output files.

Notes
-----

- The script expects CIME case structure: ``<csmdir>/<casename>/run/`` containing history files
- History file naming follows CIME convention: ``<casename>.<model>.h<n>.<date>.nc``
- The ``lnd_in`` namelist file must exist in the run directory to determine output configuration
- Multiple cases can be plotted together for comparison
- The ``--runnames`` option provides full control over case naming when the standard prefix+site+compset pattern doesn't apply
- Special handling for ``RAIN`` variable: automatically sums ``RAIN`` and ``SNOW`` for total precipitation
