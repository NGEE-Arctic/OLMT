NetCDF I/O Helpers
==================

OLMT provides two lightweight NetCDF I/O helper modules that abstract read and
write operations for variables within NetCDF files. Both modules expose the
same two-function API (``getvar`` and ``putvar``) but differ in their
underlying NetCDF backend.

Which Module to Use
--------------------

**netcdf4_functions** (preferred)
    Use this module for all new code. It wraps the modern ``netCDF4`` Python
    library and is the actively maintained option.

**netcdf_functions** (legacy)
    Legacy module that falls back from ``Scientific.IO.NetCDF`` to
    ``scipy.io.netcdf`` (both deprecated). No longer used in the codebase;
    retained for backwards compatibility only.

Current Usage in Codebase
--------------------------

As of June 2026, ``netcdf4_functions`` is imported (as ``nffun``) in:

- ``runcase.py``
- ``makepointdata.py``
- ``manage_ensemble.py``
- ``ensemble_copy.py``
- ``adjust_restart.py``

The legacy ``netcdf_functions`` module is not actively used.

API Reference
-------------

Both modules expose the same interface:

getvar(fname, varname)
~~~~~~~~~~~~~~~~~~~~~~

Read a variable from a NetCDF file.

**Parameters:**
    - ``fname`` (str): Path to the NetCDF file
    - ``varname`` (str): Name of the variable to read

**Returns:**
    numpy array or scalar containing the variable's data

**netcdf4_functions behavior:**
    Raises ``ValueError`` if ``varname`` does not exist in the file.

**netcdf_functions behavior:**
    Returns the variable value; behavior on missing variable is undefined.

**Example:**

.. code-block:: python

    import netcdf4_functions as nffun
    lat = nffun.getvar('domain.nc', 'lat')

putvar(fname, varname, varvals)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Write a variable to an existing NetCDF file (append mode).

**Parameters:**
    - ``fname`` (str): Path to the NetCDF file
    - ``varname`` (str): Name of the variable to write
    - ``varvals`` (array-like): Values to assign to the variable

**Returns:**
    ``0`` on success (always; no actual error signaling)

**netcdf4_functions behavior:**
    Prints a warning if ``varname`` does not exist in the file; does not raise
    an exception.

**netcdf_functions behavior:**
    For scipy backend, silently skips scalar writes; multi-element arrays are
    written. For Scientific backend, uses ``assignValue``.

**Example:**

.. code-block:: python

    import netcdf4_functions as nffun
    nffun.putvar('domain.nc', 'mask', mask_array)

Implementation Details
----------------------

netcdf4_functions
~~~~~~~~~~~~~~~~~

Uses the ``netCDF4`` Python library (``from netCDF4 import Dataset``). Opens
files in read mode (``'r'``) for ``getvar`` and append mode (``'a'``) for
``putvar``. Always closes the file handle before returning.

Read operations use NumPy-style slicing (``variables[varname][:]``); write
operations use ellipsis assignment (``variables[varname][...] = varvals``).

netcdf_functions
~~~~~~~~~~~~~~~~

Attempts to import ``Scientific.IO.NetCDF``; falls back to ``scipy.io.netcdf``
if unavailable. Both backends are deprecated and may not be available in modern
Python environments.

The scipy path uses ``netcdf_file`` with ``mmap=False``; the Scientific path
uses the older ``NetCDFFile`` API with ``.getValue()`` and ``.assignValue()``.

Migration Notes
---------------

To convert code from ``netcdf_functions`` to ``netcdf4_functions``:

1. Change the import statement:

   .. code-block:: python

       # Old
       import netcdf_functions
       # New
       import netcdf4_functions as nffun

2. No other changes needed; the API is identical.

3. Be aware that ``getvar`` will now raise ``ValueError`` for missing variables
   rather than silently returning an undefined value.
