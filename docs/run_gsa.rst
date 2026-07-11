run_GSA.py
==========

Purpose
-------

Performs global sensitivity analysis (GSA) using Sobol sensitivity indices on surrogate model output. This script is part of OLMT's uncertainty quantification workflow and computes first-order (main) and total-effect sensitivity indices for parameter-QOI relationships using the Saltelli sampling scheme and SALib.

Command-line Arguments
----------------------

``--case``
    Name of the ensemble case. This must correspond to a previously run ensemble with trained surrogate model outputs in ``./UQ_output/<casename>/``. **Required**.

    Example: ``--case myensemble_run``

Required Input Files
--------------------

The script expects the following directory structure under ``./UQ_output/<casename>/``:

- ``param_range.txt`` — Parameter bounds file used by SALib (Saltelli sampling and Sobol analysis). Format is SALib-specific (name, lower bound, upper bound per line).
- ``data/ptrain.dat`` — Training parameter samples (nparms columns, ntrain rows).
- ``data/ytrain.dat`` — Training output observations (nobs columns, ntrain rows).
- ``data/pnames.txt`` — Parameter names (read by ``model_surrogate.MyModel``).
- ``data/obsnames.txt`` (or equivalent) — Observation/QOI names (read by ``model_surrogate.MyModel``).
- Pre-trained neural network surrogate model weights (loaded by ``model_surrogate.MyModel``).

Sensitivity Metrics Computed
-----------------------------

The script computes Sobol sensitivity indices using SALib's ``sobol`` analyzer:

**Main effect (first-order) sensitivity indices** (``S1``)
    The fraction of output variance explained by each parameter acting independently. Represents the direct effect of varying a parameter while all others are held fixed at their nominal values.

**Total effect sensitivity indices** (``ST``)
    The fraction of output variance explained by a parameter including all its interactions with other parameters. Represents the total contribution of a parameter, including main effect and all higher-order interaction effects.

For each QOI (quantity of interest, one per column in ``ytrain.dat``), the script:

1. Generates Saltelli quasi-random samples (8192 base samples → ~200K model evaluations for typical parameter counts).
2. Evaluates the neural network surrogate model on all Saltelli samples.
3. Computes Sobol indices by calling ``SALib.analyze.sobol`` via subprocess for each QOI.
4. Parses the text output to extract main and total indices with their bootstrap confidence intervals.

Output Format
-------------

**Numerical outputs** (all under ``./UQ_output/<casename>/GSA/``):

``Saltelli_samples.txt``
    The quasi-random parameter samples used for GSA (nparms columns, ~(nparms+2)*N*8192 rows).

``outputs.txt``
    Surrogate model predictions for all Saltelli samples (nobs columns, one row per sample).

``analyses/analysis_ob<n>.txt``
    SALib text output for QOI index ``n``. Contains main and total indices with confidence intervals for all parameters.

**Graphical outputs** (all under ``./UQ_output/<casename>/GSA/``):

``sens_main.pdf``
    Stacked bar chart of first-order (main) sensitivity indices. One bar per QOI, colored segments represent individual parameter contributions. Legend shows parameter names.

``sens_tot.pdf``
    Stacked bar chart of total-effect sensitivity indices. Same structure as ``sens_main.pdf``. Total indices sum to more than 1.0 when interaction effects are present.

**In-memory arrays** (not saved to disk by this script):

- ``sens_main`` — (nparms, nobs) array of main-effect indices
- ``sens_main_unc`` — (nparms, nobs) array of main-effect confidence intervals
- ``sens_tot`` — (nparms, nobs) array of total-effect indices
- ``sens_tot_unc`` — (nparms, nobs) array of total-effect confidence intervals

Relationship to UQTk_scripts/
------------------------------

``run_GSA.py`` and ``UQTk_scripts/`` represent **two alternative GSA workflows**:

**run_GSA.py** (Python / SALib)
    - Uses Python's ``SALib`` library for Sobol sensitivity analysis.
    - Requires a pre-trained neural network surrogate (see ``surrogate_NN.py``).
    - Generates Saltelli samples and evaluates the NN surrogate directly in Python.
    - Produces stacked bar charts of sensitivity indices.
    - Self-contained single-script workflow after surrogate training.

**UQTk_scripts/** (UQTk / polynomial chaos)
    - Uses the UQTk C++/Python toolchain for polynomial chaos expansion (PCE) surrogates.
    - ``run_sensitivity.x`` drives UQTk's ``uq_pc.py`` to build PCE surrogates via least-squares or Bayesian compressive sensing.
    - Expects ``ptrain.dat``, ``ytrain.dat``, ``pval.dat``, ``yval.dat``, ``param_range.txt`` in a data directory.
    - Computes sensitivities analytically from PCE coefficients (no Saltelli sampling needed).
    - Produces more extensive visualizations: data-vs-model, sensitivity matrices, circular plots, multi-index plots, output PDFs.
    - Requires external UQTk installation (paths configured in ``prepare_env.x``).

**When to use which:**

- Use ``run_GSA.py`` when you have a trained NN surrogate and want Sobol indices quickly with standard Python dependencies.
- Use ``UQTk_scripts/`` when you need polynomial chaos surrogates, analytical sensitivity computation, or the richer UQTk visualization suite. Requires UQTk installed externally.

Both workflows share the same ``./UQ_output/<casename>/`` structure for training data, but diverge in surrogate construction (NN vs PCE) and sensitivity computation (Saltelli sampling vs analytical PCE).

Example Usage
-------------

After running an ensemble and training a surrogate::

    python run_GSA.py --case my_ensemble_case

This will create ``./UQ_output/my_ensemble_case/GSA/`` with Sobol indices and bar charts.

Notes
-----

- The script uses 8192 base samples (hardcoded, line 18), which translates to approximately ``8192 * (nparms + 2)`` surrogate evaluations for a problem with ``nparms`` parameters. This is the Saltelli scheme's requirement for computing second-order indices (though this script only reports first-order and total indices).
- SALib is invoked via ``os.system()`` subprocesses rather than direct Python API calls. Stderr/stdout are redirected to ``analyses/analysis_ob<n>.txt``.
- The script does not save the parsed sensitivity arrays (``sens_main``, ``sens_tot``) to disk; only the raw SALib text outputs and PDF plots are written. To persist the arrays, add ``np.savetxt()`` calls after the parsing loop (line 67).
- X-axis labels in the bar charts collapse repeated QOI names to save space (lines 73-78). If consecutive QOIs share the same name, only the first occurrence is labeled.

See Also
--------

- ``model_surrogate.py`` — Defines ``MyModel`` class that loads surrogate and runs predictions.
- ``surrogate_NN.py`` — Trains the neural network surrogate used by this script.
- ``manage_ensemble.py`` — Orchestrates ensemble runs that produce the training data.
- ``UQTk_scripts/run_sensitivity.x`` — Alternative GSA workflow using UQTk polynomial chaos.
