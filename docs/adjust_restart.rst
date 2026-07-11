adjust_restart.py
==================

Purpose
-------

``adjust_restart.py`` modifies ELM/CLM restart files to replace accelerated pool values with mean values from the last meteorological cycle. This adjustment brings accelerated pools (coarse woody debris, dead stem/coarse root, and soil C/N/P pools) more into line with expected equilibrium results after accelerated decomposition spinup.

The script can also apply a 95% above-ground harvest to vegetation pools, useful for disturbance-recovery experiments.

Command-Line Arguments
----------------------

.. option:: --rundir <path>

   Location of the run directory containing restart and history files.

.. option:: --casename <name>

   Name of the CIME case. Used to construct file paths.

.. option:: --restart_year <year>

   Year of the restart file to modify (e.g., ``0600`` for year 600). If not provided, the script automatically selects the most recent restart file in ``rundir`` matching the case name and model name pattern.

.. option:: --BGC

   Flag indicating a BGC compset. Controls which soil pool variables are modified:

   - **Without** ``--BGC``: modifies SOIL4 and SOIL3 C/N/P pools
   - **With** ``--BGC``: modifies SOIL3 and SOIL2 C/N/P pools (SOIL4 not used in BGC mode)

   If ``"BGC"`` appears in the case name, this flag is set automatically.

.. option:: --harvest

   Apply a 95% above-ground harvest. Multiplies vegetation C/N/P state variables (stem, leaf, coarse root, storage pools) by 0.05, with custom resets for ``LEAFC``, ``FROOTC``, ``LEAFN``, and ``FROOTN`` to simulate post-harvest regrowth initial conditions.

.. option:: --model_name <name>

   Model name used in restart file naming convention. Default is ``clm2``; use ``elm`` for E3SM runs.

Use Cases
---------

Post-spinup pool adjustment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After accelerated decomposition spinup, call ``adjust_restart.py`` to replace accelerated pool state variables with their cycle-mean values from the final spinup history file::

    python adjust_restart.py --rundir /path/to/case/run --casename CASE_NAME \
        --restart_year 0600 --model_name elm

This reads the restart file ``CASE_NAME.elm.r.0600-01-01-00000.nc`` and the matching history file ``CASE_NAME.elm.h1.0600-01-01-00000.nc``, then overwrites accelerated pool variables in the restart file with time-averaged values from the history file.

Harvest disturbance experiment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To simulate a harvest event at the end of spinup::

    python adjust_restart.py --rundir /path/to/case/run --casename CASE_NAME \
        --restart_year 0600 --model_name elm --harvest

This reduces above-ground vegetation pools by 95%, leaving 5% residual biomass.

NetCDF Modifications Applied
-----------------------------

The script modifies variables in place in the restart file ``<casename>.<model_name>.r.<year>-01-01-00000.nc``. A read-only backup is saved as ``<file>.orig`` before any modifications.

Standard pool adjustment (without --harvest)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replaces restart values with cycle-mean values from the corresponding ``.h1.`` history file, but **only** where the restart value is positive and the history value is within valid bounds (``0.001 < hist_val < 1e10``).

**1D variables (column-level):**

- ``DEADSTEMC``, ``DEADSTEMN``, ``DEADSTEMP``
- ``DEADCROOTC``, ``DEADCROOTN``, ``DEADCROOTP``

**2D variables (column × soil-layer):**

- ``CWDC_vr``, ``CWDN_vr``, ``CWDP_vr`` (coarse woody debris)
- Non-BGC mode: ``SOIL4C_vr``, ``SOIL4N_vr``, ``SOIL4P_vr``, ``SOIL3C_vr``, ``SOIL3N_vr``, ``SOIL3P_vr``
- BGC mode (``--BGC``): ``SOIL3C_vr``, ``SOIL3N_vr``, ``SOIL3P_vr``, ``SOIL2C_vr``, ``SOIL2N_vr``, ``SOIL2P_vr``

For 2D variables, the replacement is applied over the first 10 vertical soil layers, subject to the same positivity and bounds checks.

Harvest adjustment (with --harvest)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Multiplies the following restart variables by **0.05** (5% retention):

- Stem: ``DEADSTEMC``, ``DEADSTEMN``, ``DEADSTEMP``, ``LIVESTEMN``, ``LIVESTEMC``, ``LIVESTEMP``
- Leaf: ``LEAFC``, ``LEAFN``, ``LEAFP``
- Fine root: ``FROOTC``, ``FROOTN``, ``FROOTP``
- Coarse root: ``LIVECROOTC``, ``LIVECROOTN``, ``LIVECROOTP``, ``DEADCROOTC``, ``DEADCROOTN``, ``DEADCROOTP``
- Storage pools: all ``*_STORAGE`` variants of the above
- Respiration pools: ``XSMRPOOL``, ``XSMRPOOL_RECOVER``

**Special overrides** (hard-coded values, not 5% scaling):

- ``LEAFC`` → ``0.33 / 0.03`` = 11.0
- ``FROOTC`` → ``0.33 / 0.03 * 0.666`` ≈ 7.33
- ``LEAFN`` → ``0.33 / 0.03 / 25.0`` = 0.44
- ``FROOTN`` → ``0.33 / 0.03 / 42.0`` ≈ 0.26

These represent minimal post-harvest leaf and fine-root biomass for regrowth initialization.

Notes
-----

- Variable names in the restart file are **lowercase**; the script downcases all variable names before calling ``nffun.putvar()``.
- The script expects an ``.h1.`` history file at the same timestamp as the restart file. If this file is missing, the script will fail when attempting to read history variables.
- Commented-out ``ncap2`` commands at the end (lines 214–217) suggest legacy workarounds for negative P-pool values and dimension re-definition; these are not active.
