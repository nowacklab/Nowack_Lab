'''
Script to start a server connection to the Blue PPMS.

This will only run in an IronPython 2.7 Shell.

Pass in two arguments: local host, local port
'''

# Add GitHub to path so we can import pyQDInstrument
import sys, os
home = os.path.expanduser('~')
path = os.path.join(home, 'Documents','GitHub')
sys.path.append(path)

import pyQDInstrument as pqi
# Arguments are: 
# 	Local host (Not sure how to find/set this)
#	Local port (Not sure how to find/set this)
#	PPMS computer IP address
# 	port (select in QD instrument server)
localhost = sys.argv[1]
localport = int(sys.argv[2])
pqi.run_server(localhost, localport, '192.168.0.101', 11000)
