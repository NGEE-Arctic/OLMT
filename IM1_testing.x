#!/bin/bash -f

# Icy Cape cases
# case 1: baseline case, uses version of E3SM with no IM1 updates
# case 2: negative control case, uses version of E3SM with IM1 updates
#	  but they are turned off (should be identical results to case 1)
# case 3: High centered polygon test case, polygonal tundra IM1 updates have been
#	  turned on and new surface file assumes polygonal ground is 100% HCP
# case 4: Flat centered polygon test case, polygonal tundra IM1 updates have been
#	  turned on and new surface file assumes polygonal ground is 100% FCP
# case 5: Low centered polygon test case, polygonal tundra IM1 updates have been
#	  turned on and new surface file assumes polygonal ground is 100% LCP
#------------------------------------------------------------
# PREREQUISITES:
# NOTE: YOU WILL NEED TO RUN THE COMMANDS IN THIS BLOCK
# SEPARATELY FROM THIS SCRIPT, AS THEY DO NOT WORK
# IN TCSH IN THIS SCRIPT!

#module purge
#module load e3sm-3.0/gcc-8.5.0-openmpi-5.0.3
#conda activate <some environment that contains netCDF4 python package>

# You may need to make your own conda environment to do this!
# I have one called ncview that has netcdf4 and ncview, so
# I typically use `conda activate ncview`

#-----------------------------------------------------------

case=5

if [ $case == 1 ]; then
  python3 ./site_fullrun.py --compiler gnu --mpilib openmpi --machine docker \
         --site AK-ICP --sitegroup NGEEArctic --caseidprefix ICP-oldinit --cpl_bypass --gswp3 --daymet4 \
         --domainfile /home/e3smuser/inputdata/share/domains/domain.clm/ngee-arctic-development/IcyCape_domain.nc \
         --surffile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.nc \
         --landusefile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.pftdyn.nc \
	 --model_root /home/e3smuser/E3SM \
         --metdir /home/e3smuser/inputdata/atm/datm7/cpl_bypass_IM1_IcyCape/ \
	 --ccsm_input /home/e3smuser/inputdata \
         --srcmods_loc /home/e3smuser/OLMT/srcmods_gswp3dm4 \
         --nofire --no_budgets --notrans --nofnsp --nopointdata
elif [ $case == 2 ]; then
  python3 ./site_fullrun.py --compiler gnu --mpilib openmpi --machine docker \
         --site AK-ICP --sitegroup NGEEArctic --caseidprefix ICP-nopolygon --cpl_bypass --gswp3 --daymet4 \
         --domainfile /home/e3smuser/inputdata/share/domains/domain.clm/ngee-arctic-development/IcyCape_domain.nc \
         --surffile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.nc \
         --landusefile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.pftdyn.nc \
	 --model_root /home/e3smuser/E3SM \
         --metdir /home/e3smuser/inputdata/atm/datm7/cpl_bypass_IM1_IcyCape/ \
         --srcmods_loc /home/e3smuser/OLMT/srcmods_gswp3dm4 \
         --nofire --no_budgets --spinup_vars --nopointdata
elif [ $case == 3 ]; then
  python3 ./site_fullrun.py --compiler gnu --mpilib openmpi --machine docker \
         --site AK-ICP --sitegroup NGEEArctic --caseidprefix ICP-HCP-test --cpl_bypass --gswp3 --daymet4 \
         --domainfile /home/e3smuser/inputdata/share/domains/domain.clm/ngee-arctic-development/IcyCape_domain.nc \
         --surffile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata_HCP.nc \
         --landusefile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.pftdyn.nc \
         --metdir /home/e3smuser/inputdata/atm/datm7/cpl_bypass_IM1_IcyCape \
         --model_root /home/e3smuser/E3SM \
         --ccsm_input /home/e3smuser/inputdata \
         --srcmods_loc /home/e3smuser/OLMT/srcmods_gswp3dm4 \
         --use_arctic_init --dailyrunoff --nofire --no_budgets --nofnsp --notrans --nopointdata --use_polygonal_tundra
elif [ $case == 4 ]; then
  python3 ./site_fullrun.py --compiler gnu --mpilib openmpi --machine docker \
         --site AK-ICP --sitegroup NGEEArctic --caseidprefix ICP-FCP-test --cpl_bypass --gswp3 --daymet4 \
         --domainfile /home/e3smuser/inputdata/share/domains/domain.clm/ngee-arctic-development/IM1/IcyCape_domain.nc \
         --surffile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata_FCP.nc \
         --landusefile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.pftdyn.nc \
         --metdir /home/e3smuser/inputdata/atm/datm7/cpl_bypass_IM1_IcyCape \
         --model_root /home/e3smuser/E3SM \
         --srcmods_loc /home/e3smuser/OLMT/srcmods_gswp3dm4 \
         --ccsm_input /home/e3smuser/inputdata \
         --nofnsp --notrans --nofire --no_budgets --spinup_vars --nopointdata --use_polygonal_tundra
elif [ $case == 5 ]; then
  python3 ./site_fullrun.py --compiler gnu --mpilib openmpi --machine docker \
         --site AK-ICP --sitegroup NGEEArctic --caseidprefix ICP-LCP-test --cpl_bypass --gswp3 --daymet4 \
         --domainfile /home/e3smuser/inputdata/share/domains/domain.clm/ngee-arctic-development/IM1/IcyCape_domain.nc \
         --surffile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata_LCP.nc \
         --landusefile /home/e3smuser/inputdata/lnd/clm2/surfdata_map/ngee-arctic-development/IM1/IcyCape/IcyCape_surfdata.pftdyn.nc \
         --metdir /home/e3smuser/inputdata/atm/datm7/cpl_bypass_IM1_IcyCape \
         --model_root /home/e3smuser/E3SM \
         --srcmods_loc /home/e3smuser/OLMT/srcmods_gswp3dm4 \
         --ccsm_input /home/e3smuser/inputdata \
         --nofire --no_budgets --notrans --nofnsp --spinup_vars --nopointdata --use_polygonal_tundra
fi
