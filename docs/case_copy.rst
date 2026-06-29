``case_copy.py``
================

Purpose
-------

``case_copy.py`` clones a pre-built CIME case for additional sites without triggering a full rebuild. It is the key optimization that allows OLMT to run multi-site experiments efficiently: the first site goes through the full ``runcase.py`` path (``create_newcase``, ``case.setup``, ``case.build``, ``case.submit``), while every subsequent site reuses the same compiled executable and only patches site-specific configuration files.

**Performance benefit**: Avoids the ~10–30 minute model rebuild per site. For a 10-site experiment, this reduces total setup time from hours to minutes.

Command-line arguments
----------------------

.. option:: --runroot <path>

   Root directory containing CIME case run directories. Default: ``../../run``

.. option:: --case_copy <name>

   Name of the parent case to clone from (required).

.. option:: --site_orig <code>

   Site code used in the original case (required for path/file substitution).

.. option:: --site_new <code>

   Site code for the new case (required).

.. option:: --nyears <int>

   Number of years to run. Patches ``stop_n`` and ``restart_n`` in ``drv_in``. Default: 0 (no change).

.. option:: --finidat_year <int>

   Year for the restart file (``finidat``). Patches the year suffix in ``lnd_in``. Default: 0 (no change).

.. option:: --finidat_thiscase

   Use restart file from this case's directory (flag).

.. option:: --spin_cycle <int>

   Number of years in spinup cycle. Adjusts ``hist_nhtfrq`` to write one history file per cycle. Default: 0 (no change).

.. option:: --1850_landuse

   Disable transient land use (sets ``flanduse_timeseries = ''``, ``do_transient_pfts = .false.``, ``do_harvest = .false.``).

.. option:: --1850_co2

   Use constant 1850 CO2 (replaces ``co2_file`` with ``*_CON.nc`` variant).

.. option:: --1850_ndep

   Use constant 1850 nitrogen deposition (replaces ``stream_fldfilename_ndep`` with ``*_CON.nc`` variant).

.. option:: --suffix <string>

   Append a suffix to the new case name (e.g., ``_eCO2``). Used for parallel aCO2/eCO2 transient pairs.

.. option:: --machine <name>

   Target machine name (affects PBS/SLURM submission logic). Default: ``cades``

.. option:: --warming <float>

   Warming level to apply (not actively used in patching logic). Default: ``0.0``

.. option:: --tempdir <path>

   Staging directory for intermediate files (``surfdata.nc``, ``domain.nc``, etc.). Defaults to ``./temp/run_<pid>_<ms>/``.

How site_fullrun.py uses it
----------------------------

``site_fullrun.py`` employs the "firstsite pattern":

1. **First site** (``firstsite`` variable):

   - Calls ``runcase.py`` for each of the three BGC phases (ad_spinup, final spinup, transient).
   - ``runcase.py`` invokes ``create_newcase``, ``case.setup``, ``case.build``, and optionally ``case.submit``.
   - Full build happens here (~10–30 minutes depending on machine/compiler).

2. **Subsequent sites** (all others in the ``--site`` comma-list or ``all``):

   - Calls ``case_copy.py`` for each phase, passing the first site's case name via ``--case_copy`` and the new site code via ``--site_new``.
   - ``case_copy.py`` shells out to ``makepointdata.py`` (via the parent ``site_fullrun.py`` logic) to generate new ``surfdata.nc``, ``domain.nc``, and landuse NetCDF files in ``tempdir``.
   - Copies namelists and configuration from the first site's run directory and patches them in place.
   - **No rebuild occurs**: the same executable (``e3sm.exe`` / ``cesm.exe``) is reused.

The firstsite case name is tracked in ``site_fullrun.py`` variables like ``ad_case_firstsite``, ``fnsp_case_firstsite``, ``transient_case_firstsite``.

What gets copied vs patched
----------------------------

**Copied from** ``<runroot>/<case_copy>/run/``:

- All ``*_in*`` files (``atm_in``, ``lnd_in``, ``drv_in``, etc.)
- All ``*nml`` files (namelist files)
- All ``*stream*`` files (DATM streams, except for ``ICB`` cases)
- All ``*.rc`` files (NUOPC run-sequence config)
- All ``*para*.nc`` files (parameter perturbation NetCDF for ensemble runs)

**Patched in place** (text substitution via Python ``open()``/``write()``):

- ``site_orig`` → ``site_new`` in all namelists and streams
- ``casename`` → ``casename_<suffix>`` if ``--suffix`` is provided
- ``stop_n`` and ``restart_n`` in ``drv_in`` if ``--nyears`` > 0
- ``finidat`` year suffix in ``lnd_in`` if ``--finidat_year`` > 0
- ``hist_nhtfrq`` in ``lnd_in`` if ``--spin_cycle`` > 0 (writes one file per cycle)
- ``flanduse_timeseries``, ``do_transient_pfts``, ``do_harvest`` if ``--1850_landuse``
- ``co2_file`` path if ``--1850_co2``
- ``stream_fldfilename_ndep`` path if ``--1850_ndep``

**Copied from** ``tempdir/`` **(newly generated via makepointdata.py)**:

- ``surfdata.nc``
- ``domain.nc``
- ``*pftdyn*.nc`` (landuse timeseries, only for ``20TR`` transient cases)

**Not copied**:

- ``*.nc`` history/restart files (explicitly deleted: ``rm <new_dir>/*.nc``)
- Executable (reused from original build location via ``diri`` in ``lnd_in``)
- ``CaseDocs/``, ``bld/``, ``Buildconf/`` (not needed — no rebuild)

Performance benefit over runcase.py
------------------------------------

**Time savings**:

+------------------------+----------------+-------------------+
| Phase                  | ``runcase.py`` | ``case_copy.py``  |
+========================+================+===================+
| ``create_newcase``     | ~10 sec        | 0 (skipped)       |
+------------------------+----------------+-------------------+
| ``case.setup``         | ~5 sec         | 0 (skipped)       |
+------------------------+----------------+-------------------+
| ``case.build``         | **10–30 min**  | **0 (skipped)**   |
+------------------------+----------------+-------------------+
| Namelist patching      | ~2 sec         | ~2 sec            |
+------------------------+----------------+-------------------+
| **Total**              | **10–30 min**  | **~30 sec**       |
+------------------------+----------------+-------------------+

For an ``N``-site experiment:

- **With** ``case_copy.py``: 1 × (10–30 min) + (N−1) × 30 sec
- **Without**: N × (10–30 min)

At 10 sites, this is **~10 minutes vs. ~100–300 minutes**.

Constraints
-----------

- **Single-point only**: Works only for single-point CLM/ELM cases compiled with ``MPI_SERIAL``. Regional/global cases cannot be cloned this way because their executable and decomposition are grid-dependent.
- **Pre-built parent required**: The ``--case_copy`` case must have completed ``case.build`` and have all namelists written to ``<runroot>/<case_copy>/run/``.
- **Same model version**: The cloned case reuses the same E3SM/CESM source tree and inputdata. Switching model versions requires a new ``runcase.py`` invocation.

See also
--------

- :doc:`runcase` — Full case creation path (first site)
- :doc:`site_fullrun` — Orchestration script that calls ``case_copy.py``
- :doc:`makepointdata` — Generates site-specific ``surfdata.nc`` / ``domain.nc`` for the new site
