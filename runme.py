import os, shutil, matplotlib, pip, sys, subprocess


home = os.path.expanduser('~')
site_packages = os.path.dirname(os.path.abspath(os.path.join(matplotlib.__file__, '..'))) #we know matplotlib is in site-packages

## Add utility to save jupyter notebook to HTML
package_path = os.path.join(os.getcwd(),'Utilities','notebook','jupyter_notebook_config.py')
jupyter_path = os.path.join(home, '.jupyter', 'jupyter_notebook_config.py')

if not os.path.exists(jupyter_path):
    os.makedirs(os.path.dirname(jupyter_path))
    open(jupyter_path, 'w').close() # make empty file
shutil.copyfile(package_path, jupyter_path)

## Add github.pth file to enable "from Nowack_Lab import *"
anaconda_path = os.path.join(site_packages,'github.pth')

with open(anaconda_path, 'w') as f:
    f.write(os.path.dirname(os.getcwd())) # Writes Github directory name

## Install required packages
packages = [
    'jsonschema',
    'pint',
    'tabulate',
    'jsonpickle',
    'pydaqmx',
    'pyvisa',
    'setuptools',
    'tornado==4.5.3',
    'peakutils',
    'gtts',
    'urllib3',
    'https://github.com/nowacklab/Instrumental/tarball/master',
    'https://github.com/nowacklab/PyANC350/tarball/master',
]
for package in packages:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', package])
    except Exception as e:
        print(e)

# Add custom.css file to add padding to bottom of the notebook
package_path = os.path.join(os.getcwd(),'Utilities','notebook', 'custom.css')
notebook_path = os.path.join(os.path.expanduser('~'), '.jupyter', 'custom', 'custom.css')

if not os.path.exists(os.path.dirname(notebook_path)):
    os.makedirs(os.path.dirname(notebook_path))
shutil.copyfile(package_path, notebook_path)

# ## Set default notebook template for scanning
# package_path = os.path.join(os.getcwd(),'Utilities','nbbase.py')
# nbformat_path = os.path.join(site_packages, 'nbformat', 'v4', 'nbbase.py')
#
# shutil.copyfile(package_path, nbformat_path)

## Add custom.js file to disable autosave
# package_path = os.path.join(os.getcwd(),'Utilities','custom.js')
# notebook_path = os.path.join(site_packages, 'notebook', 'static', 'custom', 'custom.js')

# shutil.copyfile(package_path, notebook_path)

## Clean up startup if exists.
# ipython_path = os.path.join(home, '.ipython', 'profile_default', 'startup', 'startup.py')

# try:
#     os.remove(ipython_path)
# except:
#     pass
