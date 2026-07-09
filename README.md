Offline Land Model Testbed (OLMT)
Contacts:
OLMT was originally developed by Dan Ricciuto (ricciutodm@ornl.gov)

If you've found this fork, it's likely that you are interested in
some of the Arctic-specific features from NGEE Arctic. Relevant
NGEE Arctic contacts for this code would be:

Ben Sulman (sulmanbn@ornl.gov)
Fengming Yuan (yuanf@ornl.gov)
Rich Fiorella (rfiorella@lanl.gov)
Matt Hoffman (mhoffman@lanl.gov)

An additional note that this is OLMT "classic" that NGEE Arctic is using
to maintain existing workflows. A new
version of OLMT exists here: https://github.com/dmricciuto/elm-olmt


OLMT is a set of python scripts designed to automate offline land model (ELM and CLM/CTSM) simulations at single sites, groups of sites, user-defined regions or global scales.
It will automatically create, build and submit the 3 cases needed for a full land model BGC simulation:
ad spinup:     Accelerated decomposition spinup (Thornton and Rosenbloom, 2005)
final spinup:  Final spinup to equilibrate biomass and nutrient pools
transient:     1850-present day simulation with transient trace gas concentrations, land use, atmospheric forcing

This utility will automatically create surface and domain files using an existing global file at the specified resolution (default:  hcru_hcru).

## Documentation

Full documentation is available at: https://ngee-arctic.github.io/OLMT/

To build documentation locally:
```bash
cd docs
make html
# Open docs/_build/html/index.html in browser
```
