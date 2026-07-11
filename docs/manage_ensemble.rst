manage_ensemble.py
==================

Purpose
-------

``manage_ensemble.py`` is an MPI-based ensemble orchestrator that distributes parameter-perturbed land model simulations across compute nodes, executes each ensemble member in parallel, and performs post-processing to extract model output for uncertainty quantification and sensitivity analysis.

It is the MPI driver for ensemble and UQ workflows in OLMT. It does **not** build cases itself — a pre-built parent case (single-point, MPI-serial) must already exist.

MPI Design
----------

The script uses a manager–worker pattern:

- **Rank 0 (manager)**: distributes job numbers to worker ranks, collects post-processed results from each ensemble member, and writes aggregated output files for surrogate modeling / sensitivity analysis.
- **Ranks 1…N (workers)**: receive a job number, invoke ``ensemble_copy.py`` to clone the parent case and apply parameter perturbations, run the model executable, extract and time-average requested variables, and send results back to rank 0.

Each worker processes one ensemble member at a time; once finished it requests another job until all members are complete.

Requirements
------------

- ``mpi4py`` (``pip install mpi4py``)
- A pre-built parent case created by ``runcase.py`` or ``site_fullrun.py`` (single-point only; regional/global cases are not supported)
- Parameter sampling file (``--ens_file``) or Monte Carlo size (``--mc_ensemble``)
- Post-processing specification file (``--postproc_file``) if output extraction is desired

Invocation
----------

Typical usage:

.. code-block:: bash

   mpirun -np 24 python manage_ensemble.py \
       --case US-Brw_ICB20TRCNPRDCTCBC \
       --runroot /path/to/runs \
       --exeroot /path/to/exes \
       --ens_file mcsamples_US-Brw_100.txt \
       --parm_list parm_list_example \
       --postproc_file postproc_vars_example \
       --site US-Brw

This will:

1. Distribute 100 ensemble members across 23 worker ranks (rank 0 is manager).
2. Each worker clones the parent case at ``/path/to/runs/US-Brw_ICB20TRCNPRDCTCBC`` using ``ensemble_copy.py``, applies parameter perturbations from ``mcsamples_US-Brw_100.txt``, and runs the model.
3. After each member completes, extract variables specified in ``postproc_vars_example`` and send results to rank 0.
4. Rank 0 writes ``US-Brw_ICB20TRCNPRDCTCBC_postprocessed.txt`` and prepares UQ-ready outputs in ``UQ_output/US-Brw_ICB20TRCNPRDCTCBC/data/`` (training/validation split, parameter ranges, surrogate inputs).

Command-Line Arguments
----------------------

Ensemble Configuration
~~~~~~~~~~~~~~~~~~~~~~~

``--case CASENAME``
   Name of the pre-built parent case (must exist in ``--runroot``).

``--runroot PATH``
   Directory where cases are created. Default: ``../../run``.

``--exeroot PATH``
   Directory containing the model executable (``e3sm.exe``, ``cesm.exe``, or ``acme.exe``). Default: ``../../run``.

``--n_ensemble N``
   Number of ensemble members. If not specified and ``--ens_file`` is provided, the number of lines in the file is used.

``--ens_file FILE``
   Path to parameter sample file. Each line is one ensemble member; whitespace-separated columns correspond to parameters in ``--parm_list``. If ``--mc_ensemble`` is used and this is omitted, defaults to ``mcsamples_<caseid>_<N>.txt``.

``--mc_ensemble N``
   Create a Monte Carlo ensemble of size N. If ``--ens_file`` is not provided, generates Latin Hypercube samples using parameter ranges from ``--parm_list`` and writes them to ``mcsamples_<caseid>_<N>.txt``.

``--parm_list FILE``
   File specifying parameters to vary. Default: ``parm_list``. See **Parameter List Format** below.

``--site SITECODE``
   Site code (e.g., ``US-Brw``). Passed to ``ensemble_copy.py``; used for site-specific logic in post-processing (e.g., SPRUCE treatments).

``--model_name {clm2,elm}``
   Model name used in restart/history filenames. Default: ``clm2``.

``--cnp``
   CNP mode — initialize phosphorus pools. Passed to ``ensemble_copy.py``.

``--microbe``
   CNP mode with microbe parameters. Changes parameter file lookup to ``microbepar_in`` instead of NetCDF files.

Post-Processing
~~~~~~~~~~~~~~~

``--postproc_file FILE``
   Path to post-processing specification file. If provided, each ensemble member's output is extracted, time-averaged, and sent to rank 0. See **Post-Processing Format** below.

``--postproc_only``
   Skip model execution; only perform post-processing on existing output. Useful for re-extracting variables after ensemble runs are complete.

``--run_uq``
   After post-processing, automatically launch surrogate modeling (``surrogate_NN.py``), global sensitivity analysis (``run_GSA.py``), and MCMC calibration (``MCMC.py``) if observational data is provided. Default: ``True``.

Special Modes
~~~~~~~~~~~~~

``--spruce_treatments``
   Run 11 SPRUCE experimental treatments (ambient + 5 warming levels × {ambient CO₂, elevated CO₂}). Requires the parent case to produce a 2015-01-01 restart file. Each treatment runs in a subdirectory of the ensemble member's run directory.

Parameter List Format (``parm_list``)
--------------------------------------

The parameter list file specifies which model parameters to perturb in the ensemble. Each line has **four whitespace-separated fields**:

.. code-block:: text

   <parameter_name> <pft> <min> <max>

- ``<parameter_name>``: NetCDF variable name in ``clm_params.nc`` (or ``fates_params.nc`` for FATES parameters prefixed with ``fates_``). Special names:

  - ``lai``: reads from ``MONTHLY_LAI`` in the surface data file.
  - ``co2``: reads ``co2_ppm`` from ``lnd_in`` namelist.

- ``<pft>``: Plant functional type (PFT) index. Use ``0`` for scalar parameters, ``>0`` for PFT-indexed parameters, ``-1`` for global.

- ``<min>``, ``<max>``: Parameter bounds for sampling.

Example (``examples/parm_list_example``):

.. code-block:: text

   flnr 7 0.02 0.20
   vcmaxha 7 40000 90000
   jmaxha 7 40000 90000
   roota_par 7 0.5 15
   mbbopt 7 2 13

This defines five parameters, all for PFT 7 (C3 arctic grass), with their valid ranges.

Ensemble Sample File Format (``--ens_file``)
---------------------------------------------

Each line is one ensemble member; columns correspond to parameters in ``--parm_list`` order. Whitespace-separated, no header.

Example (3 members, 5 parameters):

.. code-block:: text

   0.05 55000 60000 5.0 8.0
   0.10 70000 75000 10.0 11.5
   0.15 80000 85000 12.0 12.0

If ``--mc_ensemble`` is used without ``--ens_file``, the script generates Latin Hypercube samples and writes this file automatically.

Post-Processing Format (``postproc_vars``)
------------------------------------------

The post-processing file specifies which model output variables to extract and how to time-average them. Each line (after comment lines starting with ``#``) has **up to 12 whitespace-separated fields**:

.. code-block:: text

   <variable> <year_start> <year_end> <day_start> <day_end> <avg_period> <factor> <offset> [<pft>] [<obs>] [<obs_err>] [<treatment>]

Required Fields
~~~~~~~~~~~~~~~

1. ``<variable>``: NetCDF variable name from model history files (``*.h0.*.nc`` or ``*.h1.*.nc``).
2. ``<year_start>``, ``<year_end>``: Year range to extract (inclusive).
3. ``<day_start>``, ``<day_end>``: Day-of-year range (1–365, inclusive).
4. ``<avg_period>``: Number of days to average over (e.g., ``910`` = 91 days × 10 years = one value per decade-spring).
5. ``<factor>``: Multiplicative scaling factor (e.g., unit conversion).
6. ``<offset>``: Additive offset applied after scaling.

Optional Fields
~~~~~~~~~~~~~~~

7. ``<pft>``: PFT index. Use ``0`` for gridcell-level variables, ``>0`` for PFT-level output from h1 files, ``-1`` if not applicable.
8. ``<obs>``: Observed value for this variable (for calibration/validation). Use ``-9999`` if not available.
9. ``<obs_err>``: Observation uncertainty (standard deviation). Use ``-9999`` if not available.
10. ``<treatment>``: Subdirectory name for treatment-specific output (used with ``--spruce_treatments``). Use ``NA`` if not applicable.

Example (``examples/postproc_vars_example``):

.. code-block:: text

   #Variable Startyear endyear Startday endday averaging period factor add offset  pft obs  obs_err
   FPSN            2000    2009         60    151          920             1    0   0    1.0     0.1
   FPSN            2000    2009        152    242          910             1    0   0    7.0     0.1
   FPSN            2000    2009        243    333          910             1    0   0    2.5     0.1
   EFLX_LH_TOT     2000    2009          1     365         3650            1    0   0   33.3     0.5

This extracts:

- Photosynthesis (``FPSN``) for three seasonal windows (spring, summer, fall) over 2000–2009, with observations.
- Latent heat flux (``EFLX_LH_TOT``) as an annual mean over the same period.

Output Files
------------

Post-Processing Outputs (Rank 0 Only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``<casename>_postprocessed.txt``
   Raw output: rows = ensemble members, columns = post-processed variables (in ``postproc_vars`` order). Only includes members without NaNs.

``UQ_output/<casename>/data/``
   Directory containing UQ-ready files:

   - ``ytrain.dat``, ``yval.dat``: Model output (80%/20% train/validation split).
   - ``ptrain.dat``, ``pval.dat``: Parameter samples (80%/20% split).
   - ``obs.dat``: Observations and uncertainties (two columns).
   - ``pnames.txt``: Parameter names (one per line).
   - ``outnames.txt``: Output variable names (one per line).
   - ``param_range.txt``: Parameter bounds (two columns: min, max).
   - ``foreden.csv``: Combined parameters + outputs in CSV format (for EDEN surrogate tool).

``UQ_output/<casename>/GSA/``
   Directory containing sensitivity analysis inputs:

   - ``param_range.txt``: Parameter names and bounds (three columns: name, min, max).

If ``--run_uq`` is enabled, the script also invokes:

- ``surrogate_NN.py --case <casename>`` — builds a neural network surrogate.
- ``run_GSA.py --case <casename>`` — performs global sensitivity analysis using SALib.
- ``MCMC.py --case <casename> --parm_list <parm_list>`` — runs MCMC calibration (only if observations are provided).

Per-Member Outputs (All Ranks)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each ensemble member runs in:

.. code-block:: text

   <runroot>/UQ/<casename>/g<NNNNN>/

where ``<NNNNN>`` is the zero-padded 5-digit job number (e.g., ``g00001``).

- ``clm_params_<NNNNN>.nc``, ``fates_params_<NNNNN>.nc``, ``surfdata_<NNNNN>.nc``: perturbed parameter/surface files.
- Model history files: ``<casename>.<model_name>.h0.<year>-01-01-00000.nc`` (and ``.h1.`` if PFT-level output is requested).
- Log files: ``e3sm_log.txt``, ``cesm_log.txt``, or ``acme_log.txt``.

Workflow Summary
----------------

1. **Parameter sampling**: Rank 0 reads ``--ens_file`` (or generates Monte Carlo samples) and ``--parm_list`` to determine ensemble size and parameter ranges.

2. **Job distribution**: Rank 0 sends job numbers (1, 2, 3, …, N) to available worker ranks.

3. **Per-member execution** (each worker rank):

   a. Receive job number from rank 0.
   b. Invoke ``ensemble_copy.py`` to clone the parent case, apply parameter perturbations, and write perturbed parameter files.
   c. Execute the model (``e3sm.exe``, ``cesm.exe``, or ``acme.exe``).
   d. If ``--postproc_file`` is provided: extract variables from history files, apply time-averaging/scaling, and send results to rank 0.
   e. Request next job.

4. **Post-processing** (rank 0):

   a. Collect results from all workers.
   b. Filter out ensemble members with NaNs.
   c. Write aggregated output files to ``UQ_output/<casename>/data/``.
   d. If ``--run_uq``: launch surrogate modeling, sensitivity analysis, and MCMC calibration.

Notes
-----

- **Single-point only**: ensemble workflows do not support regional or global simulations. The parent case must be a single-point case created with ``site_fullrun.py`` or ``runcase.py --compset I1850CNPRDCTCBC``.

- **MPI-serial executable**: the model executable must be built MPI-serial (``--ninst 1``, ``--ntasks 1``). Ensemble parallelism comes from running many single-point cases in parallel across MPI ranks, not from MPI-parallel model execution.

- **Pre-built parent case required**: ``manage_ensemble.py`` does not call ``create_newcase`` or ``case.build``. Run ``site_fullrun.py`` or ``runcase.py`` first to create and build the parent case, then pass its name via ``--case``.

- **Parameter file backend**: By default, parameters are read from NetCDF files (``clm_params.nc``, ``fates_params.nc``, ``surfdata.nc``). If ``--microbe`` is set, the script reads ASCII ``microbepar_in`` instead (legacy CNP-microbe mode).

- **SPRUCE treatments**: The ``--spruce_treatments`` flag is specific to the SPRUCE experiment at US-SPR. It runs 11 treatment simulations per ensemble member by modifying met forcing paths and CO₂ settings in ``lnd_in`` and ``drv_in``. This mode requires the parent case to produce a restart file at 2015-01-01.

See Also
--------

- ``ensemble_copy.py`` — clones a case for one ensemble member and applies parameter perturbations.
- ``ensemble_run.py`` — alternate driver (non-MPI) for single ensemble member execution.
- ``surrogate_NN.py`` — builds neural network surrogate models from ensemble output.
- ``run_GSA.py`` — performs global sensitivity analysis using SALib.
- ``MCMC.py`` — performs Bayesian calibration via MCMC on surrogate models.
- ``UQTk_scripts/`` — shell scripts for UQTk-based sensitivity (legacy, mostly replaced by SALib).
