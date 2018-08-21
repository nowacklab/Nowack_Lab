print('Importing a bunch of stuff, hang tight!')

import os, shutil
# Workaround for scipy altering KeyboardInterrupt behavior
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

from .Utilities import save

# Set experiment data path
try:
    print('Current experiment: %s' %save.get_experiment_data_dir())
except:
    pass

print('Use save.set_experiment_data_dir to change experiments')

# Check for remote data server connection
if not os.path.exists(save.get_data_server_path()):
    print('''SAMBASHARE not connected. Could not find path %s.''' %save.get_data_server_path())

# Make a setup file. This file contains all desired imports.
setup_path = os.path.join(os.path.dirname(__file__),
                            'Utilities',
                            'setup',
                            save.get_computer_name() + '.py'
                        )
if not os.path.exists(setup_path):
    print('\nSetup file %s created.' %setup_path)
    template_path = os.path.join(os.path.dirname(__file__),
                            'Utilities',
                            'setup',
                            'template.py'
                        )
    shutil.copy(template_path, setup_path)

# Run the setup file.
from IPython import get_ipython, display
ip = get_ipython()
if ip: # if we are in an IPython/Jupyter environment
    ip.magic('run \"%s\"' %setup_path)
