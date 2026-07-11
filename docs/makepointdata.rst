=============================
makepointdata.py
=============================

Purpose
-------

``makepointdata.py`` generates site- or region-specific NetCDF input files for ELM/CLM simulations by subsetting and customizing global gridded datasets. It creates three types of NetCDF files:

1. **Domain file** - defines the grid extent, land fractions, and coordinate bounds
2. **Surface data file** - contains static land surface properties (PFT distribution, soil texture, LAI, topography)
3. **Land-use timeseries file** (``surfdata.pftdyn.nc``) - transient PFT fractions, harvest, and grazing (1850–2015 or later)

These files are prerequisites for CIME case setup and are generated once per site/region/configuration before any simulation phases begin.

Command-Line Arguments
----------------------

Site/Region Selection
^^^^^^^^^^^^^^^^^^^^^

``--site <code>``
    Six-character FLUXNET or site code (e.g., ``US-SPR``). Looks up coordinates and metadata from ``inputdata/PTCLM/<sitegroup>_sitedata.txt``.

``--sitegroup <name>``
    Site metadata group (default ``AmeriFlux``). Also used: ``NGEEArctic``.

``--point_list <path>``
    Path to a text file containing a list of points (lat, lon, optional PFT per line). Used for unstructured multi-point runs.

``--lat_bounds <min>,<max>``
    Latitude range for regional subset (degrees). Requires ``--lon_bounds``.

``--lon_bounds <min>,<max>``
    Longitude range for regional subset (degrees, -180 to 180 or 0 to 360).

PFT and Vegetation
^^^^^^^^^^^^^^^^^^

``--pft <int>``
    Replace all gridcell PFT fractions with a single PFT index (0–16 for ELM, 0–14 for CLM5 natural PFTs). Overrides site-specific PFT data.

``--lai <value>``
    Set constant LAI for all months (SP mode only). Default uses time-varying LAI from global surface file.

``--crop``
    Enable crop compset (24 PFTs, including 10 crop functional types). Selects appropriate global surface file.

``--usersurfnc <path>``
    Path to a user-provided NetCDF file for extracting custom surface variables (e.g., custom PFT distributions).

``--usersurfvar <var1>,<var2>,...``
    Comma-separated list of variable names to extract from ``--usersurfnc``. Required if ``--usersurfnc`` is used. Common example: ``PCT_NAT_PFT``.

Soil and Topography
^^^^^^^^^^^^^^^^^^^

``--surfdata_grid``
    Use gridded soil data from global files instead of site-specific ``_soildata.txt`` lookup.

``--humhol``
    Enable hummock/hollow microtopography for permafrost sites (creates two columns per site).

``--marsh``
    Enable marsh hydrology and elevation adjustments.

Spatial Scaling
^^^^^^^^^^^^^^^

``--point_area_kmxkm <value>``
    Set grid cell area in square kilometers (e.g., ``1`` for 1 km²). Overrides default resolution-based area.

``--point_area_degxdeg <value>``
    Set grid cell area in square degrees (e.g., ``0.5`` for 0.5° × 0.5°).

Model and Resolution
^^^^^^^^^^^^^^^^^^^^

``--model <CLM5|ELM>``
    Target model. Affects PFT dimension size and phosphorus variable handling.

``--res <resolution>``
    Global file resolution (default ``hcru_hcru`` = 0.5° × 0.5°). Other options: ``f19_f19`` (1.9° × 2.5°), ``f09_f09`` (0.9° × 1.25°), ``ne30np4``.

Input/Output Paths
^^^^^^^^^^^^^^^^^^

``--ccsm_input <path>``
    Root directory for CESM/E3SM input data (required). Default: ``../../../../ccsm_inputdata``.

``--tempdir <path>``
    Per-invocation staging directory for intermediate NetCDF files. Default: ``./temp/run_<pid>_<ms>``.

``--metdir <subdir>``
    Subdirectory name for meteorological forcing data (used with ``--makemetdata``).

``--makemetdata``
    Generate meteorology data (not typically used; met forcing is usually pre-staged).

Land-Use Options
^^^^^^^^^^^^^^^^

``--nopftdyn``
    Do not create transient land-use file (``surfdata.pftdyn.nc``). Use for static vegetation runs.

``--mysimyr <1850|2000>``
    Simulation year for surface data (1850 or 2000). Selects appropriate global surface file and CO2 levels.

Regional Masking
^^^^^^^^^^^^^^^^

``--mask <path>``
    Path to a NetCDF mask file for regional runs. Applies custom land/ocean mask.

Point-List Options
^^^^^^^^^^^^^^^^^^

``--keep_duplicates``
    Retain duplicate points in point list (same grid cell, same PFT). Default behavior removes duplicates and writes ``point_list_output.txt`` with unique points.

Input Global Files
------------------

``makepointdata.py`` reads from three global gridded datasets located under ``--ccsm_input``:

1. **Domain file** (``share/domains/domain.lnd.*``)
    - Variables: ``xc``, ``yc``, ``xv``, ``yv`` (coordinates), ``area``, ``mask``, ``frac``
    - Defines the lat/lon grid structure and land fractions

2. **Surface data file** (``lnd/clm2/surfdata_map/surfdata_*_simyr<year>.nc``)
    - Variables include:
        - ``PCT_NAT_PFT`` - natural PFT percentages (npft × nlat × nlon)
        - ``PCT_CROP``, ``PCT_CFT`` - crop fractions (CLM5/crop mode only)
        - ``PCT_WETLAND``, ``PCT_LAKE``, ``PCT_GLACIER``, ``PCT_URBAN``
        - ``PCT_SAND``, ``PCT_CLAY`` - soil texture (10 layers)
        - ``ORGANIC`` - organic matter content
        - ``SOIL_COLOR`` - soil color class
        - ``MONTHLY_LAI``, ``MONTHLY_SAI``, ``MONTHLY_HEIGHT_TOP``, ``MONTHLY_HEIGHT_BOT``
        - ``FMAX`` - maximum soil moisture
        - ``LABILE_P``, ``APATITE_P``, ``SECONDARY_P``, ``OCCLUDED_P``, ``SOIL_ORDER`` (phosphorus cycle)

3. **Land-use timeseries file** (``lnd/clm2/surfdata_map/landuse.timeseries_*_hist_simyr1850-2015.nc``)
    - Dimensions: ``time`` (nyears_landuse, typically 166 years), ``npft``, ``nlat``, ``nlon``
    - Variables:
        - ``PCT_NAT_PFT`` - time-varying natural PFT fractions
        - ``HARVEST_VH1``, ``HARVEST_VH2`` - forest harvest (very high and high)
        - ``HARVEST_SH1``, ``HARVEST_SH2``, ``HARVEST_SH3`` - forest harvest (secondary, high, low)
        - ``GRAZING`` - grazing intensity

The script uses ``ncks`` (NetCDF Kitchen Sink) to extract spatial subsets, then patches variables with site-specific data from lookup tables or user inputs.

Output NetCDF Structure
------------------------

All output files are written to ``<tempdir>/`` (default: ``./temp/run_<pid>_<ms>/``).

1. **domain.nc**
   - Dimensions: ``ni`` (longitude), ``nj`` (latitude; becomes record dimension for single sites)
   - Variables: ``xc``, ``yc`` (cell centers), ``xv``, ``yv`` (cell vertices), ``area``, ``mask``, ``frac``
   - For single-site: ``ni=1, nj=1``, coordinates set to site lat/lon
   - For point lists: ``ni=n_grids``, ``nj=1``

2. **surfdata.nc**

   - Dimensions:

     - Single-site: ``lsmlat=1, lsmlon=1``
     - Point list: ``gridcell=n_grids`` (unstructured)

   - All variables from global surface file, subset and optionally modified:

     - PFT fractions (``PCT_NAT_PFT``, ``PCT_CROP``, ``PCT_CFT``)
     - Soil texture (``PCT_SAND``, ``PCT_CLAY``, ``ORGANIC``)
     - Vegetation phenology (``MONTHLY_LAI``, etc.)
     - Coordinates (``LONGXY``, ``LATIXY``, ``AREA``)

3. **surfdata.pftdyn.nc** (unless ``--nopftdyn`` is specified)

   - Dimensions:

     - ``time`` (nyears_landuse, typically 166)
     - ``npft`` (17 for ELM, 15 for CLM5)
     - Spatial: same as ``surfdata.nc``

   - Variables: ``PCT_NAT_PFT(time,npft,...)``, ``HARVEST_*``, ``GRAZING``
   - For sites with ``<site>_dynpftdata.txt``, uses site-specific transient PFT and harvest data
   - Otherwise uses constant 1850 values from ``surfdata.nc`` or time-varying gridded data

NetCDF Format
^^^^^^^^^^^^^

Final files are written in NetCDF-4 Classic format (``nccopy -7 -u``) for broad tool compatibility. Intermediate files may be NetCDF-3 with 64-bit offsets (``nccopy -6 -u``) to handle large point lists.

PFT and Soil Data Integration
------------------------------

Site-Specific Lookup Tables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For ``--site`` runs (without ``--surfdata_grid``), the script reads site-specific metadata from three text files in ``inputdata/PTCLM/<sitegroup>_*.txt``:

1. **<sitegroup>_sitedata.txt**
   - Format: ``site_code,name,country,lon,lat,elev,startyear,endyear,alignyear``
   - Example: ``US-SPR,Spruce and Peatland Responses Under Changing Environments,USA,-93.4534,47.5075,418,2010,2019,2011``
   - Used to look up coordinates and met forcing year ranges

2. **<sitegroup>_pftdata.txt**
   - Format: ``site_code,pct1,pft1,pct2,pft2,pct3,pft3,pct4,pft4,pct5,pft5``
   - Example: ``US-SPR,30,1,40,2,30,9,0,0,0,0`` (30% ENF Temperate, 40% ENF Boreal, 30% EB Shrub)
   - Up to 5 PFT fractions per site; must sum to 100%

3. **<sitegroup>_soildata.txt**
   - Format: ``site_code,color,pct_sand,pct_clay,pct_om``
   - Used for soil texture (all 10 layers set to same %sand/%clay)

If a site code is not found in these files, the script falls back to gridded data from the global surface file.

Dynamic Land-Use Files
^^^^^^^^^^^^^^^^^^^^^^^

For transient runs, sites may have an optional ``inputdata/PTCLM/<site>_dynpftdata.txt`` file with annual PFT transitions and harvest/grazing:

- Format: one row per year (starting at 1850), columns: ``trans_year,pct1,pft1,...,harvest_vh1,harvest_vh2,...,harvest_sh1,harvest_sh2,harvest_sh3,grazing,harvest_flag``
- If this file exists, ``surfdata.pftdyn.nc`` uses site-specific transient data
- If absent, uses constant 1850 PFT fractions for all years

User-Provided Surface Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``--usersurfnc`` and ``--usersurfvar`` allow extraction of custom PFT distributions or other surface variables from an external NetCDF file:

1. Script reads ``LATIXY`` and ``LONGXY`` from the user file
2. For each point in ``--point_list``, finds the nearest grid cell in user file
3. Extracts specified variables (e.g., ``PCT_NAT_PFT``) and patches them into the output ``surfdata.nc``
4. Ensures PFT fractions sum to original ``PCT_NATVEG`` (adjusts if necessary)

This is useful for custom vegetation maps, downscaled PFT products, or sensitivity experiments.

PFT Indexing
^^^^^^^^^^^^

ELM (17 natural PFTs, no crops):
  0. Bare ground
  1. ENF Temperate
  2. ENF Boreal
  3. DNF Boreal
  4. EBF Tropical
  5. EBF Temperate
  6. DBF Tropical
  7. DBF Temperate
  8. DBF Boreal
  9. EB Shrub
  10. DB Shrub Temperate
  11. DB Shrub Boreal
  12. C3 arctic grass
  13. C3 non-arctic grass
  14. C4 grass
  15. Crop (placeholder, not used in non-crop runs)
  16. (reserved)

CLM5 (15 natural + 10 crop PFTs when ``--crop`` is enabled):
  0–14: natural PFTs (similar to ELM)
  15–24: crop functional types (CFTs)

How site_fullrun/global_fullrun Call It
-----------------------------------------

``makepointdata.py`` is invoked early in the simulation workflow, before any CIME cases are created:

Typical Call Path
^^^^^^^^^^^^^^^^^

1. User runs ``site_fullrun.py --site <site> ...``
2. ``site_fullrun.py`` determines if custom surface data is needed (always true for site runs, unless user provides ``--surfdata_filepath``)
3. Constructs the ``makepointdata.py`` command line:

   .. code-block:: python

      cmdline = "python makepointdata.py --site " + site
      cmdline += " --sitegroup " + sitegroup
      cmdline += " --ccsm_input " + ccsm_input
      cmdline += " --res " + res
      cmdline += " --model " + ("CLM5" if "clm5" in compset else "ELM")
      cmdline += " --tempdir " + tempdir
      if crop:
          cmdline += " --crop"
      if nopftdyn or noad:
          cmdline += " --nopftdyn"
      if pft >= 0:
          cmdline += " --pft " + str(pft)
      # ... other flags

4. Executes ``makepointdata.py`` via ``os.system(cmdline)`` or ``subprocess``
5. Expects output in ``<tempdir>/domain.nc``, ``<tempdir>/surfdata.nc``, and optionally ``<tempdir>/surfdata.pftdyn.nc``
6. Passes these file paths to ``runcase.py`` via ``--domain_file``, ``--surfdata_file``, ``--pftdyn_file``

Argument Forwarding
^^^^^^^^^^^^^^^^^^^

``site_fullrun.py`` forwards many user flags directly to ``makepointdata.py``:

- ``--sitegroup`` → ``--sitegroup``
- ``--pft`` → ``--pft``
- ``--crop`` → ``--crop``
- ``--lai`` → ``--lai``
- ``--surfdata_grid`` → ``--surfdata_grid``
- ``--tempdir`` → ``--tempdir`` (ensures consistency across all scripts)

For regional or point-list runs (``global_fullrun.py``), the call is similar but uses ``--lat_bounds``/``--lon_bounds`` or ``--point_list`` instead of ``--site``.

Output File Usage
^^^^^^^^^^^^^^^^^

``runcase.py`` uses the generated files as follows:

- **domain.nc**: passed to CIME via XML variable ``ATM_DOMAIN_FILE`` and ``LND_DOMAIN_FILE``
- **surfdata.nc**: set in ``user_nl_elm`` as ``fsurdat = '<path>/surfdata.nc'``
- **surfdata.pftdyn.nc**: set in ``user_nl_elm`` as ``flanduse_timeseries = '<path>/surfdata.pftdyn.nc'`` (transient runs only)

These files must exist before ``./case.setup`` is called, as the land model reads dimension sizes during initialization.

Example Invocations
-------------------

Single AmeriFlux Site
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python makepointdata.py \
       --site US-SPR \
       --sitegroup AmeriFlux \
       --ccsm_input /path/to/inputdata \
       --model ELM \
       --res hcru_hcru \
       --tempdir ./temp/run_12345_1623456789

Overriding PFT to 100% ENF Boreal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python makepointdata.py \
       --site US-SPR \
       --pft 2 \
       --ccsm_input /path/to/inputdata \
       --tempdir ./temp

Regional Subset
^^^^^^^^^^^^^^^

.. code-block:: bash

   python makepointdata.py \
       --lat_bounds 60,70 \
       --lon_bounds -180,-150 \
       --ccsm_input /path/to/inputdata \
       --res hcru_hcru \
       --tempdir ./temp

Point List with Custom PFT File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python makepointdata.py \
       --point_list my_sites.txt \
       --usersurfnc custom_pfts.nc \
       --usersurfvar PCT_NAT_PFT \
       --ccsm_input /path/to/inputdata \
       --tempdir ./temp

(where ``my_sites.txt`` has header ``lon lat pft`` and one row per point)

Dependencies
------------

- NCO tools: ``ncks``, ``ncrcat``, ``ncecat``, ``ncwa``, ``ncpdq``, ``ncrename``, ``nccopy`` (must be in ``PATH`` or ``/usr/local/nco/bin``)
- Python packages: ``numpy``, ``netCDF4``
- Local module: ``netcdf4_functions.py`` (imported as ``nffun``)

Notes and Caveats
-----------------

- Unstructured point lists are reshaped to a 1-D ``gridcell`` dimension. The original 2-D ``lsmlat × lsmlon`` structure is collapsed via a series of ``ncwa``, ``ncpdq``, and ``ncrename`` operations.
- Duplicate removal (when ``--keep_duplicates`` is not set) checks for identical ``(xgrid_min, ygrid_min, pft)`` tuples and writes unique points to ``point_list_output.txt``.
- For ``--humhol`` or ``US-SPR`` sites, two grid cells are created (hummock and hollow columns).
- Phosphorus variables (``LABILE_P``, etc.) are created as placeholders for CLM5/crop mode if not present in the global surface file. For US-SPR, custom P initial values are hard-coded.
- The script modifies coordinates (``LONGXY``, ``LATIXY``) and area for single-site runs to center the grid cell exactly on the site lat/lon.
- NetCDF processing is serial and may be slow for large point lists (thousands of sites). Consider pre-subsetting global files if performance is critical.
