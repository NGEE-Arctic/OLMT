OLMT Documentation
==================

**Offline Land Model Testbed (OLMT)** is a collection of Python scripts that automate ELM and CLM/CTSM simulations on top of E3SM/CIME. It orchestrates the standard three-phase BGC simulation workflow: accelerated decomposition spinup, final spinup, and transient runs from 1850 to present.

Quick Links
-----------

* **Single-site simulations:** :doc:`site_fullrun`
* **Regional/global simulations:** :doc:`global_fullrun`
* **Ensemble & UQ workflows:** :doc:`manage_ensemble`, :doc:`MCMC <mcmc>`
* **Getting started:** :doc:`user_guide`

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide

.. toctree::
   :maxdepth: 1
   :caption: Core Scripts

   site_fullrun
   global_fullrun
   runcase
   makepointdata
   case_copy

.. toctree::
   :maxdepth: 1
   :caption: Ensemble & UQ Scripts

   manage_ensemble
   ensemble_run
   ensemble_copy
   mcmc
   model_surrogate
   surrogate_nn
   run_gsa

.. toctree::
   :maxdepth: 1
   :caption: Analysis & Utilities

   plotcase
   adjust_restart
   compare_cases
   gui
   netcdf_io

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
