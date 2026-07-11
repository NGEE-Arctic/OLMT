================
site_fullrun.py
================

Overview
========

``site_fullrun.py`` is the **primary entry point for single-site ELM/CLM simulations** in OLMT. It orchestrates the standard three-phase BGC spinup and transient workflow, automating case creation, configuration, building, and submission for one or more sites.

Unlike ``runcase.py`` (which handles a single case), ``site_fullrun.py`` manages the complete simulation sequence:

1. **AD spinup** — accelerated decomposition spinup to equilibrate soil carbon pools
2. **Final spinup** — equilibrate biomass and nutrient pools at normal decomposition rates
3. **Transient** — historical simulation (default: 1850–present) with prescribed forcing, land use, and CO2

Each phase is a separate CIME case. For the first site, ``site_fullrun.py`` shells out to ``runcase.py`` to build each case. For additional sites (when ``--site`` is a comma-delimited list or ``all``), it calls ``case_copy.py`` to clone the first site's run directory, which avoids rebuilding the executable and is significantly faster.

``site_fullrun.py`` does **not** run the model itself — it generates and submits CIME cases. A working E3SM (or CESM/CTSM) source tree and inputdata directory are required.


Command-Line Arguments
======================

General OLMT Options
--------------------

``--no_submit``
  Do NOT submit built model to queue (build only). Default: False.

``--caseidprefix <string>``
  Unique identifier to include as a prefix to the case name. Default: empty.

``--caseroot <path>``
  Case root directory where submission scripts live. Default: ``model_root/cime/scripts``.

``--runroot <path>``
  Directory where the run would be created. Default: machine-dependent or ``model_root/run``.

``--tempdir <path>``
  Per-invocation staging directory. Defaults to ``./temp/run_<pid>_<ms>``. All child script invocations share this directory to avoid concurrent collisions.

``--exeroot <path>``
  Location of executable (if pre-built). Default: empty (build fresh).

``--archiveroot <path>``
  Archive root directory (mesabi only). Default: empty.

``--batch_build``
  Do build as part of submitted batch script. Default: False.

``--constraints <path>``
  Directory containing model constraints. Default: empty.

``--compare_cases <string>``
  caseidprefix(es) to compare. Default: empty.

``--ninst <int>``
  Number of land model instances. Default: 1.

``--mc_ensemble <int>``
  Monte Carlo ensemble (argument is number of simulations). Default: -1 (off).

``--ng <int>``
  Number of groups to run in ensemble mode. Default: 256.

``--parm_list <path>``
  File containing list of parameters to vary (ensemble mode). Default: ``parm_list``.

``--mod_parm_file <path>``
  Path to modified parameter file. Default: empty.

``--mod_parm_file_P <path>``
  Path to modified parameter file (P). Default: empty.

``--ensemble_file <path>``
  Parameter sample file to generate ensemble. Default: empty.

``--postproc_file <path>``
  File for ensemble post-processing. Default: ``postproc_vars``.

``--nopftdyn``
  Do not use dynamic PFT file. Default: False.


Model Build Options
-------------------

``--model_root <path>``
  Base CESM/E3SM directory. **Required** (or defaults to ``../E3SM`` if it exists).

``--compiler <string>``
  Compiler to use (``pgi``, ``gnu``, etc.). Default: empty (machine default).

``--mpilib <string>``
  MPI library (``openmpi``, ``mpich``, ``ibm``, ``mpi-serial``). Default: ``mpi-serial``.

``--debugq``
  Use debug queue and options. Default: False.

``--clean_build``
  Perform a clean build. Default: False.

``--cpl_bypass``
  Bypass coupler (direct-to-land forcing). Default: False.

``--machine <string>``
  Machine to use. Default: inferred from hostname.

``--np <int>``
  Number of processors. Default: 1.

``--walltime <hours>``
  Desired walltime for each job (hours). Default: 6.

``--pio_version <1|2>``
  PIO version. Default: 2.


Simulation Length and Phase Control
------------------------------------

``--nyears_ad_spinup <int>``
  Number of years to run AD spinup. Default: 250. Must be a multiple of the met cycle length.

``--nyears_final_spinup <int>``
  Base number of years for final spinup. Default: 200. Must be a multiple of the met cycle length.

``--nyears_transient <int>``
  Number of years to run transient. Default: -1 (auto: 1850 to end of forcing).

``--ad_Pinit``
  Initialize AD spinup with P pools and use CNP mode. Default: False (CN mode for AD spinup).

``--noad``
  **Do not perform AD spinup simulation.** Default: False.

``--nofnsp``
  **Do not perform final spinup simulation.** Default: False.

``--notrans``
  **Do not perform transient simulation (spinup only).** Default: False.

``--finidat <path>``
  Full path of ELM restart file to use (for transient only, requires ``--noad --nofnsp``). Default: empty.


Site and Input Data Options
----------------------------

``--site <string>``
  6-character FLUXNET code(s) to run. **Required.** Can be a single site, a comma-delimited list (``US-Brw,US-NR1``), or ``all`` (all sites in sitegroup). Example: ``US-Brw``.

``--sitegroup <string>``
  Site group to use. Default: ``AmeriFlux``. Options: ``AmeriFlux``, ``NGEEArctic``, ``Wetland``. Determines which ``<sitegroup>_sitedata.txt`` file is read from ``inputdata/lnd/clm2/PTCLM/``.

``--ccsm_input <path>``
  Input data directory for CESM/E3SM. **Required** (or defaults to machine-specific location).

``--nopointdata``
  Do NOT make point data (use data already created). Default: False.

``--metdir <path>``
  Subdirectory for met data forcing (cpl_bypass mode). Default: ``none``.

``--metdata_dir <path>``
  Directory containing cpl_bypass met data (site only). Default: ``none``.

``--makemetdata``
  Generate site meteorology. Default: False.


Meteorological Forcing Options
-------------------------------

The forcing-source flags are **mutually exclusive**. They control two things:

1. The spinup met cycle is hard-coded to 1901–1920.
2. The transient end year (``endyear_trans``) is set to the latest year of available forcing.

``--cruncep``
  Use CRU-NCEP meteorology. Transient ends 2010. Default: False.

``--cruncepv8``
  Use CRU-NCEP v8 meteorology. Transient ends 2016. Default: False.

``--era5``
  Use ERA5 meteorology. Transient ends 2023. Default: False. **Note:** ERA5 forcing with ``--cpl_bypass`` requires source modifications (``srcmods_era5cb/``).

``--gswp3``
  Use GSWP3 meteorology. Transient ends 2014. Default: False.

``--gswp3_w5e5``
  Use GSWP3-W5E5 meteorology. Transient ends 2019. Default: False.

``--princeton``
  Use Princeton meteorology. Transient ends 2012. Default: False.

``--crujra``
  Use CRU-JRA meteorology. Transient ends 2024. Default: False.

``--trendy25``
  Use TRENDY2025 meteorology. Transient ends 2021. Default: False.

``--daymet``
  Use Daymet corrected meteorology. Default: False.

``--daymet4``
  Use Daymet v4 downscaled GSWP3-v2 or ERA5 forcing (with user-provided domain and surface data). Default: False.


CO2 and Climate Forcing
------------------------

``--co2_file <filename>``
  CO2 data filename. Default: ``fco2_datm_rcp4.5_1765-2500_c130312.nc``.

``--eco2_file <filename>``
  Elevated CO2 data filename. When set, spawns **three** transient simulations: (1) standard historical, (2) ambient CO2 (``aCO2``), (3) elevated CO2 (``eCO2``). Default: empty.

``--add_co2 <ppmv>``
  CO2 (ppmv) to add to atmospheric forcing. Default: 0.0.

``--startdate_add_co2 <YYYYMMDD>``
  Date to begin adding CO2. Default: ``99991231``.

``--add_temperature <K>``
  Temperature to add to atmospheric forcing. Default: 0.0.

``--startdate_add_temperature <YYYYMMDD>``
  Date to begin adding temperature. Default: ``99991231``.


Surface Data Options
--------------------

``--surfdata_grid``
  Use gridded surface data instead of site data. Default: False.

``--surffile <path>``
  Use specified surface data file. Default: empty (auto-generate via ``makepointdata.py``).

``--domainfile <path>``
  Domain file to use. Default: empty (auto-generate).

``--pft <int>``
  Use this PFT (override site default). Default: -1 (use site default).

``--siteparms``
  Use default PFT parameters. Default: False.

``--parm_file <path>``
  Parameter file to use. Default: empty.

``--parm_file_P <path>``
  Parameter file to use (P). Default: empty.

``--fates_paramfile <path>``
  FATES parameter file to use. Default: empty.

``--parm_vals <string>``
  User-specified parameter values. Default: empty.


Model Configuration Options
----------------------------

``--namelist_file <path>``
  File containing custom namelist options for ``user_nl_clm``. Default: empty.

``--tstep <hours>``
  CLM timestep (hours). Default: 0.5.

``--SP``
  Use satellite phenology mode. Default: False.

``--lai <value>``
  Set constant LAI (SP mode only). Default: -999 (not set).

``--run_startyear <YYYY>``
  Starting year for simulation (SP mode only). Default: 1850.

``--crop``
  Perform a crop model simulation. Default: False.

``--humhol``
  Use hummock/hollow microtopography. Default: False.

``--marsh``
  Use marsh hydrology/elevation. Default: False.

``--tide_components_file <path>``
  NOAA tide components file. Default: empty.

``--tide_forcing_file <path>``
  Tide height and salinity forcing time series file. Default: empty.

``--nofire``
  Turn off fire algorithms. Default: False.

``--C13``
  Switch to turn on C13. Default: False.

``--C14``
  Use C14 as C13 (no decay). Default: False.

``--aero_rcp85``
  Use RCP8.5 aerosols. Default: False.

``--ndep_rcp85``
  Use RCP8.5 N deposition. Default: False.

``--harvmod``
  Turn on harvest modification (all harvest at first timestep). Default: False.

``--no_dynroot``
  Turn off dynamic root distribution. Default: False.

``--vertsoilc``
  Turn on CN with multiple soil layers, excluding CENTURY C module (CLM4ME on). Default: False.

``--centbgc``
  Turn on CN with multiple soil layers, CENTURY C module (CLM4ME on). Default: False.

``--CH4``
  Turn on CN with CLM4me (methane). Default: False.

``--no_methane``
  Turn off CH4 for BGC runs. Default: False.

``--fates``
  Use FATES model. Default: False.

``--fates_nutrient <RD|ECA>``
  Which version of fates_nutrient to use. Default: empty.

``--fates_logging``
  Set FATES logging to true. Default: False.

``--ECA``
  Use ECA compset. Default: False.

``--c_only``
  Carbon only (saturated N&P). Default: False.

``--cn_only``
  Carbon/Nitrogen only (saturated P). Default: False.

``--srcmods_loc <path>``
  Copy sourcemods from this location. Default: empty.

``--dailyvars``
  Write daily output variables. Default: False.

``--var_soilthickness``
  Use variable soil depth from surface data file. Default: False.

``--no_budgets``
  Turn off CNP budget calculations. Default: False.

``--alquimia <path>``
  Compile model with Alquimia BGC interface using specified input file. Default: empty.

``--alquimia_ad <path>``
  Alquimia input file for AD spinup. Default: empty.

``--use_hydrstress``
  Turn on hydraulic stress. Default: False.

``--spruce_treatments``
  Run SPRUCE treatment simulations (ensemble mode). Default: False.

``--balland_and_arp``
  Use Balland and Arp (2005) soil thermal conductivity model. Default: False.


Model Output Options
--------------------

``--hist_vars <string>``
  Output only selected variables in h0 file (comma delimited). Default: empty (all variables).

``--diags``
  Write special outputs for diagnostics. Default: False.

``--trans_varlist <string>``
  Transient outputs. Default: empty.

``--hist_mfilt_trans <int>``
  Number of output timesteps per file (transient only). Default: 365.

``--hist_nhtfrq_trans <int>``
  Output file timestep (transient only). Default: -24 (daily).

``--spinup_vars``
  Limit output variables for spinup. Default: False.

``--dailyrunoff``
  Turn on hydrological terms for analyzing hydrology. Default: False.

``--hist_mfilt_spinup <int>``
  Number of output timesteps per file (spinup only). Default: -999 (one file per cycle).

``--hist_nhtfrq_spinup <int>``
  Output file timestep (spinup only). Default: -999 (one timestep per cycle).


NGEE Arctic Options
-------------------

**Snow Options**

``--dust_snow_mixing``
  Use Hao et al. dust/snow mixing albedo parameterization. Default: False.

``--no_snicar_ad``
  Turn off SNICAR-AD snow microphysics model. Default: False.

``--use_extra_snow_layers``
  Turn on extra snow layers. Default: False.

``--use_firn_percolation_and_compaction``
  Turn on firn percolation and compaction. Default: False.

**Topounit Options**

``--topounits_atmdownscale``
  Use atmospheric downscaling in topounits. Default: False.

``--topounits_raddownscale``
  Use radiation downscaling in topounits. Default: False.

**Polygonal Tundra**

``--use_polygonal_tundra``
  Turn on the polygonal tundra parameterizations (NGEE Arctic Phase 3 IM1). Default: False.

``--unified_polygonal_tundra``
  Use unified polygonal tundra parameterization across all topounits. Default: False.

**Cold Initialization**

``--use_arctic_init``
  Use colder and saturated initial conditions (NGEE Arctic IM2 and IM0). Default: False.

**IM2 Hillslope Hydrology**

``--use_IM2_hillslope_hydrology``
  Use IM2 hillslope hydrology parameterization. Default: False.

**Output Options**

``--arctic_topounit_output``
  Activate topounit-level and PFT-level outputs by turning on ``hist_dov2xy``. Default: False.

**Phenology**

``--use_onset_gdd_extension``
  Extend leaf onset based on accumulated growing degree days past summer solstice in Arctic. Default: False.


User-Defined PFT Options
-------------------------

``--maxpatch_pft <int>``
  User-defined max. patch PFT number. Default: 17.

``--landusefile <path>``
  User-defined dynamic PFT file. Default: empty.

``--var_list_pft <string>``
  Comma-separated list of vars to output at PFT level. Default: empty.


Workflow
========

Three-Phase Simulation Sequence
--------------------------------

1. **AD Spinup** (Accelerated Decomposition)

   - Compset: ``I1850<nutrients><decomp>`` (or ``ICB1850<nutrients><decomp>`` with ``--cpl_bypass``)
   - Duration: ``--nyears_ad_spinup`` (default: 250 years, adjusted to a multiple of the met cycle)
   - Purpose: Rapidly equilibrate soil carbon pools by accelerating decomposition rates
   - Nutrients: CN mode by default; CNP if ``--ad_Pinit`` is set
   - Met cycle: 1901–1920 (for gridded forcing) or site-specific years (for tower forcing)
   - Skipped if ``--noad`` is set

2. **Final Spinup**

   - Compset: ``I1850<nutrients><decomp>`` (or ``ICB1850<nutrients><decomp>`` with ``--cpl_bypass``)
   - Duration: ``--nyears_final_spinup`` (default: 200 years, adjusted to a multiple of the met cycle)
   - Purpose: Equilibrate biomass and nutrient pools at normal decomposition rates
   - Nutrients: CNP mode (unless ``--cn_only`` or ``--c_only`` is set)
   - Initial conditions: Restart from AD spinup (year ``nyears_ad_spinup + 1``)
   - Skipped if ``--nofnsp`` is set

3. **Transient**

   - Compset: ``I20TR<nutrients><decomp>`` (or ``ICB20TR<nutrients><decomp>`` with ``--cpl_bypass``)
   - Duration: ``--nyears_transient`` (default: 1850 to end of available forcing)
   - Purpose: Historical simulation with prescribed forcing, land use, and CO2
   - Initial conditions: Restart from final spinup (year ``nyears_final_spinup + 1``)
   - Skipped if ``--notrans`` is set


Multi-Site Execution
--------------------

When ``--site`` is a comma-delimited list (``US-Brw,US-NR1``) or ``all``:

- The **first site** is built using ``runcase.py`` for each phase.
- **Subsequent sites** are cloned from the first site using ``case_copy.py``, which:

  - Copies the case directory structure
  - Patches site-specific files (domain, surface data, met forcing)
  - Reuses the executable from the first site (avoids rebuilding)
  - Is significantly faster than calling ``runcase.py`` for each site

The ``firstsite`` variable (and ``ad_case_firstsite``, ``fin_case_firstsite``, ``tr_case_firstsite``) tracks the first site's case names for cloning.


eCO2 Experiments
----------------

When ``--eco2_file <filename>`` is set, ``site_fullrun.py`` spawns **three** transient simulations:

1. **Standard historical** (1850 to ``startyear - 1``): Uses ``--co2_file``
2. **Ambient CO2 (aCO2)**: ``ncycle`` years starting at ``startyear``, uses ``--co2_file``
3. **Elevated CO2 (eCO2)**: ``ncycle`` years starting at ``startyear``, uses ``--eco2_file``

This workflow supports CO2 manipulation experiments (e.g., FACE sites). The aCO2 and eCO2 runs are initialized from the same restart file (end of the standard historical transient).


Site Metadata
-------------

Site metadata is read from ``inputdata/lnd/clm2/PTCLM/<sitegroup>_sitedata.txt``. Each row contains:

- Site code (e.g., ``US-Brw``)
- Lat/lon
- PFT
- Start/end year of available tower forcing
- Timezone (for diagnostics)

The ``--sitegroup`` flag selects which file to read (default: ``AmeriFlux``; CI uses ``NGEEArctic``). To add a new site, append a row to the appropriate ``_sitedata.txt`` (and matching ``_pftdata.txt`` / ``_soildata.txt``).


Submission Behavior
-------------------

- **On machines with schedulers** (``cades``, ``anvil``, ``chrysalis``, ``compy``, ``cori``): ``site_fullrun.py`` builds PBS/SLURM submission scripts in ``./scripts/<caseidprefix>/`` and submits them in dependency order (AD spinup → final spinup → transient). Each script contains a ``case.submit --no-batch &`` call for the first site or a direct executable invocation for subsequent sites.

- **On machines without schedulers** (``docker``, ``ubuntu``, ``mac``): ``runcase.py`` directly calls ``./case.submit`` (which runs the model immediately).

- **With ``--no_submit``**: Cases are built but not submitted.


Examples
========

Basic Single-Site Run
---------------------

Run US-Brw from the NGEEArctic sitegroup with GSWP3 forcing::

    python site_fullrun.py \
        --site US-Brw \
        --sitegroup NGEEArctic \
        --caseidprefix test_brw \
        --model_root /path/to/E3SM \
        --ccsm_input /path/to/inputdata \
        --machine cades \
        --compiler gnu \
        --mpilib openmpi \
        --cpl_bypass \
        --gswp3

Multi-Site Run
--------------

Run three sites concurrently::

    python site_fullrun.py \
        --site US-Brw,US-NR1,US-Ivo \
        --sitegroup NGEEArctic \
        --caseidprefix multisite \
        --model_root /path/to/E3SM \
        --ccsm_input /path/to/inputdata \
        --machine cades \
        --cpl_bypass \
        --gswp3

Spinup-Only Run
---------------

Skip the transient phase::

    python site_fullrun.py \
        --site US-Brw \
        --sitegroup NGEEArctic \
        --caseidprefix spinup_only \
        --notrans \
        --nyears_ad_spinup 200 \
        --nyears_final_spinup 400 \
        --model_root /path/to/E3SM \
        --ccsm_input /path/to/inputdata \
        --machine cades \
        --cpl_bypass \
        --gswp3

Marsh Site with User-Provided Surface Data
-------------------------------------------

(from ``examples/site_fullrun_marsh_example.sh``)::

    python site_fullrun.py \
        --site US-GC3 \
        --sitegroup Wetland \
        --caseidprefix Test2Col \
        --nyears_ad_spinup 200 \
        --nyears_final_spinup 600 \
        --tstep 1 \
        --cpl_bypass \
        --machine cades \
        --compiler gnu \
        --mpilib openmpi \
        --gswp3 \
        --model_root /lustre/or-hydra/cades-ccsi/f9y/models/E3SM \
        --caseroot /lustre/or-hydra/cades-ccsi/f9y/cases \
        --ccsm_input /lustre/or-hydra/cades-ccsi/proj-shared/project_acme/ACME_inputdata \
        --runroot /lustre/or-hydra/cades-ccsi/scratch/f9y \
        --spinup_vars \
        --marsh \
        --np 2 \
        --nopointdata \
        --domainfile /path/to/domain.lnd.2x1pt_US-GC3_navy_vji.nc \
        --surffile /path/to/surfdata_2x1pt_US-GC3_simyr1850.nc \
        --landusefile /path/to/surfdata.pftdyn_2x1pt_US-GC3_simyr1850-2015.nc

User-Provided Met Forcing
--------------------------

(from ``examples/site_fullrun_userdata_example.sh``)::

    python site_fullrun.py \
        --site AK-K64G \
        --sitegroup NGEEArctic \
        --caseidprefix TestOMLT \
        --nyears_ad_spinup 200 \
        --nyears_final_spinup 600 \
        --tstep 1 \
        --machine mymac \
        --compiler gnu \
        --mpilib mpich \
        --cpl_bypass \
        --model_root /Users/f9y/mygithub/e3sm \
        --caseroot /Users/f9y/project_acme/cases \
        --ccsm_input /Users/f9y/mygithub/pt-e3sm-inputdata \
        --runroot /Users/f9y/project_acme/scratch \
        --spinup_vars \
        --nopointdata \
        --metdir /path/to/cpl_bypass_full \
        --domainfile /path/to/domain.lnd.1x1pt_kougarok-GRID_navy.nc \
        --surffile /path/to/surfdata_1x1pt_kougarok-GRID_simyr1850_c360x720_171002.nc \
        --landusefile /path/to/landuse.timeseries_1x1pt_kougarok-GRID_simyr1850-2015_c180423.nc

eCO2 Manipulation Experiment
-----------------------------

Run a FACE-style experiment with ambient and elevated CO2::

    python site_fullrun.py \
        --site US-ORv \
        --sitegroup AmeriFlux \
        --caseidprefix face_exp \
        --model_root /path/to/E3SM \
        --ccsm_input /path/to/inputdata \
        --machine cades \
        --cpl_bypass \
        --gswp3 \
        --co2_file fco2_datm_historical_0.9x1.25_c130312.nc \
        --eco2_file fco2_datm_rcp8.5_0.9x1.25_c130312.nc

This will create three transient cases:

- ``<caseidprefix>_US-ORv_ICB20TRCNPRDCTCBC`` (historical, 1850–2000)
- ``<caseidprefix>_US-ORv_ICB20TRCNPRDCTCBC_aCO2`` (ambient CO2, 2001–2020)
- ``<caseidprefix>_US-ORv_ICB20TRCNPRDCTCBC_eCO2`` (elevated CO2, 2001–2020)


See Also
========

- ``runcase.py`` — Low-level script that builds a single CIME case
- ``case_copy.py`` — Clones an existing case for a new site
- ``makepointdata.py`` — Generates domain/surface/landuse files for a site
- ``manage_ensemble.py`` — MPI-driven ensemble execution
- ``global_fullrun.py`` — Global/regional simulation entry point
