import os, shutil, matplotlib, pip

## Install required packages
packages = [
    'pint',
    'tabulate',
    'jsonpickle',
    'pydaqmx',
    'pyvisa',
    'setuptools',
    'https://github.com/nowacklab/PyANC350/tarball/master',
    'https://github.com/nowacklab/Instrumental/tarball/master'
]
for package in packages:
    pip.main(['install', '--upgrade', package])


home = os.path.expanduser('~')
site_packages = os.path.dirname(os.path.abspath(os.path.join(matplotlib.__file__, '..')))

## Add utility to save jupyter notebook to HTML
package_path = os.path.join(os.getcwd(),'Utilities','jupyter_notebook_config.py')
jupyter_path = os.path.join(home, '.jupyter', 'jupyter_notebook_config.py')

shutil.copyfile(package_path, jupyter_path)

## Add github.pth file to enable "from Nowack_Lab import *"
package_path = os.path.join(os.getcwd(),'Utilities','github.pth')
anaconda_path = os.path.join(site_packages,'github.pth')

with open(anaconda_path, 'w') as f:
    f.write(os.path.dirname(os.getcwd())) # Writes Github directory name

## Add custom.css file to add padding to bottom of the notebook
package_path = os.path.join(os.getcwd(),'Utilities','custom.css')
notebook_path = os.path.join(site_packages, 'notebook', 'static', 'custom', 'custom.css')

shutil.copyfile(package_path, notebook_path)

## Add custom.js file to disable autosave
package_path = os.path.join(os.getcwd(),'Utilities','custom.js')
notebook_path = os.path.join(site_packages, 'notebook', 'static', 'custom', 'custom.js')

shutil.copyfile(package_path, notebook_path)
