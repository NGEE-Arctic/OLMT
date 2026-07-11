User Guide
==========

OLMT (Offline Land Model Testbed) automates ELM and CLM/CTSM simulations at single sites, groups of sites, user-defined regions, or global scales. It orchestrates the standard three-phase BGC simulation workflow on top of E3SM/CIME.

Getting Started
---------------

**OLMT is not a Python package.** Every script is a standalone executable invoked via ``python ./script.py ...`` from the repository root. Scripts import each other by name, so always run them from the repo root.

**Prerequisites:**

1. Working E3SM or CESM/CTSM source tree (passed via ``--model_root``)
2. CIME inputdata directory (passed via ``--ccsm_input``)
3. Python 3 with ``netCDF4``, ``numpy``, ``scipy`` (see ``requirements.txt``)
4. ``mpi4py`` only needed for ensemble workflows (``manage_ensemble.py``)

**Installation:**

.. code-block:: bash

   git clone https://github.com/NGEE-Arctic/OLMT.git
   cd OLMT
   pip install -r requirements.txt

Three-Phase BGC Workflow
-------------------------

OLMT's core abstraction is the standard ELM/CLM BGC spinup sequence:

1. **AD Spinup** — Accelerated decomposition spinup (Thornton and Rosenbloom, 2005)
2. **Final Spinup** — Equilibrate biomass and nutrient pools
3. **Transient** — 1850–present with prescribed forcing, land use, CO2

``site_fullrun.py`` (single sites) and ``global_fullrun.py`` (regional/global) orchestrate this sequence by calling ``runcase.py`` for each phase.

**Skip phases with flags:**

- ``--noad`` — skip AD spinup
- ``--nofnsp`` — skip final spinup
- ``--notrans`` — skip transient

Entry Points
------------

Single-Site Simulations
~~~~~~~~~~~~~~~~~~~~~~~

Use ``site_fullrun.py`` for point-location runs:

.. code-block:: bash

   python ./site_fullrun.py \\
       --site US-UMB \\
       --sitegroup AmeriFlux \\
       --caseidprefix test \\
       --model_root /path/to/E3SM \\
       --ccsm_input /path/to/inputdata \\
       --runroot /path/to/scratch \\
       --gswp3

**Key arguments:**

- ``--site`` — site code from ``inputdata/PTCLM/<sitegroup>_sitedata.txt`` (or comma-list, or ``all``)
- ``--sitegroup`` — lookup table name (``AmeriFlux``, ``NGEEArctic``)
- ``--gswp3`` / ``--era5`` / ``--cruncep`` — forcing source (controls 1901–1920 spinup cycle and transient end year)
- ``--machine`` — CIME machine name (``docker``, ``compy``, ``anvil``, etc.)

See :doc:`site_fullrun` for full reference.

Regional and Global Simulations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``global_fullrun.py`` for gridded runs:

.. code-block:: bash

   python ./global_fullrun.py \\
       --caseidprefix global_test \\
       --model_root /path/to/E3SM \\
       --ccsm_input /path/to/inputdata \\
       --runroot /path/to/scratch \\
       --res hcru_hcru \\
       --region arctic

**Key arguments:**

- ``--res`` — grid resolution (``hcru_hcru``, ``1x1_brazil``, etc.)
- ``--region`` — pre-defined region (``arctic``, ``tropics``, ``global``) or custom via ``--lat_bounds``/``--lon_bounds``
- ``--run_startyear`` / ``--run_n`` / ``--run_units`` — simulation length

See :doc:`global_fullrun` for full reference.

Site Metadata
-------------

Site lookup tables live in ``inputdata/PTCLM/<sitegroup>_sitedata.txt``. Each row defines:

- Site code
- Latitude/longitude
- PFT composition (from ``<sitegroup>_pftdata.txt``)
- Soil texture (from ``<sitegroup>_soildata.txt``)
- Valid year range for forcing/observations

**Add a new site:** Append a row to ``_sitedata.txt``, ``_pftdata.txt``, and ``_soildata.txt``.

**Example line from** ``AmeriFlux_sitedata.txt``::

   US-UMB  45.56  -84.71  2000  2010  1  1  1  ...

Meteorological Forcing
----------------------

Forcing sources are selected via mutually-exclusive flags:

.. list-table::
   :header-rows: 1
   :widths: 20 30 20

   * - Flag
     - Source
     - Transient End Year
   * - ``--gswp3``
     - GSWP3
     - 2014
   * - ``--gswp3_w5e5``
     - GSWP3-W5E5
     - 2019
   * - ``--era5``
     - ERA5
     - 2016
   * - ``--cruncep``
     - CRU-NCEP (v4)
     - 2016
   * - ``--cruncepv8``
     - CRU-NCEP (v8)
     - 2016
   * - ``--princeton``
     - Princeton
     - 2012
   * - ``--crujra``
     - CRU-JRA
     - 2022
   * - ``--trendy25``
     - TRENDY v2.5
     - 2023

All sources use a 1901–1920 spinup cycle.

**ERA5 cpl_bypass mode:** ERA5 simulations use ``--cpl_bypass`` (direct DATM→ELM coupling) and require ``srcmods_era5cb/src.elm/lnd_import_export.F90`` passed via ``--srcmods_loc``.

eCO2 Manipulation Experiments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``--eco2_file <path>`` adds parallel transient cases for CO2 manipulation:

- ``<caseid>_ICB1850CNECACBC_transient`` — ambient CO2 (aCO2)
- ``<caseid>_ICB1850CNECACBC_transient_eCO2`` — elevated CO2 (eCO2)
- ``<caseid>_ICB1850CNECACBC_transient_e2xCO2`` — 2× CO2

See :doc:`site_fullrun` examples.

Multi-Site Execution
--------------------

``site_fullrun.py`` optimizes multi-site runs via the **firstsite cloning pattern**:

1. Build the first site via ``runcase.py`` (10–30 minutes)
2. Clone pre-built case for subsequent sites via ``case_copy.py`` (~1 minute each)

**Example (3 sites):**

.. code-block:: bash

   python ./site_fullrun.py \\
       --site US-UMB,US-Syv,US-WCr \\
       --sitegroup AmeriFlux \\
       --caseidprefix multi \\
       --model_root /path/to/E3SM \\
       --ccsm_input /path/to/inputdata \\
       --runroot /scratch \\
       --gswp3

Total setup: ~12 minutes (10 min first site + 1 min × 2 clones) vs. ~30 minutes serial.

See :doc:`case_copy` for details.

Ensemble and UQ Workflows
--------------------------

OLMT supports parameter perturbation ensembles and uncertainty quantification via ``manage_ensemble.py``.

Parameter Sampling
~~~~~~~~~~~~~~~~~~

**Parameter list format** (``parm_list``)::

   leafcn       0  20.0  40.0
   frootcn      0  40.0  60.0
   q10          0   1.5   3.0

Four whitespace-separated fields: ``name pft min max``. PFT index 0 = broadcast to all PFTs.

**Ensemble sample file:** One row per member, columns match ``parm_list`` order, whitespace-separated::

   25.3  48.2  2.1
   32.1  55.0  2.7
   ...

**Generate samples:** Latin hypercube, Sobol, etc. (external tool, not part of OLMT).

Post-Processing Variable Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Post-processing format** (``postproc_vars``)::

   GPP  H  240  12  2000  2010  0  -  -  gC/m2/day  -  observations.txt

12 fields: ``var hfreq startday nsteps startyear endyear pft depth1 depth2 units constraint_file obs_file``

See ``examples/postproc_vars_example`` for full spec and ``examples/postproc_vars_crop`` for crop-specific variables.

Running an Ensemble
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. Build parent case (single-site, MPI_SERIAL)
   python ./site_fullrun.py \\
       --site US-UMB \\
       --caseidprefix parent \\
       --model_root /path/to/E3SM \\
       --ccsm_input /path/to/inputdata \\
       --runroot /scratch \\
       --gswp3 \\
       --no_submit

   # 2. Run ensemble (MPI distributes members)
   mpirun -np 8 python ./manage_ensemble.py \\
       --case parent_ICB1850CNECACBC \\
       --runroot /scratch \\
       --ens_num 50 \\
       --ens_file samples_lhs_50.txt \\
       --parm_list examples/parm_list_example \\
       --postproc_file examples/postproc_vars_example \\
       --model_root /path/to/E3SM \\
       --ccsm_input /path/to/inputdata

**MPI design:** Rank 0 distributes jobs, ranks 1-N execute members in parallel. Each member runs 250 years of spinup.

**Outputs:**

- ``UQ_output/<case>/data/`` — parameter samples, model outputs, observations
- ``UQ_output/<case>/<member>/`` — per-member run directories

See :doc:`manage_ensemble` for full details.

Surrogate Modeling and Sensitivity Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After ensemble completion, build surrogate and run sensitivity analysis:

.. code-block:: bash

   # 3. Train neural network surrogate
   python ./surrogate_NN.py --case parent_ICB1850CNECACBC

   # 4. Global sensitivity analysis (Sobol indices)
   python ./run_GSA.py --case parent_ICB1850CNECACBC

**Outputs:**

- ``UQ_output/<case>/NN_surrogate/NNmodel.pkl`` — trained surrogate
- ``UQ_output/<case>/SA_output/`` — sensitivity indices, plots

**Alternative:** ``UQTk_scripts/`` for polynomial chaos expansion-based sensitivity (UQTk toolkit required).

See :doc:`surrogate_nn`, :doc:`run_gsa`, :doc:`model_surrogate`.

Bayesian Calibration
~~~~~~~~~~~~~~~~~~~~~

If observations have non-zero uncertainty:

.. code-block:: bash

   python ./MCMC.py \\
       --case parent_ICB1850CNECACBC \\
       --nevals 10000 \\
       --burnsteps 2000

**Outputs:**

- ``UQ_output/<case>/MCMC_output/MCMC_chain.txt`` — full chain
- ``UQ_output/<case>/MCMC_output/best_params.txt`` — MAP estimate
- ``UQ_output/<case>/MCMC_output/credible_intervals.txt`` — 95% CI
- ``UQ_output/<case>/MCMC_output/*.pdf`` — trace plots, marginals

See :doc:`mcmc`.

Visualization
-------------

``plotcase.py`` generates time series, diurnal cycles, seasonal cycles, and spinup plots:

.. code-block:: bash

   python ./plotcase.py \\
       --csmdir /scratch/parent_ICB1850CNECACBC \\
       --vars GPP,NEE,ER \\
       --ystart 2000 \\
       --yend 2010 \\
       --obs

**Key flags:**

- ``--vars`` — comma-separated variable list
- ``--obs`` — overlay FluxNet observations (where available)
- ``--avpd`` — average to diurnal cycle
- ``--noperpage 1`` — one variable per page

See :doc:`plotcase`.

Utilities
---------

Adjust Restart Files
~~~~~~~~~~~~~~~~~~~~

``adjust_restart.py`` replaces accelerated spinup pool values with cycle-mean values from history files:

.. code-block:: bash

   python ./adjust_restart.py \\
       --rundir /scratch/test_ICB1850CNECACBC_ad_spinup/run \\
       --casename test_ICB1850CNECACBC_ad_spinup

Used internally by ``site_fullrun.py`` between AD and final spinup. See :doc:`adjust_restart`.

Compare Cases
~~~~~~~~~~~~~

``compare_cases.py`` verifies input files and history outputs are identical:

.. code-block:: bash

   python ./compare_cases.py \\
       --runroot /scratch \\
       --cases case1,case2

See :doc:`compare_cases`.

GUI
~~~

``OLMT_GUI.py`` provides a wxPython GUI wrapper around ``site_fullrun.py``:

.. code-block:: bash

   python ./OLMT_GUI.py

Limited functionality vs. command-line. See :doc:`gui`.

Advanced Topics
---------------

Source Modifications
~~~~~~~~~~~~~~~~~~~~

``--srcmods_loc`` copies Fortran sources into the case before build:

.. code-block:: bash

   python ./site_fullrun.py \\
       --site US-UMB \\
       --srcmods_loc /path/to/srcmods_era5cb \\
       --era5 \\
       ...

Required for ERA5 cpl_bypass mode. See :doc:`runcase`.

Custom Surface Data
~~~~~~~~~~~~~~~~~~~

``--usersurfnc`` skips ``makepointdata.py`` and uses pre-generated surface files:

.. code-block:: bash

   python ./site_fullrun.py \\
       --site US-UMB \\
       --usersurfnc \\
       --model_root /path/to/E3SM \\
       ...

See :doc:`makepointdata`.

NGEE Arctic Extensions
~~~~~~~~~~~~~~~~~~~~~~

NGEE Arctic-specific flags:

- ``--C13`` / ``--C14`` — isotope tracers
- ``--MICROBE`` — microbial decomposition model
- ``--humhol`` — hummock/hollow microtopography
- ``--no_trunc`` — disable snow truncation
- ``--regional_pftmerge`` — merge PFT tiles for polygon simulations

See :doc:`site_fullrun` NGEE Arctic section.

Troubleshooting
---------------

CIME create_newcase fails
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Verify ``--model_root`` points to valid E3SM/CESM source
- Check ``--machine`` is defined in CIME's ``config_machines.xml``
- Docker users: ensure ``--machine docker``

Build failures
~~~~~~~~~~~~~~

- Check compiler flags via ``--compiler``
- Verify inputdata completeness (``--ccsm_input``)
- Look in ``<runroot>/<caseid>/bld/``

Submit hangs or fails
~~~~~~~~~~~~~~~~~~~~~

- ``--no_submit`` to skip scheduler submission
- Check PBS/SLURM scripts in ``<runroot>/<caseid>/``
- Docker: requires ``--machine docker`` (skips PBS, runs directly)

MPI errors in ensemble
~~~~~~~~~~~~~~~~~~~~~~

- ``manage_ensemble.py`` requires ``mpi4py``
- Parent case must use ``MPILIB=mpi-serial`` (single-point only)
- Check MPI ranks ≥ 2 (rank 0 = manager)

References
----------

- **E3SM:** https://e3sm.org
- **CIME:** https://esmci.github.io/cime/
- **ELM Technical Note:** Thornton et al. (2007)
- **AD Spinup:** Thornton and Rosenbloom (2005) *JGR-Biogeosciences*
- **OLMT Repository:** https://github.com/NGEE-Arctic/OLMT-unified

Contact
-------

Dan Ricciuto (ricciutodm@ornl.gov)
