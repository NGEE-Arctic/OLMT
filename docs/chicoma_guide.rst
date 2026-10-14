Global 0.5° GSWP3 Runs on Chicoma
==================================

This guide covers submitting a global half-degree (``hcru_hcru``) three-phase ELM
BGC simulation with GSWP3 forcing on **chicoma-cpu** (LANL Institutional
Computing), with automatic chained restarts, a 16-hour wall clock limit, and a
4-node × 128-core layout.

It also covers two containerized variants of the same image:
**``docker-chicoma-cpu``**, a laptop rehearsal machine that mirrors chicoma's
node geometry for validating the OLMT pipeline before spending allocation, and
**``chicoma-cpu-charliecloud``**, which runs that same container on chicoma's
**compute nodes** under real Slurm batch via Charliecloud — containerized
production, not just rehearsal. See :ref:`chicoma-charliecloud`.

.. _chicoma-two-machines:

Three machines, three purposes
--------------------------------

``docker-chicoma-cpu`` and ``chicoma-cpu-charliecloud`` are the **same
container image**; the only differences are the launcher and whether Slurm
is involved. Neither "containerized" nor "batch-submitted" implies the
other — the container can submit real jobs, it just needs a different
machine definition than the laptop-rehearsal one to do it.

.. list-table::
   :header-rows: 1
   :widths: 18 27 27 27

   * -
     - ``docker-chicoma-cpu``
     - ``chicoma-cpu-charliecloud``
     - ``chicoma-cpu``
   * - Defined in
     - ``~/.cime/config_machines.xml`` **inside the container**
     - ``~/.cime/config_machines.xml`` **inside the container**
     - E3SM ``cime_config/machines/config_machines.xml``
   * - Purpose
     - Rehearse config/namelists/decomp on a laptop
     - Containerized **production** on chicoma compute nodes
     - Native production runs
   * - ``BATCH_SYSTEM``
     - ``none``
     - ``slurm``
     - ``slurm``
   * - ``MAX_MPITASKS_PER_NODE``
     - 128
     - 128
     - 128
   * - ``MAX_TASKS_PER_NODE``
     - 128
     - 128
     - 256 (2 threads/core)
   * - Launcher
     - ``mpirun -np N --bind-to core --map-by numa``
     - ``srun -n N -N M -c 2 --cpu_bind=cores -m plane=128 ch-run $IMAGE --``
     - ``srun -n N -N M -c 2 --cpu_bind=cores -m plane=128``
   * - MPI
     - Open MPI 4.1.6 (PMIx-enabled)
     - Open MPI 4.1.6 (PMIx-enabled)
     - Cray MPICH 8.1.28
   * - ``DIN_LOC_ROOT``
     - ``/scratch/inputdata``
     - ``/scratch/inputdata`` (bind-mounted from lustre)
     - ``/lustre/scratch5/$USER/inputdata``
   * - ``CIME_OUTPUT_ROOT``
     - ``/scratch``
     - ``/scratch`` (bind-mounted from lustre)
     - ``/lustre/scratch5/$USER/E3SM/scratch/chicoma-cpu``
   * - ``PROJECT_REQUIRED``
     - ``FALSE`` (defaults to ``docker_runs``)
     - ``TRUE``
     - ``TRUE``
   * - OLMT submit mode
     - ``""`` — wrappers **execute directly, serially**
     - ``sbatch -d afterok:`` chain
     - ``sbatch -d afterok:`` chain

All three match chicoma's **128 MPI tasks per node** and ``GMAKE_J 128``, so
PE-layout arithmetic, decomposition, namelist generation, and the
chained-restart wrapper logic all exercise the same code paths.

.. _chicoma-container-image:

Which container image
~~~~~~~~~~~~~~~~~~~~~

Images which have the correct CIME machine files are ``e3sm-dev-debug`` and 
``e3sm-dev-amd64-v3-znver1``. If ``create_newcase`` reports
``ERROR: No machine docker-chicoma-cpu found``, you are in the wrong image.

``e3sm-dev-debug`` is multi-arch (amd64 + arm64), Ubuntu 26.04, gcc 15.2.0,
Open MPI 4.1.6, with ``ncks``/``ncrcat``/``csh`` and netCDF4 1.7.4 / numpy 2.5.2 /
scipy 1.18.1 present. Container-visible paths are ``/scratch`` and
``/scratch/inputdata``. ``e3sm-dev-amd64-v3-znver1`` has some compiler tuning options
to try to get the best performance out of the image but is otherwise similar

.. warning::

   Avoid ``e3sm-dev-amd64-v4-znver4`` for chicoma work regardless, as it requires
   a processor microarchitecture that ch-cpu lacks.

.. _chicoma-rehearse:

Rehearsing in the container
----------------------------

Two OLMT quirks must be worked around, both consequences of substring matching on
the machine name.

**1. You must pass ``--mpilib openmpi`` explicitly.** ``global_fullrun.py``
resolves the default mpilib through an ``elif`` ladder that tests
``"chicoma" in options.machine`` *before* ``"docker"``, so
``docker-chicoma-cpu`` auto-resolves to ``mpich``. The container machine declares
``MPILIBS openmpi,mpi-serial``, so ``create_newcase`` rejects it at
``CIME/case/case.py:1464``::

   ERROR: MPIlib mpich is not supported on machine docker-chicoma-cpu

**2. You must pass ``--ccsm_input`` and ``--runroot`` explicitly.** The same
ordering problem applies: the ``ccsm_input`` and ``runroot`` ladders resolve
chicoma's lustre paths for any machine name containing ``chicoma``, and
``basecmd`` always forwards them to ``runcase.py``, overriding the container's
``DIN_LOC_ROOT``/``CIME_OUTPUT_ROOT``. Without them you get
``/lustre/scratch5/$USER/inputdata``, which does not exist in the container.

.. code-block:: bash

   docker run --rm -it \
     -v $PWD:/home/e3smuser/OLMT \
     -v /path/to/E3SM:/home/e3smuser/E3SM \
     -v /path/to/inputdata:/scratch/inputdata \
     -v /path/to/output:/scratch \
     -w /home/e3smuser/OLMT \
     rfiorella/model-containers:e3sm-dev-debug \
     python ./global_fullrun.py \
       --caseidprefix rehearse \
       --machine docker-chicoma-cpu \
       --compiler gnu \
       --mpilib openmpi \
       --model_root /home/e3smuser/E3SM \
       --ccsm_input /scratch/inputdata \
       --runroot /scratch \
       --caseroot /scratch/cases \
       --tempdir /scratch/olmt_temp \
       --res hcru_hcru --gswp3 --cpl_bypass \
       --np 4 \
       --nyears_ad_spinup 20 --nyears_final_spinup 20 \
       --runblock 20 \
       --domainfile   /scratch/inputdata/share/domains/domain.clm/domain.lnd.360x720_cruncep.100429.nc \
       --surffile     /scratch/inputdata/lnd/clm2/surfdata_map/surfdata_360x720cru_simyr1850_c180216.nc \
       --landusefile  /scratch/inputdata/lnd/clm2/surfdata_map/landuse.timeseries_360x720cru_hist_simyr1850-2015_c180220.nc

What the rehearsal does and does not cover
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covered: compset resolution, year arithmetic, surface/domain/param staging,
``user_nl_elm`` contents, ``metdata_bypass`` paths, the chained-wrapper logic
(including the ``--runblock`` restart handoff), and the PE-layout math.

Not covered:

* **512 tasks will not run.** Keep ``--np`` small (4–12). At ``--np 512``,
  ``mpirun -np 512`` in a container with a handful of cores fails with *"not
  enough slots available"* — the container machine supplies no ``-N`` and there is
  no ``srun``. The 128-per-node figure shapes CIME's *arithmetic*, not the
  container's actual capacity.
* **PIO backend differs.** ``runcase.py`` sets ``PIO_TYPENAME=netcdf`` when the
  machine name contains ``docker`` **and** ``--np < 80``. A production run at
  ``--np 512`` keeps pnetcdf, so I/O behaviour is not identical.
* **MPI stack differs.** Open MPI vs Cray MPICH; chicoma's
  ``FI_CXI_RX_MATCH_MODE=software`` and ``MPICH_COLL_SYNC`` tuning is absent.
* **Scheduler behaviour differs.** See below.

How restarts behave in the container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``global_fullrun.py`` sets ``mysubmit_type = ""`` for any machine name containing
``docker``. In ``submit()`` this makes the command ``os.system(" " + fname + ...)``,
which **executes the wrapper script directly** rather than queueing it (the
scripts are ``chmod u+x``'d first, and their ``#SBATCH`` lines are inert comments
under ``#!/bin/csh -f``). The job-ID regex is skipped, so ``job_depend`` stays
empty and every chunk takes the same direct-execution path.

Net effect: all chunks of all three phases run **serially in the foreground** of
your ``docker run``, in dependency order. That is correct for a machine with
``BATCH_SYSTEM none`` and no Slurm client — but it means the container rehearsal
exercises restart *handoff* (the ``finidat`` chaining) without exercising
*queued* chaining.

.. _chicoma-production:

Production: the chicoma-cpu invocation
---------------------------------------

Run from the OLMT repo root on a chicoma **front-end** node.
Do **not** use ``docker-chicoma-cpu`` here: it has ``BATCH_SYSTEM none``, local
``/scratch`` paths, Open MPI, and OLMT will not submit for it.

.. code-block:: bash

   export IN=/lustre/scratch5/$USER/inputdata

   python ./global_fullrun.py \
     --caseidprefix g05_gswp3 \
     --machine chicoma-cpu \
     --compiler gnu \
     --mpilib mpich \
     --project <your_IC_account> \
     --model_root /path/to/E3SM \
     --ccsm_input $IN \
     --caseroot  /lustre/scratch5/$USER/E3SM/cases \
     --runroot   /lustre/scratch5/$USER/E3SM/scratch/chicoma-cpu \
     --tempdir   /lustre/scratch5/$USER/olmt_temp/g05_gswp3 \
     --res hcru_hcru \
     --gswp3 \
     --cpl_bypass \
     --np 512 \
     --walltime 15.5 \
     --runblock 20 \
     --domainfile   $IN/share/domains/domain.clm/domain.lnd.360x720_cruncep.100429.nc \
     --surffile     $IN/lnd/clm2/surfdata_map/surfdata_360x720cru_simyr1850_c180216.nc \
     --landusefile  $IN/lnd/clm2/surfdata_map/landuse.timeseries_360x720cru_hist_simyr1850-2015_c180220.nc \
     --no_submit

Notes on individual flags:

``--compiler gnu`` / ``--mpilib mpich``
   OLMT defaults to exactly these for ``chicoma-cpu``, and unlike the container
   case they are *valid* there (``MPILIBS mpich``). Stating them documents intent.

``--project``
   Required: chicoma-cpu sets ``PROJECT_REQUIRED TRUE``, and OLMT only writes
   ``#SBATCH -A`` when the project is non-empty. If omitted, OLMT falls back to
   the first line of ``~/.cesm_proj``.

``--cpl_bypass``
   Strongly recommended for global BGC spinups. It selects the ``ICB`` compset
   prefix and reads GSWP3 directly via
   ``metdata_bypass=$IN/atm/datm7/atm_forcing.datm7.GSWP3.0.5d.v1.c170516/cpl_bypass_full``,
   skipping DATM entirely. It also sets the transient length to 161 years rather
   than 71.

``--domainfile`` / ``--surffile`` / ``--landusefile``
   Recommended: passing these explicitly skips the ``makepointdata`` staging
   path entirely.

``--no_submit``
   Recommended for the first pass: builds all three cases and writes every wrapper
   script without queueing, so you can verify the node directives.

``--tempdir``
   Put this on Lustre and keep it: the chained wrapper scripts live here and you
   will need them for manual submission.

Resulting case directories under ``--caseroot``::

   g05_gswp3_hcru_hcru_ICB1850CNRDCTCBC_ad_spinup     (260 yr)
   g05_gswp3_hcru_hcru_ICB1850CNPRDCTCBC              (200 yr)
   g05_gswp3_hcru_hcru_ICB20TRCNPRDCTCBC              (161 yr)

PE layout, wall clock, and run lengths
---------------------------------------

Requested layout: 4 nodes × 128 cores = 512 MPI tasks.

``--np 512`` with ``--machine chicoma-cpu`` gives ``ppn = min(128, 512) = 128`` in
``runcase.py:1104-1118``, which sets both ``MAX_TASKS_PER_NODE`` and
``MAX_MPITASKS_PER_NODE`` to 128 — deliberately disabling the second hardware
thread per core, since ELM scales poorly with SMT. CIME's node arithmetic
(``env_mach_pes.py``) then gives::

   tasks_per_node = min(128 // 1, 128, 512) = 128
   num_nodes      = ceil(512 / 128)        = 4

and the machine file's ``mpirun`` block expands to::

   srun --label -n 512 -N 4 -c 2 --cpu_bind=cores -m plane=128

which is exactly the requested layout.

Wall clock
~~~~~~~~~~

``--walltime 16`` produces ``#SBATCH --time=16:0:00``; CIME's
``convert_to_seconds`` parses that as 57600 s, identical to ``16:00:00``. But
chicoma-cpu's ``config_batch.xml`` declares a single ``standard`` queue with
``walltimemax="16:00:00"``, so 16 h is the exact maximum with **zero slack** — an
overrunning chunk is killed, not extended. Prefer ``--walltime 15.5``
(→ ``15:30:00``) so a slow chunk still writes its restart.

Run lengths with GSWP3
~~~~~~~~~~~~~~~~~~~~~~

``--gswp3`` fixes the spinup met cycle to 1901–1920 (``ncycle = 20``) and sets
``site_endyear = 2010``. Spinup lengths are rounded **up** to multiples of the
cycle:

.. list-table::
   :header-rows: 1
   :widths: 24 12 64

   * - Phase
     - Years
     - Derivation
   * - AD spinup
     - 260
     - ``--nyears_ad_spinup`` default 250, rounded up to a multiple of 20
   * - Final spinup
     - 200
     - ``--nyears_final_spinup`` default 200, already a multiple of 20
   * - Transient
     - 161
     - ``site_endyear - 1850 + 1`` = ``2010 - 1850 + 1`` (with ``--cpl_bypass``)

Total 621 simulated years. ``--align_year`` is computed as
``(1920 - 1850 + 1) % 20 + 1 = 12`` and forwarded to ``runcase.py``
automatically.

Choosing ``--runblock``
~~~~~~~~~~~~~~~~~~~~~~~

``--runblock`` is the number of simulated years per queued job. The wrapper
hard-wires ``REST_N 20`` for global runs, and each chunk restarts from a
year-boundary restart file written by the previous chunk. **Choose a multiple of
20** so every chunk ends exactly on a restart write; otherwise the file the next
chunk expects will not exist.

Sizing: run one short case, read throughput from the timing files, then scale. If
the ad_spinup sustains *R* simulated years per wall hour at 512 tasks, pick the
largest multiple of 20 with ``runblock / R`` comfortably under 15 h. With
``--runblock 20`` the phases become 13, 10, and 9 chained jobs respectively
(``ceil(161/20) = 9``, so the transient's last chunk is a single year).

How the automatic restarts actually work
-----------------------------------------

It is worth being explicit, because it is **not** CIME's ``RESUBMIT``.

``runcase.py:3073`` runs ``./xmlchange BATCH_SYSTEM=none`` unconditionally, on
every machine, immediately before ``./case.setup``. Since ``case.setup`` is what
generates the batch scripts, the resulting ``.case.run`` has no batch directives
and ``env_batch.xml`` carries ``<batch_system type="none">`` with empty
``<directive/>`` elements. CIME's queue-level chaining is therefore inert as
configured.

OLMT's mechanism instead: each phase is split into
``ceil(run_n_total / runblock)`` chunks, one wrapper script per chunk at
``<tempdir>/global_<case>_<n>.pbs``, each containing:

.. code-block:: bash

   cd <caseroot>/<case>/
   ./xmlchange --id STOP_N        --val <this_chunk_years>
   ./xmlchange --id REST_N        --val 20
   ./xmlchange --id RUN_STARTDATE --val <chunk_start>-01-01
   # chunks after the first: patch finidat to the previous chunk's restart
   cp user_nl_elm_<n> user_nl_elm
   ./case.submit --no-batch
   cd <olmt_root>

On ``chicoma-cpu`` these are chained with ``sbatch -d afterok:<previous_jobid>``,
across phase boundaries as well as within a phase, so ad → final → transient is
one dependency chain. On ``docker-chicoma-cpu`` they execute directly and
serially instead.

Each chunk is a fresh startup run reading the previous chunk's restart through
``finidat``; ``CONTINUE_RUN`` is never set. This is why ``runblock`` must be a
multiple of ``REST_N``.

The alternative: native CIME ``RESUBMIT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CIME's ``RESUBMIT`` *is* honored even under ``--no-batch``: ``env_batch.py`` calls
``case.case_run(submit_resubmits=...)`` in-process, and ``_resubmit_check`` fires
when ``RESUBMIT > 0`` and ``DOUT_S`` is false — which holds, since ``runcase.py``
ends up setting ``DOUT_S=FALSE``. So you can drive restarts inside one
allocation:

.. code-block:: bash

   cd <caseroot>/<case>
   ./xmlchange STOP_OPTION=nyears,STOP_N=20
   ./xmlchange REST_OPTION=nyears,REST_N=20
   ./xmlchange RESUBMIT=12
   ./xmlchange RESUBMIT_SETS_CONTINUE_RUN=TRUE,CONTINUE_RUN=FALSE

**Caveat:** under ``--no-batch`` those resubmits run *sequentially within the same
job*, so all 13 chunks must fit one 16-hour allocation — which defeats the
purpose. For genuinely queued resubmission, undo the forced ``BATCH_SYSTEM``
and regenerate the batch scripts:

.. code-block:: bash

   ./xmlchange BATCH_SYSTEM=slurm
   ./case.setup --reset     # regenerates .case.run WITH real #SBATCH directives
   ./case.submit            # CIME submits and chains via RESUBMIT

``case.setup --reset`` deletes the existing batch script and re-runs
``set_job_defaults`` + ``make_all_batch_files``, so the regenerated ``.case.run``
picks up chicoma's ``--partition=standard --qos=standard --account $PROJECT``
submit arguments and a correct ``--nodes``, at the cost of stepping outside
OLMT's orchestration once the cases are built. OLMT's own wrapper now writes
equivalent node directives directly, so this
alternative is no longer required to get correct node requests — it remains
useful mainly for multi-case and ensemble work where OLMT's wrapper chaining
earns its keep over single-allocation ``RESUBMIT``.

.. _chicoma-charliecloud:

Containerized production: ``chicoma-cpu-charliecloud``
---------------------------------------------------------

``docker-chicoma-cpu`` cannot submit batch jobs — that is correct, by design,
for a laptop rehearsal machine with ``BATCH_SYSTEM none``. It does **not**
follow that the container itself can't run under Slurm. Charliecloud
(LANL's unprivileged container runtime) can launch the same image on
chicoma's compute nodes, and the ``chicoma-cpu-charliecloud`` CIME machine
definition (in ``model-containers/cime_files/``, alongside
``docker-chicoma-cpu``) wires that up as a real ``BATCH_SYSTEM=slurm``
machine. The container's Open MPI is built ``--with-pmix=/usr`` for exactly
this: ``srun`` launches one ``ch-run`` per MPI rank directly, with **no inner
``mpirun``**, rendezvousing through Slurm's PMIx server.

Converting the image
~~~~~~~~~~~~~~~~~~~~~

Charliecloud runs unpacked images or SquashFS files, not Docker Hub
references directly. Pull and convert on a chicoma front-end:

.. code-block:: bash

   ch-image pull rfiorella/model-containers:e3sm-dev-amd64-v3-znver1
   ch-convert -o squash rfiorella/model-containers:e3sm-dev-amd64-v3-znver1 \
     /lustre/scratch5/$USER/images/e3sm-dev-amd64-v3-znver1.sqfs

   export OLMT_CHARLIECLOUD_IMAGE=/lustre/scratch5/$USER/images/e3sm-ddev-amd64-v3-znver1

``OLMT_CHARLIECLOUD_IMAGE`` is read by the machine's ``<mpirun>`` block
(``$ENV{OLMT_CHARLIECLOUD_IMAGE}``) and must be set in every shell that runs
``case.setup``, ``case.build``, or submits/executes a chunk — including
inside the ``sbatch`` wrappers, so export it before building and add it to
your shell init or the project's ``~/.bashrc`` if submitting across sessions.

Build phase
~~~~~~~~~~~

Run ``global_fullrun.py`` **inside** an interactive ``ch-run`` session on a
chicoma front-end, bind-mounting lustre onto the container's existing mount
points (``/scratch``, ``/E3SM``, ``/OLMT`` — these exist in the image
specifically for Charliecloud bind-mounts):

.. code-block:: bash

   ch-run --bind /lustre/scratch5/$USER/inputdata:/scratch/inputdata \
          --bind /lustre/scratch5/$USER/E3SM/scratch:/scratch \
          --bind /path/to/E3SM:/E3SM \
          --bind /path/to/OLMT:/OLMT \
          -w $OLMT_CHARLIECLOUD_IMAGE -- bash

   # inside the container:
   cd /OLMT
   python ./global_fullrun.py \
     --caseidprefix g05_gswp3_cc \
     --machine chicoma-cpu-charliecloud \
     --compiler gnu \
     --mpilib openmpi \
     --project <your_IC_account> \
     --model_root /E3SM \
     --ccsm_input /scratch/inputdata \
     --caseroot  /scratch/cases \
     --runroot   /scratch \
     --tempdir   /scratch/olmt_temp/g05_gswp3_cc \
     --res hcru_hcru \
     --gswp3 \
     --cpl_bypass \
     --np 512 \
     --walltime 15.5 \
     --runblock 20 \
     --domainfile   /scratch/inputdata/share/domains/domain.clm/domain.lnd.360x720_cruncep.100429.nc \
     --surffile     /scratch/inputdata/lnd/clm2/surfdata_map/surfdata_360x720cru_simyr1850_c180216.nc \
     --landusefile  /scratch/inputdata/lnd/clm2/surfdata_map/landuse.timeseries_360x720cru_hist_simyr1850-2015_c180220.nc \
     --no_submit

This is the same ``--no_submit`` pattern as the native production path: it
builds all three cases and writes wrapper scripts without queueing
. ``--mpilib openmpi`` and the
``/scratch``-rooted paths above are required explicitly, exactly as for
``docker-chicoma-cpu`` — ``chicoma-cpu-charliecloud`` gets its own carve-out
in ``global_fullrun.py``'s ``ccsm_input``/``mpilib``/``runroot`` ladders
(before the generic ``"chicoma" in options.machine`` branches) so it does
**not** inherit chicoma-cpu's real lustre defaults or ``mpich``. Put
``--tempdir`` and ``--caseroot``/``--runroot`` under the lustre paths you
bind-mounted onto ``/scratch`` so the wrapper scripts are visible outside
the container too.

Submit phase
~~~~~~~~~~~~

Exit the container — no Slurm client is needed inside it. From the bare
front-end, submit the chained wrappers with ``sbatch``, exactly as described
in :ref:`chicoma-production`. The wrappers now carry their own
``--nodes``/``--ntasks-per-node``/``--partition``/``--qos``/``--exclusive``
directives, so no command-line override is
needed:

.. code-block:: bash

   export OLMT_CHARLIECLOUD_IMAGE=/lustre/scratch5/$USER/images/e3sm-dev-debug.sqfs
   cd <tempdir>
   prev=""
   for f in $(ls global_*ad_spinup_*.pbs | sort -t_ -k3 -n) \
            $(ls global_*ICB1850CNPRDCTCBC_*.pbs | sort -t_ -k3 -n) \
            $(ls global_*ICB20TRCNPRDCTCBC_*.pbs | sort -t_ -k3 -n); do
     if [ -z "$prev" ]; then jid=$(sbatch --parsable $f)
     else                    jid=$(sbatch --parsable -d afterok:$prev $f); fi
     echo "$f -> $jid"; prev=$jid
   done

``OLMT_CHARLIECLOUD_IMAGE`` must be exported in the submitting shell because
Slurm propagates the submitting environment into the job by default — the
wrapper's ``srun`` line references ``$ENV{OLMT_CHARLIECLOUD_IMAGE}`` at
``case.setup`` time (baked into ``env_mach_specific.xml``, not re-read at
submit time), so this only matters if you re-run ``case.setup --reset``.

Each chunk's actual run step, generated by CIME from the new ``<mpirun>``
block, is::

   srun --label -n 512 -N 4 -c 2 --cpu_bind=cores -m plane=128 \
     ch-run $OLMT_CHARLIECLOUD_IMAGE -- /scratch/cases/<case>/bld/e3sm.exe

Verify this with ``./preview_run | grep srun`` inside the case directory
before submitting, same as the native-production checklist.

What does not change
~~~~~~~~~~~~~~~~~~~~~

The wall-clock, run-length, and ``--runblock`` guidance under
:ref:`chicoma-production` (PE layout, wall clock, and run lengths) is
unchanged — ``chicoma-cpu-charliecloud`` uses the same ``MAX_MPITASKS_PER_NODE
128`` and the same ``standard`` queue walltime cap as native ``chicoma-cpu``.
``docker-chicoma-cpu``'s guidance in :ref:`chicoma-rehearse` is untouched and
remains correct for laptop rehearsal — it still cannot submit batch jobs, by
design; that limitation was never about containers in general.

Verification checklist before spending allocation
--------------------------------------------------

.. code-block:: bash

   cd <caseroot>/g05_gswp3_hcru_hcru_ICB1850CNRDCTCBC_ad_spinup

   ./xmlquery NTASKS_LND,NTASKS_ATM,MAX_MPITASKS_PER_NODE,MAX_TASKS_PER_NODE
   #   expect 512, 512, 128, 128
   ./preview_run | grep srun
   #   expect: srun --label -n 512 -N 4 -c 2 --cpu_bind=cores -m plane=128

   ./xmlquery PIO_TYPENAME       # expect pnetcdf at np=512
   ./xmlquery DOUT_S             # expect FALSE

   grep -E 'fsurdat|flanduse|paramfile|metdata_type|metdata_bypass' user_nl_elm
   #   metdata_type = 'gswp3'
   #   metdata_bypass = .../atm_forcing.datm7.GSWP3.0.5d.v1.c170516/cpl_bypass_full

   grep -c SBATCH <tempdir>/global_*_0.pbs
   #   expect 7 (-A, --time, --nodes, --ntasks-per-node, --partition, --qos,
   #   --exclusive) -- see "The wrapper never requested 4 nodes" under
   #   Fixed on this branch

   ls -l $(./xmlquery --value RUNDIR)/{domain.nc,surfdata.nc,clm_params.nc}

Then submit **one** chunk alone, confirm it completes and writes
``<case>.elm.r.<year>-01-01-00000.nc``, and only then build the full dependency
chain.
