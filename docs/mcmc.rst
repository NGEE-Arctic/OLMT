``MCMC.py``
===========

Purpose
-------

``MCMC.py`` performs Bayesian parameter calibration using Markov Chain Monte Carlo (MCMC) sampling via the Metropolis-Hastings algorithm. It uses a neural-network surrogate model (built by ``surrogate_NN.py``) to approximate ELM behavior, enabling efficient uncertainty quantification without running the full model thousands of times.

The script estimates posterior probability distributions of parameters conditioned on observational data, producing:

1. Best-fit parameter values
2. 95% confidence intervals for parameters and model outputs
3. Parameter correlation structure
4. MCMC chain diagnostics (trace plots, burn-in behavior)
5. Prediction uncertainty plots comparing observations to model confidence intervals

``MCMC.py`` is invoked automatically by ``manage_ensemble.py`` after surrogate model training if observational error is provided (``max(myobs_err) > 0``).

Command-line Arguments
----------------------

``--case``
  Case name. Must match the case name passed to ``manage_ensemble.py``. The script expects surrogate model artifacts and training data in ``UQ_output/<casename>/``.

  **Default:** ``""`` (empty string)

``--nevals``
  Number of MCMC iterations (model evaluations). More iterations improve convergence and posterior sampling density but increase runtime. Typical values: 50,000–500,000.

  **Default:** ``"200000"``

``--burnsteps``
  Number of burn-in adaptation phases. During each burn-in step, the algorithm adapts proposal step sizes and covariance structure based on acceptance ratio. After ``burnsteps * nevals / (2 * burnsteps)`` evaluations, adaptation stops and the chain enters the sampling phase.

  **Default:** ``"10"``

``--parm_list``
  Path to the parameter list file (``parm_list`` format: one line per parameter, four whitespace-separated fields ``name pft min max``). Must match the file used for ensemble generation.

  **Default:** ``"parm_list"``

``--parm_default``
  Optional path to a file containing default parameter values (one value per line, same order as ``--parm_list``). When provided, the script runs the surrogate model with default parameters and plots the default prediction as a green line in prediction plots for comparison.

  **Default:** ``""`` (not used)

Algorithm Implementation
------------------------

Metropolis-Hastings with Adaptive Proposal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The MCMC algorithm is implemented in the ``MCMC()`` function (lines 66–320):

1. **Initialization**: Starting values are set to parameter midpoints (``model.pdef``). Initial step sizes are 5% of the prior range for each parameter.

2. **Proposal generation**: At each iteration, a new parameter vector is drawn from a multivariate normal distribution centered on the current chain position with covariance matrix ``mycov``:

   .. code-block:: python

      parms = np.random.multivariate_normal(parm_last, mycov)

3. **Posterior evaluation**: The ``posterior()`` function (lines 37–60) computes:

   - **Prior**: Uniform within the parameter bounds defined by ``parm_list``; zero outside.
   - **Log likelihood**: Gaussian likelihood for each observation:

     .. math::

        \ell_i = -\frac{1}{2} \log(2\pi) - \log(\sigma_i) - \frac{1}{2} \left(\frac{y_i - \hat{y}_i}{\sigma_i}\right)^2

     where :math:`y_i` is the observation, :math:`\hat{y}_i` is the surrogate model prediction, and :math:`\sigma_i` is the observational error.

4. **Accept/reject**: The proposal is accepted if:

   .. code-block:: python

      post - post_last >= log(random.uniform(0, 1))

   This is the standard Metropolis-Hastings criterion. Rejected proposals keep the chain at the current position.

5. **Adaptive burn-in**: Every ``nburn`` iterations during the first ``burnsteps * nburn`` evaluations, the algorithm:

   - Computes the acceptance ratio over the last ``nburn`` steps.
   - Adjusts the scaling factor:

     - If acceptance ratio ≤ 0.2, scale down (min 0.15×).
     - If acceptance ratio > 0.4, scale up (max 2.5×).
   - Recomputes ``mycov`` from the empirical covariance of recent accepted samples.
   - Prints diagnostics: burn step number, acceptance ratio, and per-parameter variance ratios.

6. **Sampling phase**: After ``burnsteps * nburn`` iterations, adaptation stops and the chain samples from the posterior with fixed covariance structure.

Surrogate Model Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^

The MCMC algorithm interfaces with the surrogate model through ``model_surrogate.MyModel`` (imported as ``models``):

- **Initialization**: ``MyModel(case=options.casename)`` loads:

  - Training data (``ptrain.dat``, ``ytrain.dat``)
  - Parameter names (``pnames.txt``)
  - Observational data and errors (``obs.dat``)
  - Output variable names (``outnames.txt``)
  - Trained neural network (``NN_surrogate/NNmodel.pkl``)
  - Valid output indices (``NN_surrogate/qoi_good.txt``)

- **Evaluation**: ``model.run(parms)`` normalizes parameters to [0,1], runs the neural network, denormalizes outputs, and populates ``model.output``.

- **Attributes**:

  - ``model.nparms``: Number of parameters
  - ``model.nobs``: Number of model outputs
  - ``model.pmin``, ``model.pmax``: Parameter bounds
  - ``model.pdef``: Default parameter values (midpoints)
  - ``model.obs``, ``model.obs_err``: Observations and uncertainties
  - ``model.obs_name``: Output variable names
  - ``model.parm_names``: Parameter names

Output Format
-------------

All outputs are written to ``UQ_output/<casename>/MCMC_output/``:

Text Files
^^^^^^^^^^

``MCMC_chain.txt``
  Post-burn-in MCMC chain (``nevals - burnsteps * nburn`` rows, ``nparms`` columns). Each row is one accepted or repeated parameter vector. Used for posterior analysis.

``parms_best.txt``
  Best-fit parameters (highest posterior probability encountered during the chain). Format: ``<name> <pft> <value>``, one parameter per line.

``parms_95pctconf.txt``
  95% credible intervals for parameters. Format: ``<name> <lower_2.5%> <upper_97.5%>``, one parameter per line.

``outputs_95pctconf.txt``
  95% prediction intervals for model outputs. Two space-separated values per line (lower and upper 97.5% quantiles), one line per output variable.

``correlation_matrix.txt``
  Parameter correlation matrix (``nparms × nparms``). Diagonal is 1.0; off-diagonal values in [-1, 1] indicate posterior correlations.

Diagnostic Plots
^^^^^^^^^^^^^^^^

``plots/chains/burnin_chain_<parmname>.pdf``
  Trace plots for burn-in phase (first ``burnsteps * nburn`` iterations). One plot per parameter. Used to verify adaptation behavior.

``plots/chains/chain_<parmname>.pdf``
  Trace plots for post-burn-in sampling phase. One plot per parameter. Used to assess convergence and mixing.

``plots/pdfs/<parmname>.pdf``
  Marginal posterior histograms (25 bins). One plot per parameter.

``plots/predictions/Predictions_<variable>.pdf``
  Model-observation comparison plots for each unique variable in ``obs.dat``. Shows:

  - Observations with error bars (black)
  - Model best-fit prediction (red)
  - Model 95% confidence interval (black dashed)
  - Default parameter prediction (green, if ``--parm_default`` provided)

  Useful for assessing fit quality and identifying outliers.

Integration with manage_ensemble.py
------------------------------------

``manage_ensemble.py`` orchestrates the full UQ workflow:

1. **Ensemble generation**: Master process distributes parameter samples across MPI ranks. Each rank runs ``ensemble_run.py`` for assigned ensemble members.

2. **Post-processing**: Master aggregates results and writes training data (``UQ_output/<casename>/data/ptrain.dat``, ``ytrain.dat``, ``obs.dat``, etc.).

3. **Surrogate training**: Invokes ``surrogate_NN.py --case <casename>`` to train the neural network emulator.

4. **Sensitivity analysis**: Invokes ``run_GSA.py --case <casename>`` to compute Sobol indices.

5. **MCMC calibration**: If ``max(myobs_err) > 0`` (i.e., observational data with non-zero uncertainties exists), invokes:

   .. code-block:: python

      os.system("python MCMC.py --case " + options.casename + " --parm_list " + options.parm_list)

   This step is skipped if no valid observational constraints are provided (zero or negative error bars).

Observational Data Format
^^^^^^^^^^^^^^^^^^^^^^^^^^

Observations are specified via the ``--postproc_file`` argument to ``manage_ensemble.py``. The file format is documented in ``examples/postproc_vars_example``. Each line specifies a variable name, file pattern, and (optionally) observational value and uncertainty.

``manage_ensemble.py`` parses this file and writes ``UQ_output/<casename>/data/obs.dat``, where each line is:

.. code-block:: text

   <observation_value> <observation_error>

Zero or negative error indicates no observational constraint for that variable. MCMC is only triggered if at least one variable has a positive error.

Workflow Example
^^^^^^^^^^^^^^^^

Typical invocation via ``manage_ensemble.py``:

.. code-block:: bash

   mpirun -n 16 python manage_ensemble.py \
       --case UQ_test \
       --ens_file ens_samples.txt \
       --postproc_file postproc_vars \
       --parm_list parm_list

If ``postproc_vars`` contains observational data with positive errors, the workflow proceeds:

1. Ensemble runs (16 parallel ranks)
2. Post-processing and data extraction
3. ``surrogate_NN.py`` (trains neural network)
4. ``run_GSA.py`` (sensitivity analysis)
5. ``MCMC.py`` (Bayesian calibration)

Convergence Diagnostics
------------------------

Assessing Convergence
^^^^^^^^^^^^^^^^^^^^^

Check the following outputs to verify MCMC convergence:

1. **Acceptance ratio**: Printed to stdout at the end. Target: 20%–40%. Values outside this range suggest poor tuning (too low: steps too large; too high: steps too small, slow exploration).

2. **Trace plots**: ``plots/chains/chain_<parmname>.pdf`` should show:

   - No systematic drift or trends (stationarity)
   - Rapid mixing (chain moves freely, not stuck in one region)
   - No burn-in artifacts (adaptation should have eliminated these)

3. **Burn-in trace plots**: ``plots/chains/burnin_chain_<parmname>.pdf`` should show adaptation working: step sizes adjust, chain explores parameter space, acceptance ratio converges to target range.

4. **Effective sample size**: Not computed automatically. Post-process ``MCMC_chain.txt`` with external tools (e.g., ``arviz``, ``PyMC``) to estimate ESS. Aim for ESS > 1000 per parameter.

Recommendations
^^^^^^^^^^^^^^^

- **Increase ``--nevals``** if trace plots show poor mixing or autocorrelation is high.
- **Increase ``--burnsteps``** if burn-in plots show slow adaptation or acceptance ratio is far from 20%–40% at the end of burn-in.
- **Check surrogate model quality** (``surrogate_NN.py`` diagnostics) if posterior is insensitive to parameters or credible intervals are unrealistically wide. A poor surrogate will produce meaningless MCMC results.
- **Run multiple chains** (currently not implemented; modify script to vary ``parms`` initialization) and check for convergence across chains using Gelman-Rubin :math:`\hat{R}` statistic.

Limitations
-----------

- **Single chain**: No automated multi-chain convergence diagnostics.
- **Gaussian likelihood**: Assumes observational errors are Gaussian. Not suitable for count data, censored data, or other non-Gaussian likelihoods.
- **Uniform priors**: All parameters have uniform priors over their specified bounds. No support for informative or hierarchical priors.
- **No thinning**: The full chain is saved. For very long chains, consider post-processing with thinning to reduce file size.
- **Surrogate model limitations**: MCMC results are only as good as the surrogate model. If the neural network poorly approximates the true model in regions of parameter space, posteriors will be incorrect. Always validate surrogate quality before trusting MCMC outputs.

References
----------

- Metropolis, N., et al. (1953). Equation of State Calculations by Fast Computing Machines. *Journal of Chemical Physics*, 21(6), 1087–1092.
- Hastings, W. K. (1970). Monte Carlo sampling methods using Markov chains and their applications. *Biometrika*, 57(1), 97–109.
- Gelman, A., et al. (2013). *Bayesian Data Analysis* (3rd ed.). Chapman and Hall/CRC.

Example Usage
-------------

Run MCMC on a pre-built surrogate model:

.. code-block:: bash

   python MCMC.py --case UQ_test --nevals 100000 --burnsteps 10 --parm_list parm_list

Run with default parameter comparison:

.. code-block:: bash

   python MCMC.py --case UQ_test --nevals 100000 --burnsteps 10 \
       --parm_list parm_list --parm_default parms_default.txt

Increase sampling for better convergence:

.. code-block:: bash

   python MCMC.py --case UQ_test --nevals 500000 --burnsteps 20 --parm_list parm_list
