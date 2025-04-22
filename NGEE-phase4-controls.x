#!/bin/bash -f
# PREREQUISITES:
# NOTE: YOU WILL NEED TO RUN THE COMMANDS IN THIS BLOCK
# SEPARATELY FROM THIS SCRIPT, AS THEY DO NOT WORK
# RUNNING IN BASH IN THIS SCRIPT!

#module purge
#module load e3sm-3.0/gcc-8.5.0-openmpi-5.0.3
#conda activate <some environment that contains netCDF4 python package>

# You may need to make your own conda environment to do this!
# I have one called ncview that has netcdf4 and ncview, so
# I typically use `conda activate ncview`

# set some variables
export MACHINE=ees
case="Toolik"


if [ $MACHINE == 'ees' ]; then
  export INPUTDATA=/project/neon_e3sm/inputdata
  export SRCMODS=/home/${USER}/OLMT/srcmods_era5cb
  export MOD_CTRL=/lclscratch/$USER/NGEE-Arctic-E3SM-master
elif [ $MACHINE == 'docker' ]; then
  export INPUTDATA=/home/e3smuser/inputdata
  export SRCMODS=/home/e3smuser/OLMT
  export MOD_CTRL=/home/e3smuser/E3SM
else
  stop
fi

export COMMON_ARGS='--compiler gnu --mpilib openmpi --sitegroup NGEEArctic --nofire --no_budgets \
                    --nopointdata --cpl_bypass --era5'

#-----------------------------------------------------------

if [ $case == "Abisko" ]; then
  
  python3 ./site_fullrun.py --machine ${MACHINE} ${COMMON_ARGS} \
         --caseidprefix cntl --ccsm_input ${INPUTDATA} --site SE-Abi --srcmods_loc ${SRCMODS} \
         --domainfile ${INPUTDATA}/share/domains/domain.clm/domain.lnd.1x1pt_Abisko-GRID.nc \
         --surffile ${INPUTDATA}/lnd/clm2/surfdata_map/surfdata_1x1pt_Abisko-GRID_simyr1850_c360x720_c250306.nc \
         --landusefile ${INPUTDATA}/lnd/clm2/surfdata_map/landuse.timeseries_1x1pt_Abisko-GRID_simyr1850-2015_c250306.nc \
         --model_root ${MOD_CTRL} \
         --metdir ${INPUTDATA}/atm/datm7/ngee-arctic-development/era5_noleap/abs

elif [ $case == "Toolik" ]; then

  python3 ./site_fullrun.py --machine ${MACHINE} ${COMMON_ARGS} \
         --caseidprefix cntl --ccsm_input ${INPUTDATA} --site AK-Tlk --srcmods_loc ${SRCMODS} \
         --domainfile ${INPUTDATA}/share/domains/domain.clm/domain.lnd.1x1pt_ToolikLake-GRID.nc \
         --surffile ${INPUTDATA}/lnd/clm2/surfdata_map/surfdata_1x1pt_ToolikLake-GRID_simyr1850_c360x720_c250306.nc \
         --landusefile ${INPUTDATA}/lnd/clm2/surfdata_map/landuse.timeseries_1x1pt_ToolikLake-GRID_simyr1850-2015_c250306.nc \
         --model_root ${MOD_CTRL} \
         --metdir ${INPUTDATA}/atm/datm7/ngee-arctic-development/era5_noleap/tfs

elif [ $case == "SamoylovIsland" ]; then

  python3 ./site_fullrun.py --machine ${MACHINE} ${COMMON_ARGS} \
         --caseidprefix cntl --ccsm_input ${INPUTDATA} --site RU-Sam --srcmods_loc ${SRCMODS} \
         --domainfile ${INPUTDATA}/share/domains/domain.clm/domain.lnd.1x1pt_SamoylovIsland-GRID.nc \
         --surffile ${INPUTDATA}/lnd/clm2/surfdata_map/surfdata_1x1pt_SamoylovIsland-GRID_simyr1850_c360x720_c250306.nc \
         --landusefile ${INPUTDATA}/lnd/clm2/surfdata_map/landuse.timeseries_1x1pt_SamoylovIsland-GRID_simyr1850-2015_c250306.nc \
         --model_root ${MOD_CTRL} \
         --metdir ${INPUTDATA}/atm/datm7/ngee-arctic-development/era5_noleap/si

elif [ $case == "TrailValleyCreek" ]; then

  python3 ./site_fullrun.py --machine ${MACHINE} ${COMMON_ARGS} \
         --caseidprefix cntl --ccsm_input ${INPUTDATA} --site CA-TVC --srcmods_loc ${SRCMODS} \
         --domainfile ${INPUTDATA}/share/domains/domain.clm/domain.lnd.1x1pt_TrailValleyCreek-GRID.nc \
         --surffile ${INPUTDATA}/lnd/clm2/surfdata_map/surfdata_1x1pt_TrailValleyCreek-GRID_simyr1850_c360x720_c250306.nc \
         --landusefile ${INPUTDATA}/lnd/clm2/surfdata_map/landuse.timeseries_1x1pt_TrailValleyCreek-GRID_simyr1850-2015_c250306.nc \
         --model_root ${MOD_CTRL} \
         --metdir ${INPUTDATA}/atm/datm7/ngee-arctic-development/era5_noleap/tvc

fi
 
