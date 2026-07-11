ensemble_copy.py
=================

Purpose
-------

``ensemble_copy.py`` clones a pre-built parent ELM/CLM case to create individual ensemble members for uncertainty quantification (UQ) workflows. It replicates the parent case's run directory structure, creates per-member parameter files, and applies parameter perturbations from an ensemble sample file or a temporary ``parm_data`` file.

This script is designed for **single-point, MPI-serial cases only** and is typically invoked by ``manage_ensemble.py`` for each ensemble member in a distributed UQ run.

Command-line Arguments
----------------------

Required or Commonly Used
~~~~~~~~~~~~~~~~~~~~~~~~~

``--case <name>``
    Name of the parent case to clone. The parent case must already be built and have all namelists in its run directory.

``--ens_num <integer>``
    Ensemble member number (default: 1). Used to generate the member-specific subdirectory name ``g<ens_num>`` under ``<runroot>/UQ/<case>/``.

``--ens_file <path>``
    Path to a samples file containing parameter values for all ensemble members (one row per member, whitespace-separated columns). If omitted, reads from a temporary ``./parm_data`` file (which is then deleted).

``--parm_list <path>``
    File listing parameters to vary (default: ``parm_list``). Format: ``<parameter_name> [<pft_index>] <min> <max>`` (one line per parameter). The script reads parameter names and PFT indices from this file.

Optional
~~~~~~~~

``--runroot <path>``
    Directory where the parent case resides (default: ``../../run``). The cloned ensemble member will be created at ``<runroot>/UQ/<case>/g<ens_num>/``.

``--site <name>``
    Site name (default: ``parm_list``). Currently not actively used in the script logic.

``--cnp``
    Flag indicating CNP mode. When set, initializes phosphorus pools and handles CNP-specific parameter files (``fsoilordercon``).

``--model_name <clm2|elm>``
    Model name used in restart file naming (default: ``clm2``). Determines the restart file pattern (``*.clm2.r.*.nc`` or ``*.elm.r.*.nc``).

What It Does
------------

1. **Creates member directory structure**: ``<runroot>/UQ/<case>/g<ens_num>/run`` with timing/checkpoints subdirs.

2. **Copies parent case files**: namelists (``*_in*``, ``*.nml``), streams (``*stream*``), resource files (``*.rc``), domain/surface files (``surf*.nc``, ``domain*.nc``), and parameter files (``*para*.nc``).

3. **Patches namelists and paths**: replaces parent directory paths with the new ensemble member directory, adjusts logfile timestamps, and creates member-specific copies of parameter files (``clm_params_<ens_num>.nc``, ``fates_params_<ens_num>.nc``, ``CNP_parameters_<ens_num>.nc``, ``surfdata_<ens_num>.nc``).

4. **Applies parameter perturbations**: reads parameter values from ``--ens_file`` (row matching ``--ens_num``) or ``./parm_data``, then writes them into the member-specific parameter NetCDF files. Handles scalar parameters (e.g., ``flnr``), PFT-indexed parameters, FATES 2D parameters, CNP parameters, and special cases like ``lai`` (monthly) and ``co2_ppmv`` (namelist).

5. **Handles restart file continuity**: for spin-up chains (ad_spinup → 1850 → transient), attempts to locate restart files from prior ensemble phases under ``<runroot>/UQ/<prior_case>/g<ens_num>/`` and copies them to the new member directory.

Relationship to ``case_copy.py``
---------------------------------

Both scripts clone a pre-built case, but serve different purposes:

- **ensemble_copy.py**: clones a single-point case for UQ/ensemble workflows. Creates the member under ``<runroot>/UQ/<case>/g<ens_num>/``, applies parameter perturbations from a samples file, and handles restart file continuity across spin-up phases for the same ensemble member.

- **case_copy.py**: clones a case for **multi-site** single-case workflows. Used by ``site_fullrun.py`` to replicate the first site's run directory for additional sites, avoiding the need to rebuild. Patches site-specific metadata (domain/surface files, lat/lon/PFT) but does not apply parameter perturbations or create a ``UQ/`` subdirectory.

In short: ``ensemble_copy.py`` is for UQ ensembles (same site, many parameter sets); ``case_copy.py`` is for multi-site single-configuration runs (many sites, same parameters).

When to Use vs ``ensemble_run.py``
-----------------------------------

- **ensemble_copy.py**: use when you already have a pre-built parent case and need to create a cloned ensemble member. This script only sets up the member directory and applies parameter perturbations; it does **not** submit or execute the case.

- **ensemble_run.py**: use for the **full ensemble member workflow**: calls ``ensemble_copy.py`` internally to clone the parent case, then submits the case, monitors execution, and performs post-processing (calculates sum-of-squared-errors against observational constraints in the ``constraints/`` directory). ``ensemble_run.py`` is the higher-level driver for a single ensemble member.

Typical invocation flow::

    manage_ensemble.py (MPI master)
      └─> ensemble_run.py (per-member, rank N)
            ├─> ensemble_copy.py --case <parent> --ens_num N --ens_file <samples>
            ├─> case.submit (CIME)
            └─> postproc (SSE calculation)

If you only need to set up member directories without running them, invoke ``ensemble_copy.py`` directly.

Constraints
-----------

- Parent case must be **single-point** and compiled with **MPI_SERIAL**.
- Parent case must be fully built with namelists in the run directory before cloning.
- ``--ens_file`` or ``./parm_data`` must provide parameter values in the same order as ``--parm_list``.
- Restart file continuity logic is case-name-dependent (looks for substrings like ``1850``, ``20TR``, ``_trans``, ``ad_spinup``, ``CROP``, ``CO2``) — ensure case naming follows OLMT conventions for spin-up chains.

Example Usage
-------------

Clone parent case ``US-Brw_I1850CRUCLM50BGC`` to create ensemble member 5 using parameter values from row 5 of ``samples_lhs.txt``::

    python ensemble_copy.py \
        --runroot /scratch/runs \
        --case US-Brw_I1850CRUCLM50BGC \
        --ens_num 5 \
        --ens_file samples_lhs.txt \
        --parm_list parm_list_bgc \
        --model_name elm

This creates ``/scratch/runs/UQ/US-Brw_I1850CRUCLM50BGC/g00005/`` with parameter perturbations applied to ``elm_params_00005.nc``, ``fates_params_00005.nc``, etc.

See Also
--------

- ``ensemble_run.py``: higher-level driver that invokes ``ensemble_copy.py`` then submits and post-processes the member
- ``manage_ensemble.py``: MPI-based ensemble orchestrator that distributes members across ranks
- ``case_copy.py``: multi-site case cloning (not for UQ ensembles)
- ``parm_list`` format: documented in ``examples/parm_list*`` files
- ``postproc_vars`` format: documented in ``examples/postproc_vars_example``
