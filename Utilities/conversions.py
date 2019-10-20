## Voltage change to capacitance change
## calibrated 20160423 by BTS, see ipython notebook dated that day
V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF)

Vx_to_um = 1/3.5 # 2016-10-05, very rough; using 3.5 V/um from 9/21 cooldown without wings
Vy_to_um = 1/3.5 # 2016-10-05, very rough; using 3.5 V/um from 9/21 cooldown without wings
Vxy_to_um = 1/3.5 # implemented in scanline. This will be the assumption until we're sure calibrations differ substantially.
Vz_to_um = .14 # based on "atto um"  atto micron/ V piezo for attocube's LUTs

# Conversion from SAA voltage to flux with SQUID locked
## NOTE: probably possible to load previous array settings without messing up the array
Vsquid_to_phi0 = {'High': 1/14.4,
                  'Med': 1/1.44,
                  'Low': 1/0.144}
# Vsquid_to_phi0 = {'High': 1/5.65, ## HYPRES
#                 'Med': 1/.565,
#                 'Low': 1/0.0565}
