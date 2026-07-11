===========
runcase.py
===========

Overview
========

``runcase.py`` is the core CIME interaction layer for OLMT, orchestrating the complete lifecycle of a single E3SM/ELM (or CLM/CTSM) simulation. This ~3600-line script is **not** called directly by users — it is invoked by ``site_fullrun.py`` and ``global_fullrun.py`` to build and configure each phase (ad_spinup, final spinup, transient) of a BGC simulation sequence.

**Key responsibilities:**

- Generate point/regional surface, domain, and land-use data (via ``makepointdata.py``)
- Call ``create_newcase`` with specified compset, resolution, machine, and MPI configuration
- Apply XML configuration changes (``./xmlchange``) for CIME environment and run settings
- Write land model namelists (``user_nl_elm``, ``user_nl_datm``, ``user_nl_mosart``) with physics options, output variables, and forcing paths
- Modify parameter files (``clm_params.nc``, ``CNP_parameters.nc``) for parameter perturbations or custom physics (hummock/hollow, marsh, polygonal tundra, etc.)
- Copy source modifications from ``--srcmods_loc``
- Build the model (``./case.build``) or skip if ``--no_build``
- Optionally submit the case (``./case.submit``) or generate ensemble PBS/SLURM scripts for MPI-parallel parameter sweeps

All shell commands are logged via ``runcmd()``, which records to ``--options_log_json`` and traps a CIME quirk where ``case.submit`` converts exceptions to warnings.


Seven-Step Workflow
====================

From the script docstring (lines 88–96), ``runcase.py`` performs these steps in sequence:

1. **Create point/domain/surface data** — shell out to ``makepointdata.py`` (unless ``--nopointdata`` or ``--makepointdata_only``).
2. **Create new case** — run ``create_newcase`` with machine, compset, resolution, MPI library, walltime, project, and compiler.
3. **Set point and case-specific namelist options** — write ``user_nl_elm`` with physics flags, output variables, parameter file paths, finidat, forcing paths, and transient/spinup settings.
4. **Configure case** — run ``./case.setup`` (unless ``--no_config``).
5. **Build model** — run ``./case.build`` (unless ``--no_build``); optionally ``--clean_build`` first.
6. **Apply user-specified PBS/SLURM and submit information** — for ensemble runs (``--ensemble_file`` or ``--mc_ensemble``), generate MPI job scripts that call ``manage_ensemble.py``.
7. **Submit job** — run ``./case.submit`` for single runs, or submit ensemble scripts (unless ``--no_submit``).


Command-Line Arguments
=======================

``runcase.py`` uses ``optparse`` (not ``argparse``) with ~150 options. They are grouped below by category.

General OLMT Options
---------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--caseidprefix``
     - Unique identifier prepended to case name (default: ``""``)
   * - ``--caseroot``
     - Case directory root (default: ``""``, i.e., ``$MODEL_ROOT/cime/scripts/``)
   * - ``--runroot``
     - Directory where run directories are created (required)
   * - ``--tempdir``
     - Per-invocation staging directory; defaults to ``./temp/run_<pid>_<ms>``
   * - ``--model_root``
     - Base model directory (E3SM or CESM source tree)
   * - ``--ccsm_input``
     - Input data directory (required)
   * - ``--project``
     - Set project code for machine accounting
   * - ``--exeroot``
     - Location of executable (if pre-built)
   * - ``--constraints``
     - Directory containing model constraints (ensemble mode)
   * - ``--metdata_dir``
     - Directory containing ``cpl_bypass`` met data (site only)
   * - ``--pft``
     - Use this PFT for all gridcells
   * - ``--parm_file``
     - File for parameter modifications (whitespace-delimited: ``name [pft] value``)
   * - ``--parm_vals``
     - User-specified parameter values (format: ``name[,pft],value[/name[,pft],value...]``)
   * - ``--parm_file_P``
     - File for P parameter modifications (ELM only)

Model Build Options
--------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--machine``
     - Target machine (``cades``, ``compy``, ``anvil``, ``chrysalis``, ``docker``, etc.)
   * - ``--compiler``
     - Compiler to use (``gnu``, ``pgi``, ``intel``)
   * - ``--mpilib``
     - MPI library (``openmpi``, ``mpich``, ``ibm``, ``mpi-serial``; default: ``mpi-serial``)
   * - ``--diags``
     - Write special outputs for diagnostics (hourly, daily, PFT-level)
   * - ``--debugq``
     - Use debug queue
   * - ``--srcmods_loc``
     - Copy sourcemods from this location
   * - ``--pio_version``
     - PIO version (``1`` or ``2``; default: ``2``)

Case Options
-------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--coldstart``
     - Set cold start (mutually exclusive with ``--finidat``)
   * - ``--compset``
     - Component set (default: ``I1850CNPRDCTCBC``)
   * - ``--istrans``
     - Force compset to act like transient
   * - ``--lat_bounds``, ``--lon_bounds``
     - Latitude/longitude range for regional run
   * - ``--humhol``
     - Use hummock/hollow microtopography
   * - ``--marsh``
     - Use marsh hydrology/elevation
   * - ``--tide_components_file``
     - NOAA tide components file (for marsh)
   * - ``--mask``
     - Mask file to use (regional only)
   * - ``--model``
     - Model to use (``ELM``, ``CLM5``)
   * - ``--namelist_file``
     - File containing custom namelist options for ``user_nl_clm``
   * - ``--ilambvars``, ``--dailyvars``
     - Write special output variables
   * - ``--res``
     - Resolution for global simulation (default: ``CLM_USRDAT``)
   * - ``--point_list``
     - File containing list of points to run

Surface Data Options
---------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--sitegroup``
     - Site group to use (default: ``AmeriFlux``)
   * - ``--site``
     - 6-character FLUXNET code to run (required for site runs)
   * - ``--site_forcing``
     - 6-character FLUXNET code for forcing data
   * - ``--metdir``
     - Subdirectory for met data forcing
   * - ``--surffile``, ``--domainfile``
     - User-provided surface/domain file
   * - ``--landusefile``
     - User-defined dynamic PFT file
   * - ``--surfdata_grid``
     - Use gridded surface data instead of site data
   * - ``--include_nonveg``
     - Include non-vegetated columns/landunits in surface data

Meteorological Forcing Options
--------------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--cruncep``, ``--cruncepv8``
     - Use CRU-NCEP forcing (v5 or v8)
   * - ``--crujra``
     - Use CRUJRA forcing
   * - ``--trendy25``
     - Use TRENDY 2025 forcing
   * - ``--gswp3``, ``--gswp3_w5e5``
     - Use GSWP3 forcing (v1 or W5E5 variant)
   * - ``--era5``
     - Use ERA5 atmospheric reanalysis
   * - ``--princeton``
     - Use Princeton forcing
   * - ``--cplhist``
     - Use CPLHIST forcing
   * - ``--livneh``, ``--daymet``, ``--daymet4``
     - Apply correction to CONUS precipitation
   * - ``--monthly_metdata``
     - File containing met data biases (``cpl_bypass`` only)
   * - ``--add_temperature``
     - Temperature to add to atmospheric forcing (K)
   * - ``--add_co2``
     - CO₂ (ppmv) to add to atmospheric forcing
   * - ``--co2_file``
     - CO₂ data file (default: ``fco2_datm_rcp4.5_1765-2500_c130312.nc``)

Spinup and Restart Options
----------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--ad_spinup``
     - Run accelerated decomposition spinup
   * - ``--exit_spinup``
     - Run exit spinup (CLM 4.0 only)
   * - ``--finidat_case``
     - Case containing initial data file
   * - ``--finidat``
     - Initial data file (absolute path)
   * - ``--finidat_year``
     - Model year of initial data file (default: last available)
   * - ``--branch``
     - Switch for branch run
   * - ``--run_units``
     - Run length units (``ndays``, ``nyears``; default: ``nyears``)
   * - ``--run_n``
     - Run length (in ``--run_units``; default: 50)
   * - ``--rest_n``
     - Restart interval (in ``--run_units``; default: -1, i.e., no restart)
   * - ``--run_startyear``
     - Starting year for model output

Model Output Options
---------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--hist_mfilt``
     - Number of output timesteps per file
   * - ``--hist_nhtfrq``
     - Output file timestep (0=monthly, -24=daily, 1=hourly, etc.)
   * - ``--hist_vars``
     - Output only selected variables in h0 file (comma-delimited)
   * - ``--spinup_vars``
     - Limit output vars in spinup runs
   * - ``--trans_varlist``
     - Transient outputs (comma-delimited)
   * - ``--var_list_pft``
     - Comma-separated list of vars to output at PFT level

Build and Submit Options
--------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--clean_config``
     - Run ``case.setup -clean`` before setup
   * - ``--clean_build``
     - Perform clean build before building
   * - ``--no_config``
     - Do NOT configure case
   * - ``--no_build``
     - Do NOT build model
   * - ``--no_submit``
     - Do NOT submit built model to queue (build only)
   * - ``--rmold``
     - Remove old case directory before proceeding
   * - ``--np``
     - Number of processors (default: 1)
   * - ``--ninst``
     - Number of land model instances (default: 1)
   * - ``--ng``
     - Number of groups to run in ensemble mode (default: 64)
   * - ``--tstep``
     - Model timestep in hours (default: 0.5)
   * - ``--walltime``
     - Desired walltime for each job in hours (default: 6)

BGC and Physics Options
------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--nofire``
     - Turn off wildfires
   * - ``--nopftdyn``
     - Do not use dynamic PFT file
   * - ``--harvmod``
     - Turn on harvest modification (all harvest in first timestep)
   * - ``--no_dynroot``
     - Turn off dynamic root distribution
   * - ``--vertsoilc``
     - Turn on CN with multiple soil layers (excluding CENTURY)
   * - ``--centbgc``
     - Turn on CN with CENTURY C module
   * - ``--CH4``, ``--no_methane``
     - Turn CH₄ on/off
   * - ``--1850_ndep``, ``--ndep_rcp85``
     - Use constant 1850 or RCP8.5 N deposition
   * - ``--1850_aero``, ``--aero_rcp85``
     - Use constant 1850 or RCP8.5 aerosol deposition
   * - ``--1850_co2``
     - Use constant 1850 CO₂ concentration
   * - ``--C13``, ``--C14``
     - Switch to turn on C13/C14
   * - ``--c_only``, ``--cn_only``, ``--cp_only``
     - Run carbon-only, CN-only, or CP-only (supplemental nutrients)
   * - ``--var_soilthickness``
     - Use variable soil thickness from surface data
   * - ``--no_budgets``
     - Turn off CNP budget calculations
   * - ``--use_hydrstress``
     - Turn on hydraulic stress

FATES Options
--------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--fates_hydro``
     - Set FATES hydro to true
   * - ``--fates_nutrient``
     - Which version of FATES nutrient to use (``RD`` or ``ECA``)
   * - ``--fates_logging``
     - Set FATES logging to true
   * - ``--fates_paramfile``
     - FATES parameter file to use

NGEE Arctic Options
--------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--topounits_atmdownscale``
     - Use atmospheric downscaling in topounits
   * - ``--topounits_raddownscale``
     - Downscale radiation input to topounits
   * - ``--dust_snow_mixing``
     - Use Hao et al. dust/snow mixing albedo parameterization
   * - ``--no_snicar_ad``
     - Turn off SNICAR-AD snow microphysics model
   * - ``--use_extra_snow_layers``
     - Turn on extra snow layers
   * - ``--use_firn_percolation_and_compaction``
     - Turn on firn percolation and compaction
   * - ``--use_polygonal_tundra``
     - Turn on polygonal tundra parameterizations (NGEE Arctic Phase 3 IM1)
   * - ``--unified_polygonal_tundra``
     - Use unified polygonal tundra across all topounits
   * - ``--use_arctic_init``
     - Use colder and saturated initial conditions (NGEE Arctic IM2 and IM0)
   * - ``--use_IM2_hillslope_hydrology``
     - Use NGEE Arctic Hillslope Hydrology across topounits
   * - ``--arctic_topounit_output``
     - Activate topounit-level and PFT-level outputs (``hist_dov2xy``)
   * - ``--use_onset_gdd_extension``
     - Extend leaf onset based on accumulated GDD past summer solstice
   * - ``--balland_and_arp``
     - Use Balland and Arp (2005) soil thermal conductivity model

Ensemble Options
-----------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--ensemble_file``
     - Parameter sample file to generate ensemble
   * - ``--mc_ensemble``
     - Monte Carlo ensemble (argument is # of simulations)
   * - ``--ensemble_nocopy``
     - Do not copy files to ensemble directories
   * - ``--parm_list``
     - File containing list of parameters to vary (format: ``name pft min max``)
   * - ``--postproc_file``
     - File for ensemble post-processing
   * - ``--spruce_treatments``
     - Run SPRUCE treatment simulations (ensemble mode)

Other Options
--------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--nopointdata``
     - Do NOT make point data (use data already created)
   * - ``--makepointdata_only``
     - Make point data for later use ONLY (no model config/build/submit)
   * - ``--alquimia``
     - Compile model with Alquimia BGC interface using specified input file
   * - ``--options_log_json``
     - Full path to JSON file recording all OLMT options and syscalls (default: ``None``)
   * - ``--archiveroot``
     - Archive root directory (only for mesabi)
   * - ``--mod_parm_file``, ``--mod_parm_file_P``
     - Path to modified parameter file (PFT or P)


CIME Integration
=================

``create_newcase`` Command
---------------------------

Line 1871–1895. Constructs the ``create_newcase`` command with::

    ./create_newcase --case <casedir> --mach <machine> --compset <compset> --res <res> \
                     --mpilib <mpilib> --walltime <timestr> --handle-preexisting-dirs u \
                     [--run-unsupported] [--project <project>] [--compiler <compiler>]

``xmlchange`` Variables
------------------------

After case creation, ``runcase.py`` applies dozens of ``./xmlchange`` commands to configure CIME XML files. Key examples:

- **Build settings:** ``SAVE_TIMING=FALSE``, ``EXEROOT``, ``PIO_VERSION``, ``MOSART_MODE=NULL``
- **Run settings:** ``RUNDIR``, ``DOUT_S``, ``DOUT_S_ROOT``, ``DIN_LOC_ROOT``, ``DIN_LOC_ROOT_CLMFORC``
- **Domain/resolution:** ``<LSM>_USRDAT_NAME`` (for site runs)
- **Spinup:** ``CLM_ACCELERATED_SPINUP=on`` (CLM5) or ``--append <LSM>_BLDNML_OPTS='-bgc_spinup on'`` (ELM)
- **DATM forcing:** ``DATM_MODE`` (``CLMCRUNCEP``, ``CLMGSWP3v1``, ``CLM1PT``), ``DATM_CLMNCEP_YR_START``, ``DATM_CLMNCEP_YR_END``, ``DATM_CLMNCEP_YR_ALIGN``
- **Tasks:** ``NTASKS_<comp>``, ``NTHRDS_<comp>``, ``MAX_TASKS_PER_NODE``, ``MAX_MPITASKS_PER_NODE``
- **Stop/restart:** ``STOP_OPTION``, ``STOP_N``, ``REST_N``
- **Transient/branch:** ``RUN_TYPE=branch``, ``RUN_REFDATE``, ``RUN_REFCASE``, ``CCSM_BGC=CO2A``, ``<LSM>_CO2_TYPE=diagnostic``

Configuration options are also appended to ``<LSM>_BLDNML_OPTS`` for features like topounits (``-topounit``), maximum PFT number (``-maxpft``), or methane disabling (stripping ``-methane``).


Namelist Generation
====================

``user_nl_elm`` (or ``user_nl_clm``)
--------------------------------------

Lines 2087–3035 write the land model namelist. Structure::

    &clm_inparm
      ! Custom namelist from --namelist_file (if provided)
      ! History file options (hist_mfilt, hist_nhtfrq, hist_fincl*, hist_dov2xy)
      ! Initial data (finidat)
      ! Surface data (fsurdat, flanduse_timeseries)
      ! Parameter files (paramfile, fsoilordercon, fates_paramfile)
      ! Forcing paths (metdata_type, metdata_bypass, co2_file, aero_file)
      ! Physics flags (use_lch4, use_c13, use_c14, use_nofire, use_hydrstress, etc.)
      ! NGEE Arctic flags (use_polygonal_tundra, use_arctic_init, use_IM2_hillslope_hydrology, etc.)
    /

**Key branches:**

- **Spinup mode** (``--ad_spinup``): write long-term average pool variables to ``hist_fincl2`` (``CWDC_vr``, ``SOIL2C_vr``, ``SOIL3C_vr``, etc.), set ``finidat = ''``, adjust ``hist_mfilt``/``hist_nhtfrq``.
- **Transient mode** (``20TR`` in compset or ``--istrans``): disable ``finidat`` auto-setting, write ``flanduse_timeseries``, set ``check_finidat_fsurdat_consistency = .false.``.
- **Diagnostics mode** (``--diags``): create 5 history streams (annual, hourly, daily-column, daily-PFT, annual-PFT) with extensive variable lists.
- **CPL_BYPASS mode** (``CBCN``/``ICB`` compsets): write ``metdata_type`` (``'cru-ncep'``, ``'gswp3'``, ``'gswp3_daymet4'``, ``'era5'``, ``'era5_daymet4'``, ``'site'``, etc.) and ``metdata_bypass`` path. If site forcing, use ``CLM1PT_data/<ptstr>_<site>/``. If reanalysis, use full ``cpl_bypass_full/`` paths.
- **Hummock/hollow or marsh** (``--humhol``, ``--marsh``): set ``humhol_ht``, ``hum_frac``, ``humhol_dist``, ``qflx_h2osfc_surfrate``, ``rsub_top_globalmax``, ``h2osoi_offset`` in ``clm_params.nc`` (via ``ncap2`` commands, lines 1592–1730); optionally parse ``--tide_components_file`` to generate tidal harmonic coefficients.

``user_nl_datm``
-----------------

Lines 3163–3264 write the DATM namelist when **not** using ``cpl_bypass``. Key modifications:

- **``streams``**: construct list of DATM stream files with start/end/align years. For ``CLMCRUNCEP`` or ``CLMGSWP3v1``, three streams (Solar, Precip, TPQW) plus ``presaero`` and optional ``co2tseries.20tr`` for transient runs. For ``CLM1PT``, single user stream.
- **``taxmode``**: set to ``'cycle', 'cycle', 'cycle', 'extend', 'extend'`` (for reanalysis) or ``'cycle', 'extend', 'extend'`` (for site forcing). Append ``'extend'`` for transient CO₂.

Also writes user stream override files (``user_datm.streams.txt.<stream_name>``) to patch aerosol file names or CO₂ file paths, and reverse directories for ``CLM1PT`` site forcing.

``user_nl_mosart``
-------------------

Not explicitly written in ``runcase.py``; MOSART is set to ``NULL`` mode via ``./xmlchange MOSART_MODE=NULL`` (line 1917).


Source Modifications
=====================

``--srcmods_loc`` Handling
---------------------------

Lines 3131–3136. If ``--srcmods_loc`` is provided, ``runcase.py``:

1. Checks that the directory exists.
2. Converts to absolute path.
3. Copies all contents to ``<casename>/SourceMods/`` via ``cp -r``.

For example, the CI workflow uses ``--srcmods_loc srcmods_era5cb`` to copy ``lnd_import_export.F90`` overrides for ERA5 + cpl_bypass simulations.


PBS/SLURM Submission Script Generation
========================================

Ensemble Mode (lines 3423–3596)
---------------------------------

When ``--ensemble_file`` or ``--mc_ensemble`` is provided, ``runcase.py`` generates a PBS or SLURM script (``scripts/<caseid>/ensemble_run_<casename>.pbs``) that:

- Sets walltime (``--walltime``), job name, project, nodes, and partition based on ``--machine``.
- Sources environment from ``<casedir>/software_environment.txt`` (for CADES, compy, anvil, chrysalis).
- Runs ``mpirun`` (or ``srun``) with ``manage_ensemble.py`` to distribute parameter samples across MPI ranks.

Command constructed (lines 3504–3582)::

    mpirun -n <np_total> python manage_ensemble.py \
        --case <casename> --runroot <runroot> --n_ensemble <nsamples> \
        --ens_file <ensemble_file> --exeroot <exeroot> --parm_list <parm_list> \
        --cnp <True/False> --site <site> --model_name <model_name> \
        [--constraints <constraints>] [--postproc_file <postproc_file>] \
        [--spruce_treatments]

If ``--no_submit`` is False, submits via ``qsub`` or ``sbatch``.

Single-Run Mode (line 3342)
-----------------------------

For non-ensemble runs, simply calls ``./case.submit`` unless ``--no_submit``.


Error Handling
==============

``runcmd()`` Function (lines 49–77)
------------------------------------

Every shell command in ``runcase.py`` is executed via ``runcmd(cmd, echo=True, check=True, tag=...)``. This function:

1. Logs the command to ``--options_log_json`` (if provided) via ``_write_cmd()``.
2. Runs the command with ``subprocess.run(..., shell=True, check=check, text=True, capture_output=True)``.
3. **CIME quirk trap**: CIME's ``case.submit`` converts Python exceptions in PBS submission to warnings, so ``runcmd()`` explicitly checks stderr for ``"Exception from "`` and exits if found (lines 75–76)::

       if check == True and "Exception from " in result.stderr:
           sys.exit(f"Error in run command {cmd}")

This prevents silent failures when PBS/SLURM submission fails.

Options Logging (``--options_log_json``)
------------------------------------------

Lines 16–46. If ``--options_log_json`` is provided, ``runcase.py`` writes a JSON array of command records, each with:

- ``i``: sequence number
- ``tag``: script name (``runcase.py`` or child script tag)
- ``lineno``: source line number (via ``inspect.stack()``)
- ``cmd``: raw command string or parsed dict (for ``create_newcase``, ``.py`` scripts)

This provides a complete audit trail of OLMT syscalls for reproducibility and debugging.


Relationship to Parent Scripts
================================

``site_fullrun.py`` / ``global_fullrun.py`` → ``runcase.py``
--------------------------------------------------------------

- **First site** (or single global run): parent constructs a ``runcase.py`` shell-out for **each** of the three phases (ad_spinup, final spinup, transient), passing:

  - ``--ad_spinup`` for phase 1
  - ``--finidat_case`` (pointing to phase 1 output) for phase 2
  - ``--finidat_case`` (pointing to phase 2 output) and ``--compset`` with ``20TR`` for phase 3
  - Common flags: ``--model_root``, ``--ccsm_input``, ``--site``, ``--sitegroup``, ``--tempdir``, ``--cruncep``/``--gswp3``/``--era5``, etc.

- **Additional sites**: instead of calling ``runcase.py``, parent calls ``case_copy.py`` to clone the first site's case directory and patch it with new site lat/lon/surface data. This is much faster than rebuilding.

``runcase.py`` → ``makepointdata.py``
---------------------------------------

Lines 1403–1464. If not ``--nopointdata``, ``runcase.py`` shells out to ``makepointdata.py`` with:

- ``--ccsm_input``, ``--mysimyr``, ``--model``, ``--tempdir``
- ``--site``, ``--sitegroup`` (for site runs) or ``--res``, ``--point_list`` (for global/multi-point runs)
- ``--metdir`` (if user-provided), ``--makemetdata``, ``--surfdata_grid``, ``--include_nonveg``, ``--nopftdyn``
- ``--mask``, ``--lai``, ``--pft``, ``--crop``, ``--marsh``, ``--humhol``

``makepointdata.py`` generates ``domain.nc``, ``surfdata.nc``, ``surfdata.pftdyn.nc`` in ``<tempdir>/``, which ``runcase.py`` copies to the run directory after build (lines 3327–3334).


Examples
=========

Example 1: Single-Site Final Spinup
-------------------------------------

Called by ``site_fullrun.py`` after ad_spinup completes::

    python runcase.py \
      --model_root /path/to/E3SM \
      --ccsm_input /path/to/inputdata \
      --runroot /path/to/cases \
      --site US-Brw \
      --sitegroup NGEEArctic \
      --compset I1850CNPRDCTCBC \
      --finidat_case US-Brw_I1850CNPRDCTCBC_ad_spinup \
      --finidat_year 251 \
      --run_units nyears \
      --run_n 200 \
      --machine docker \
      --mpilib mpi-serial \
      --gswp3 \
      --tempdir /tmp/olmt_run_12345_67890 \
      --no_submit

This will:

1. Skip ``makepointdata.py`` (already run during ad_spinup).
2. Create case ``US-Brw_I1850CNPRDCTCBC`` in ``<runroot>/``.
3. Set ``finidat`` to ``<runroot>/US-Brw_I1850CNPRDCTCBC_ad_spinup/run/US-Brw_I1850CNPRDCTCBC_ad_spinup.elm.r.0251-01-01-00000.nc``.
4. Build ELM with ``mpi-serial``.
5. Skip submission (``--no_submit``).

Example 2: Regional Transient with ERA5 + Daymet4 + Source Mods
-----------------------------------------------------------------

::

    python runcase.py \
      --model_root /path/to/E3SM \
      --ccsm_input /path/to/inputdata \
      --runroot /path/to/cases \
      --res ELM_USRDAT \
      --lat_bounds 65.0,70.0 \
      --lon_bounds -165.0,-150.0 \
      --compset I20TRCNPRDCTCBC \
      --finidat_case my_region_I1850CNPRDCTCBC \
      --finidat_year 1850 \
      --run_units nyears \
      --run_n 170 \
      --machine cades \
      --np 32 \
      --era5 \
      --daymet4 \
      --metdir /path/to/era5_daymet4_forcing/ \
      --srcmods_loc srcmods_era5cb/ \
      --walltime 12 \
      --project CLI185 \
      --options_log_json /path/to/olmt_log.json

This will:

1. Call ``makepointdata.py`` to extract domain/surface/landuse for 65–70°N, 165–150°W.
2. Create case with ``I20TRCNPRDCTCBC`` (transient BGC) compset.
3. Set ``finidat`` to final spinup restart from 1850.
4. Set ``metdata_type = 'era5_daymet4'`` and ``metdata_bypass = '/path/to/era5_daymet4_forcing/'``.
5. Copy source mods from ``srcmods_era5cb/`` to ``SourceMods/``.
6. Build on 32 cores (CADES SLURM).
7. Submit via ``sbatch`` with 12-hour walltime.
8. Log all commands to ``/path/to/olmt_log.json``.

Example 3: Monte Carlo Ensemble (100 samples)
-----------------------------------------------

::

    python runcase.py \
      --model_root /path/to/E3SM \
      --ccsm_input /path/to/inputdata \
      --runroot /path/to/cases \
      --site US-Brw \
      --sitegroup NGEEArctic \
      --compset I1850CNPRDCTCBC \
      --machine compy \
      --np 1 \
      --ng 64 \
      --gswp3 \
      --mc_ensemble 100 \
      --parm_list examples/parm_list_example \
      --walltime 6 \
      --no_submit

This will:

1. Read parameter names/ranges from ``examples/parm_list_example``.
2. Generate 100 random samples via Latin hypercube (or uniform random).
3. Write samples to ``mcsamples_US-Brw_I1850CNPRDCTCBC.txt``.
4. Build case ``US-Brw_I1850CNPRDCTCBC`` with ``mpi-serial``.
5. Generate ``scripts/ensemble_run_US-Brw_I1850CNPRDCTCBC.pbs`` with 64 groups (``--ng 64``), total 64 MPI ranks.
6. Skip submission (``--no_submit``); user can inspect and submit manually.


Summary
========

``runcase.py`` is the workhorse of OLMT's CIME integration, handling:

- **Data generation** (via ``makepointdata.py``)
- **Case creation** (``create_newcase``)
- **XML configuration** (``xmlchange``)
- **Namelist generation** (``user_nl_elm``, ``user_nl_datm``)
- **Parameter file modification** (``ncap2`` commands for custom physics)
- **Source modifications** (``--srcmods_loc``)
- **Build** (``./case.build``)
- **Submission** (``./case.submit`` or ensemble PBS/SLURM scripts)

It is **not** user-facing — ``site_fullrun.py`` and ``global_fullrun.py`` construct the appropriate ``runcase.py`` invocations for each spinup/transient phase. For debugging, the ``--options_log_json`` flag provides a complete audit trail of all CIME commands issued.
