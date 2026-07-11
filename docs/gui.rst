GUI Overview
============

Purpose
-------

``OLMT_GUI.py`` provides a wxPython-based graphical user interface for running single-site ELM/ALM simulations. It is a wrapper around ``site_fullrun.py`` and related scripts, offering point-and-click configuration as an alternative to command-line invocation. The GUI supports both single-site runs and ensemble-based uncertainty quantification workflows.

Launch Instructions
-------------------

Run from the OLMT repository root:

.. code-block:: bash

   python OLMT_GUI.py

Dependencies:

- ``wxPython`` (required for the GUI framework)
- Standard OLMT runtime dependencies (see main README)

GUI Components
--------------

The interface is organized into three vertical panels:

Left Panel: Basic Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Input data directory**: Path to the E3SM/CESM input data tree (defaults vary by hostname; see ``ccsm_input`` at line 875).
- **Model run directory**: Path where CIME case directories will be created.
- **Site group**: Choose from available site groups (``AmeriFlux``, ``NGEEArctic``, etc.). Changing this reloads the site list from ``<ccsm_input>/lnd/clm2/PTCLM/<sitegroup>_sitedata.txt``.
- **Site**: Multi-select list of sites to run. Selecting "all" runs every site in the group.
- **Case prefix**: String prepended to case directory names.
- **Run type**: Choose one of:

  - *ad spinup* — accelerated decomposition spinup (default 250 years)
  - *final spinup* — biomass/nutrient equilibration (default 250 years)
  - *transient* — historical simulation (default 150 years)
  - *full simulation* — runs the entire three-phase sequence with diagnostics

- **# of years**: Simulation length (auto-populated when Run type changes).

Middle Panel: Site-Specific Options and Model Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Site information** (top): Read-only display of selected site's lat/lon and dominant PFTs.

**Site-specific options**:

- **Make surface data files**: Generate domain/surface/landuse files via ``makepointdata.py`` (checked by default).
- **Use site-level data in surface data files**: Apply site-specific PFT/soil data from ``_pftdata.txt`` / ``_soildata.txt`` (checked by default).
- **Use site parameters**: Passed as ``--siteparms`` (checked by default).

**Model configuration**:

- **Use satellite phenology**: Switches to ICLM45 / ICLM45CB compsets (unchecked by default: prognostic BGC).
- **Use ECA (RD if not selected)**: Toggles between ECA and RD nutrient competition schemes.
- **Use Century (CTC if not selected)**: Toggles between Century (CNT) and CTC decomposition.
- **Carbon only mode**: BGC-C (unchecked: CNP default).
- **Carbon-nitrogen mode**: BGC-CN (unchecked: CNP default).
- **Use wildfire submodel**: Enable fire model (checked by default).
- **Use dynamic rooting**: Enable dynamic root distribution (unchecked by default).
- **No datm (coupler bypass)**: Enable cpl_bypass mode (checked by default).
- **Use hourly timestep**: Run at 1-hour resolution (checked by default).
- **Use cru-ncep forcing data**: Select CRUNCEP met forcing (mutually exclusive with other forcing flags).
- **Use gswp3 forcing data**: Select GSWP3 met forcing.
- **Use c14**: Enable C14 tracer (unchecked by default).

**File for parameter mods**: Path to a custom parameter file (passed as ``--parm_file``). Use the "Browse" button to select.

**Configure, build and run**: Click "Begin simulation" to generate and execute the appropriate command.

Right Panel: Uncertainty Quantification and Plotting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Uncertainty Quantification**:

- **Ensemble File**: Path to a ``parm_list`` file defining parameter ranges (see ``examples/parm_list*``). Selecting a file auto-populates the ensemble member count.
- **Run Monte Carlo ensemble**: Generate random parameter samples (alternative to providing an ensemble file).
- **Number of ensemble members**: Total ensemble size (auto-set when loading an ensemble file).
- **Number of processors to use**: MPI ranks for ensemble execution (defaults to 256; capped at ``n_ensemble + 1``).

**Plotting and Diagnostics**:

- **Variables to plot**: Multi-select list (GPP, NEE, NPP, TLAI, TOTSOMC, TOTVEGC).
- **Generate plots**: Invokes ``plotcase.py`` with the selected variables, sites, and compset. Requires completed simulations.
- **View/Edit Files**: Opens the parameter file in Emacs (line 695: hard-coded to ``emacs <file> &``).

Workflow
--------

Single-site example:

1. Select site group (e.g., "AmeriFlux").
2. Choose one or more sites from the list.
3. Set case prefix (e.g., "test_run").
4. Choose "full simulation" to run the three-phase BGC sequence.
5. Adjust model configuration checkboxes as needed.
6. Click "Begin simulation".

The GUI builds a ``site_fullrun.py`` command with the appropriate flags and invokes it via ``os.system()`` (line 855). Output is printed to the terminal where the GUI was launched.

For ensemble runs:

1. Complete steps 1–5 above (Run type should be *ad spinup*, *final spinup*, or *transient*, not *full simulation*).
2. In the right panel, browse for an ensemble file or check "Run Monte Carlo ensemble".
3. Set the number of processors.
4. Click "Begin simulation".

The GUI will append ``--ensemble_file`` or ``--mc_ensemble`` to the command.

Plotting results:

1. After simulations complete, select sites and variables in the right panel.
2. Click "Generate plots".

This invokes ``plotcase.py --case <prefix> --site <sites> --compset <compset> --spinup --vars <vars> --csmdir <rundir>``.

Limitations vs Command-Line
----------------------------

**Not exposed in the GUI**:

- ``--model_root``: The GUI hard-codes this to ``/home/<user>/models/ACME`` for full simulations (line 810). Single-phase runs omit it (assumes OLMT scripts will handle it internally or expect it as an environment variable).
- ``--srcmods_loc``: Not configurable; no custom source modifications.
- ``--metdir``: Forcing data paths are implicit (derived from ``--ccsm_input``).
- ``--eco2_file``, ``--ssp_rcp``: No CO2 scenario control.
- Advanced spinup options (``--run_startyear``, ``--align_year``, ``--exit_spinup``).
- ``--tempdir``, ``--options_log_json``: Not exposed.
- Ensemble post-processing (``--postproc_file``): Not shown. Must be added manually to ``manage_ensemble.py`` invocations outside the GUI.
- Multi-site runs use implicit ``case_copy.py`` logic but do not expose per-site rebuild control.

**Machine detection**:

The GUI infers the machine from ``hostname`` (lines 874–883):

- ``or-condo``: sets ``--machine cades``
- ``eos`` / ``titan``: sets machine and paths for ORNL Titan (deprecated)
- Otherwise: defaults to ``--machine oic2`` (custom machine; may require manual ``config_machines.xml`` setup)

**Hardcoded paths**:

- Default ``rundir`` on CADES: ``/lustre/or-hydra/cades-ccsi/scratch/<user>``
- Default ``ccsm_input`` on CADES: ``/lustre/or-hydra/cades-ccsi/proj-shared/project_acme/ACME_inputdata/``
- Emacs as the file viewer (line 695)

**Command-line flexibility**:

For production workflows, the command-line interface (``site_fullrun.py``) is recommended — it exposes the full range of flags, supports scriptable invocation, and avoids the GUI's hostname-dependent defaults.

**Related scripts**:

- ``site_fullrun.py``: The main orchestrator invoked by the GUI.
- ``plotcase.py``: Plotting utility (not part of the standard OLMT distribution; verify availability before using the plot features).
