Nowack Lab Code Package
Brian Schaefer
David Low
Guen Prawiroatmodjo
Matt Ferguson


%%%%%%%%%%%%%%%%%%%%%%%%%%%
You will need to clone PyANC350 from https://github.com/nowacklab/attocube-ANC350-Python-library
into the GitHub folder and rename the folder PyANC350; dashes are bad!

%%%%%%%%%%%%%%%%%%%%%%%%%%%

Install Utilities by running “runme.py”.
Explanation of Utilities:

%%%%%%%%%%
github.pth
%%%%%%%%%%
To allow Anaconda to import modules, create a github.pth file with the github directory (e.g. C:\Users\Hemlock\Documents\GitHub) as contents in the Anaconda site-packages directory (C:\Anaconda3\Lib\site-packages\).
Then you can import like: from "Nowack_Lab.Procedures import touchdown"
or just "from Nowack_Lab.Procedures import *" to import everything in "Procedures"

%%%%%%%%%%
custom.css
%%%%%%%%%%
To add a bottom border, find your custom.css file (…/site-packages/notebook/static/custom/ or thereabouts) and replace it with this one. This will add some padding so you can scroll down a bit more and watch plots as they come in.

%%%%%%%%%%%%%%%%%%%%%%%%%%
jupyter_notebook_config.py
%%%%%%%%%%%%%%%%%%%%%%%%%%
Configures notebook to save a .html copy along with the .ipynb file. Allows for easy viewing of notebooks.
