global_fullrun.py
==================

Purpose
-------

``global_fullrun.py`` is the entry point for regional and global ELM/CLM simulations. Unlike ``site_fullrun.py`` (which targets single-point or multiple single-point configurations), this script orchestrates full three-phase BGC simulations at model resolutions (e.g., half-degree, 1-degree grids) for regional domains or the entire globe.

Key differences from ``site_fullrun.py``:

- Works with gridded domain/surface files at native CIME resolutions
- Uses ``--res`` to specify resolution instead of extracting point subsets
- Can accept pre-defined regions (via ``--region``) or custom lat/lon bounds
- Can run unstructured grids via ``--point_list`` with user-specified point areas
- Does **not** call ``makepointdata.py`` unless using point-list mode
- More suited to HPC batch systems with high processor counts (default 256 cores)

Three-Phase BGC Workflow
-------------------------

``global_fullrun.py`` implements the standard ELM BGC spinup-to-transient sequence:

1. **AD Spinup** (``--noad`` to skip)

   - Accelerated decomposition spinup with CN-only (no phosphorus)
   - Default 250 years (``--nyears_ad_spinup``)
   - Uses 1901-1920 meteorology cycle (for standard forcing datasets)
   - Compset: ``I1850CNRDCTC`` (or variant, see Compset Selection below)

2. **Final Spinup** (``--nofn`` to skip)

   - Full CNP equilibration at 1850 pre-industrial conditions
   - Default 200 years (``--nyears_final_spinup``)
   - Uses restart from end of AD spinup (or coldstart if ``--noad``)
   - Same met cycle as AD spinup
   - Compset: ``I1850CNPRDCTCBC`` (or variant)

3. **Transient** (``--notrans`` to skip)

   - Historical simulation from 1850 to present
   - Uses restart from end of final spinup
   - Transient CO2, land use, nitrogen deposition
   - Length determined by forcing dataset end year (e.g., 2010 for GSWP3)
   - Compset: ``I20TRCNPRDCTCBC`` (or variant)

Resolution Options
------------------

Specify via ``--res``. Common values:

- ``hcru_hcru`` — half-degree (~0.5 × 0.5 degrees) (default)
- ``CLM_USRDAT`` — user-provided domain and surface data (requires ``--domainfile`` and ``--surffile``)
- Other CIME-supported grids (e.g., ``f09_f09``, ``f19_f19``)

When using ``CLM_USRDAT``, you must supply:

- ``--domainfile <path>`` — SCRIP-format domain file
- ``--surffile <path>`` — ELM surface dataset

Region Specification
--------------------

**Option 1: Pre-defined regions** (via ``--region``)

``global_fullrun.py`` includes 20+ named regions with hard-coded bounds. Examples:

- ``noam`` — North America
- ``conus`` — Continental United States
- ``bona`` — Boreal North America
- ``euro`` — Europe
- ``asia`` — Asia
- ``global`` — entire globe (default if no region specified)

See ``get_regional_bounds()`` function (lines 566-610) for full list.

**Option 2: Custom bounds** (via ``--lat_bounds`` and ``--lon_bounds``)

Supply comma-separated min,max pairs:

.. code-block:: bash

   --lat_bounds 30,50 --lon_bounds -130,-100

Defaults to global (``-90,90`` × ``-180,180``) if not specified.

**Option 3: Unstructured point list** (via ``--point_list``)

Provide a file containing a list of lat/lon points. Optionally specify point area via:

- ``--point_area_kmxkm <N>`` — area in km × km
- ``--point_area_degxdeg <N>`` — area in degrees × degrees

Unstructured mode disables automatic bounds setting.

Command-Line Arguments
----------------------

See full list via ``python global_fullrun.py --help``. Key arguments:

Required
^^^^^^^^

- ``--model_root <dir>`` — E3SM/CESM source tree
- ``--ccsm_input <dir>`` — inputdata directory (or use machine defaults)
- ``--machine <name>`` — target machine (``docker``, ``cades``, ``compy``, ``anvil``, etc.)

Case Control
^^^^^^^^^^^^

- ``--caseidprefix <str>`` — prepend this to auto-generated case names
- ``--caseroot <dir>`` — where to create cases (default: ``<model_root>/cime/scripts``)
- ``--runroot <dir>`` — where run directories are created (default: machine-specific)
- ``--project <name>`` — HPC allocation/project (or read from ``~/.cesm_proj``)

Spinup/Transient Control
^^^^^^^^^^^^^^^^^^^^^^^^^

- ``--noad`` — skip AD spinup
- ``--nofn`` — skip final spinup
- ``--notrans`` — skip transient (spinup only)
- ``--nyears_ad_spinup <N>`` — years for AD spinup (default 250)
- ``--nyears_final_spinup <N>`` — years for final spinup (default 200)
- ``--nyears_transient <N>`` — override transient length (default: dataset-dependent)
- ``--runblock <N>`` — years per job submission (default 9999, i.e., single submit)

Resolution & Region
^^^^^^^^^^^^^^^^^^^

- ``--res <name>`` — grid resolution (default ``hcru_hcru``)
- ``--region <name>`` — pre-defined region (e.g., ``conus``, ``bona``)
- ``--lat_bounds <min>,<max>`` — latitude range (default ``-90,90``)
- ``--lon_bounds <min>,<max>`` — longitude range (default ``-180,180``)
- ``--mask <file>`` — custom mask file (regional only)
- ``--point_list <file>`` — unstructured point list
- ``--domainfile <file>`` — user domain file (required if ``--res CLM_USRDAT``)
- ``--surffile <file>`` — user surface file (required if ``--res CLM_USRDAT``)
- ``--landusefile <file>`` — dynamic PFT/land-use file

Meteorology Forcing
^^^^^^^^^^^^^^^^^^^

**Mutually exclusive.** Choose one:

- ``--cruncep`` — CRU-NCEP (1901-2013)
- ``--cruncepv8`` — CRU-NCEP v8 (1901-2016)
- ``--gswp3`` — GSWP3 (1901-2010)
- ``--princeton`` — Princeton (1901-2012)
- ``--crujra`` — CRU-JRA (1901-2017)
- ``--cplhist`` — coupler history forcing
- ``--site_forcing <name>`` — use forcing from a named site for all gridcells

Optional corrections:

- ``--livneh`` — Livneh precipitation correction (CONUS only, with CRU-NCEP)
- ``--daymet`` — Daymet v3 precipitation correction (CONUS only, with GSWP3)
- ``--daymet4`` — Daymet v4 downscaled GSWP3-v2 (requires user domain/surface)

Other:

- ``--cpl_bypass`` — bypass coupler (uses ``ICB`` compsets instead of ``I``)
- ``--metdir <subdir>`` — subdirectory within forcing dataset path

Model Physics
^^^^^^^^^^^^^

- ``--BGC`` — use BGC compset (legacy flag; default is CN)
- ``--SP`` — satellite phenology (skips spinup, runs as prescribed vegetation)
- ``--C13`` — enable C13 tracer
- ``--C14`` — enable C14 (without decay, as C13)
- ``--centbgc`` — use CENTURY decomposition model
- ``--vertsoilc`` — vertical soil carbon
- ``--CH4`` — enable methane model
- ``--cn_only`` — carbon and nitrogen only (saturated phosphorus)
- ``--eca`` — use ECA competition
- ``--nofire`` — disable fire
- ``--harvmod`` — apply all harvest at first timestep
- ``--no_dynroot`` — disable dynamic root distribution
- ``--nopftdyn`` — disable dynamic PFT/land use
- ``--pft <N>`` — force all gridcells to a single PFT index

Topography
^^^^^^^^^^

- ``--topounits`` — enable topographic units (> 1)
- ``--topounits_atmdownscale`` — use atmospheric downscaling with topounits

Snow/Albedo
^^^^^^^^^^^

- ``--dust_snow_mixing`` — Hao et al. dust/snow albedo parameterization
- ``--no_snicar_ad`` — disable SNICAR-AD snow microphysics
- ``--use_extra_snow_layers`` — enable extra snow layers

Build & Execution
^^^^^^^^^^^^^^^^^

- ``--compiler <name>`` — compiler (``gnu``, ``intel``, ``pgi``; machine-specific default)
- ``--mpilib <name>`` — MPI library (``openmpi``, ``mpich``, ``impi``, etc.)
- ``--np <N>`` — number of MPI tasks (default 256)
- ``--tstep <hours>`` — model timestep in hours (default 0.5)
- ``--clean_build`` — perform clean build
- ``--exeroot <dir>`` — use existing executable (skips build)
- ``--srcmods_loc <dir>`` — copy source modifications from this location
- ``--walltime <hours>`` — walltime per job (default 24)
- ``--debugq`` — use debug queue
- ``--no_submit`` — do not submit jobs (create scripts only)

Parameters & Ensembles
^^^^^^^^^^^^^^^^^^^^^^

- ``--parm_file <file>`` — custom CN parameter file
- ``--parm_file_P <file>`` — custom P parameter file
- ``--mod_parm_file <file>`` — modified parameter file
- ``--mod_parm_file_P <file>`` — modified P parameter file
- ``--parm_vals <str>`` — user-specified parameter value overrides
- ``--parm_list <file>`` — parameter list for ensemble generation (default ``parm_list``)
- ``--mc_ensemble <N>`` — generate Monte Carlo ensemble with N samples

Output Control
^^^^^^^^^^^^^^

- ``--hist_nhtfrq_spinup <N>`` — spinup history write frequency (hours)
- ``--hist_mfilt_spinup <N>`` — spinup history samples per file
- ``--hist_nhtfrq_trans <N>`` — transient history write frequency (default 0 = monthly)
- ``--hist_mfilt_trans <N>`` — transient history samples per file (default 1)
- ``--spinup_vars`` — limit output to spinup variable set
- ``--ilambvars`` — write ILAMB diagnostic variables (transient only)
- ``--dailyvars`` — write daily output variables
- ``--dailyrunoff`` — write daily hydrology output
- ``--trans_varlist <file>`` — custom transient variable list
- ``--co2_file <file>`` — CO2 forcing file (default ``fco2_datm_rcp4.5_1765-2500_c130312.nc``)

Restart Control
^^^^^^^^^^^^^^^

- ``--finidat <file>`` — use this restart file (skips spinup, transient only)
- ``--run_startyear <year>`` — starting year for model (SP or transient-only mode)

Other
^^^^^

- ``--tempdir <dir>`` — per-invocation staging directory (default ``./temp/run_<pid>_<ms>``)
- ``--archiveroot <dir>`` — archive root (machine-specific; for mesabi)
- ``--nopointdata`` — do not generate point data
- ``--makepointdata_only`` — only generate point data (no build/run)

Compset Selection
-----------------

The script auto-constructs compsets based on flags:

**Nutrient model:**

- CN (default)
- CNP (default unless ``--cn_only``)

**Decomposition model:**

- CTC (default, CLM-CASA Truncated)
- CNT (if ``--centbgc``, CENTURY)

**Competition:**

- RD (default, Relative Dominance)
- ECA (if ``--eca``, Explicit Competition Algorithm)

**Coupler mode:**

- ``I`` (default, fully coupled)
- ``ICB`` (if ``--cpl_bypass``, coupler bypass)

**Temporal mode:**

- AD spinup: ``I1850CNRDCTC`` (CN-only, no P)
- Final spinup: ``I1850CNPRDCTCBC``
- Transient: ``I20TRCNPRDCTCBC``

Example: ``--centbgc --eca --cpl_bypass`` produces ``ICB1850CNPECACNTBC`` for final spinup.

Example Invocations
-------------------

**1. Global GSWP3 run at half-degree:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix global_test \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine docker \
       --res hcru_hcru \
       --gswp3 \
       --np 256

**2. Regional run over CONUS with CRU-NCEP forcing:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix conus_cruncep \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine cades \
       --res hcru_hcru \
       --region conus \
       --cruncep \
       --compiler gnu \
       --np 128 \
       --walltime 48

**3. Custom lat/lon bounds (Columbia River watershed):**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix columbia \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine compy \
       --res hcru_hcru \
       --lat_bounds 40,55 \
       --lon_bounds -126,-108 \
       --gswp3 \
       --np 64

**4. User-provided domain/surface with Daymet4 forcing:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix custom_domain \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine anvil \
       --res CLM_USRDAT \
       --domainfile /path/to/domain.nc \
       --surffile /path/to/surfdata.nc \
       --gswp3 \
       --daymet4 \
       --np 256

**5. Spinup only (no transient), with source modifications:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix spinup_only \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine docker \
       --res hcru_hcru \
       --region noam \
       --gswp3 \
       --notrans \
       --srcmods_loc /path/to/srcmods \
       --nyears_ad_spinup 100 \
       --nyears_final_spinup 100

**6. Transient-only run from existing restart:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix transient_restart \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine cades \
       --res hcru_hcru \
       --region conus \
       --gswp3 \
       --noad --nofn \
       --finidat /path/to/restart.nc \
       --run_startyear 1850 \
       --nyears_transient 161

**7. Unstructured point-list run:**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix unstructured \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine docker \
       --res CLM_USRDAT \
       --point_list /path/to/points.txt \
       --point_area_kmxkm 25 \
       --domainfile /path/to/domain.nc \
       --surffile /path/to/surfdata.nc \
       --gswp3

**8. Monte Carlo ensemble (generate parameter samples):**

.. code-block:: bash

   python global_fullrun.py \
       --caseidprefix mc_test \
       --model_root /path/to/E3SM \
       --ccsm_input /path/to/inputdata \
       --machine cades \
       --res hcru_hcru \
       --region bona \
       --gswp3 \
       --parm_list /path/to/parm_list \
       --mc_ensemble 100

   # Creates mcsamples_mc_test_100.txt with 100 parameter sets

How It Works
------------

1. **Argument parsing and defaults** (lines 12-518)

   - Resolves machine-specific defaults (compiler, MPI library, paths)
   - Validates mutually exclusive options (e.g., only one forcing dataset)
   - Creates per-invocation ``tempdir`` for staging

2. **Forcing dataset configuration** (lines 825-863)

   - Sets ``startyear``, ``endyear`` (met cycle bounds, e.g., 1901-1920)
   - Sets ``site_endyear`` (last year of available forcing for transient)
   - Adjusts for correction datasets (Livneh, Daymet)

3. **Spinup length validation** (lines 865-872)

   - Ensures AD and final spinup lengths are multiples of met cycle length
   - Auto-adjusts if not (rounds up to next multiple)

4. **Region bounds resolution** (lines 890-907)

   - Calls ``get_regional_bounds()`` if ``--region`` specified
   - Otherwise uses ``--lat_bounds`` / ``--lon_bounds``
   - Detects if regional (any bound not at global extent)

5. **Base command construction** (lines 909-1038)

   - Builds a long ``basecmd`` string that will be passed to ``runcase.py``
   - Forwards all relevant flags and paths
   - Includes ``--tempdir`` so child processes share staging

6. **Compset construction** (lines 1045-1073)

   - Assembles compset strings based on physics flags
   - Constructs three variants: ``mymodel_adsp``, ``mymodel_fnsp``, ``mymodel_trns``

7. **Per-phase command construction** (lines 1078-1281)

   - ``cmd_adsp`` — AD spinup (CN-only, accelerated decomposition)
   - ``cmd_fnsp`` — final spinup (CNP, 1850 conditions)
   - ``cmd_trns`` — transient (1850 to present)
   - ``cmd_trns2`` — optional second transient phase (CRU-NCEP without cpl_bypass only)

8. **Case creation** (lines 1287-1310)

   - Shells out to ``runcase.py`` for each phase
   - Builds executable once during AD spinup (or final spinup if ``--noad``)
   - Subsequent phases reuse executable via ``--no_build --exeroot``

9. **Job script generation** (lines 1313-1514)

   - For each case, generates PBS/SLURM submission scripts
   - Handles multi-year runs via ``--runblock`` (splits into sequential jobs)
   - Auto-updates ``RUN_STARTDATE`` and ``finidat`` for continuation runs
   - Submits jobs in dependency chain (each phase waits for previous)

10. **Execution** (optional, lines 1506-1514)

    - If ``--no_submit`` not set, submits jobs to queue
    - Returns job IDs for dependency chaining

Notes
-----

- **Point data generation is usually skipped** in global mode. The script does not call ``makepointdata.py`` unless running unstructured point-list mode or explicitly requested.
- **ILAMB diagnostics**: ``--ilambvars`` writes the 90+ variables listed in ``ilamb_outputs`` (lines 614-690) for benchmarking.
- **CRU-NCEP phase 2**: For CRU-NCEP forcing without coupler bypass, a second transient phase (1921 to ``site_endyear``) is auto-generated to cover the full record.
- **Restart file adjustment** (commented out, lines 1495-1503): Previous versions included a post-AD-spinup restart adjustment step; this is now optional/deprecated.
- **Ensemble generation**: ``--mc_ensemble`` generates a Latin Hypercube or Monte Carlo sample file (``mcsamples_<caseid>_<N>.txt``) but does not run the ensemble — use ``manage_ensemble.py`` for that.

See Also
--------

- ``site_fullrun.py`` — single-site and multi-site point simulations
- ``runcase.py`` — low-level case creation and submission (called by this script)
- ``manage_ensemble.py`` — ensemble execution with MPI
- ``README.md`` — high-level OLMT overview
