``compare_cases.py``
====================

Purpose
-------

``compare_cases.py`` is a utility for comparing the configuration and output of two or more ELM/CLM cases. It verifies that input files and model output are identical between cases, reporting differences in numerical values. This is useful for regression testing, verifying case cloning, or confirming that parameter changes have the expected impact.

The script compares:

1. Input configuration files referenced in ``lnd_in``
2. Model output history files (``*.clm2.h0.*.nc``)

Command-line Arguments
----------------------

``--runroot``
  Base directory containing CIME case run directories. If comparing cases from different root directories, provide a comma-delimited list matching the order of ``--cases``.

  **Default:** ``""`` (empty string)

``--cases``
  Comma-delimited list of case names (case IDs) to compare. The first case is treated as the reference; all subsequent cases are compared against it.

  **Required.** No default.

``--h0vars``
  Comma-delimited list of variables to compare in h0 output files. When specified, only these variables are checked; otherwise all variables are compared (except those on the exclusion list).

  **Default:** ``""`` (compare all variables)

Comparison Metrics
------------------

Input Files
^^^^^^^^^^^

The following input file types are extracted from ``lnd_in`` and compared:

- ``paramfile`` — PFT/general parameters
- ``fates_paramfile`` — FATES-specific parameters
- ``fsoilordercon`` — soil order constants
- ``fsurdat`` — surface dataset
- ``fatmlndfrc`` — land fraction / domain file
- ``finidat`` — initial conditions

For each input file type, the script performs a pairwise comparison between the first case and every subsequent case. Files are compared variable-by-variable using NumPy's ``np.ma.allequal()``, which accounts for masked arrays.

History Files (h0 output)
^^^^^^^^^^^^^^^^^^^^^^^^^

All ``*.clm2.h0.*.nc`` files in each case's ``run/`` directory are sorted and compared sequentially. The number of h0 files must match between cases.

Each variable is compared using ``np.ma.allequal()`` after squeezing dimensions. When differences are found, the mean value from each case is printed.

Excluded Variables
^^^^^^^^^^^^^^^^^^

The following variables are excluded from h0 comparisons because they are metadata, diagnostics, or known to differ between cases without indicating a problem:

- ``date_written``, ``time_written``
- ``pftname``, ``soilordername``
- ``qflx_snofrz_lyr``, ``irrig_rate``
- ``TWS_MONTH_BEGIN``, ``ENDWB_COL``
- ``vcmaxcintsun``, ``vcmaxcintsha``
- ``fates_ddbhdt``, ``mlaidiff``
- ``btran2``, ``locfnh``, ``locfnhr``
- ``fates_pftname``, ``fates_prt_organ_name``

Output Format
-------------

The script writes test results to stdout with a ``TEST`` / ``PASS`` / ``FAIL`` structure:

**Input file comparison:**

.. code-block:: text

   TEST for <file_type>
     PASS: /path/to/file1 and
           /path/to/file2 are equal.

   TEST for <file_type>
     FAIL: /path/to/file1 and
           /path/to/file2 differ.
       Differences in <varname>:
         Case 1 Mean: <value>
         Case 2 Mean: <value>

**History file comparison:**

.. code-block:: text

   TEST for h0 model output
   Case 1: <case_id_1>
   Case 2: <case_id_2>
     PASS: All <N> h0 files are equal.

   TEST for h0 model output
   Case 1: <case_id_1>
   Case 2: <case_id_2>
     FAIL: /path/to/case1.clm2.h0.YYYY-MM.nc and
           /path/to/case2.clm2.h0.YYYY-MM.nc differ.
       Differences in <varname>:
         Case 1 Mean: <value>
         Case 2 Mean: <value>
     Exiting test

When h0 file differences are detected, the script exits immediately rather than continuing through all files.

Example Usage
-------------

Compare two cases in the same run root:

.. code-block:: bash

   python compare_cases.py --runroot /scratch/cime_cases --cases case1,case2

Compare cases from different run roots:

.. code-block:: bash

   python compare_cases.py --runroot /scratch/root1,/scratch/root2 --cases case1,case2

Compare only GPP and NPP in h0 files:

.. code-block:: bash

   python compare_cases.py --runroot /scratch/cime_cases --cases case1,case2 --h0vars GPP,NPP
