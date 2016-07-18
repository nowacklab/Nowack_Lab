Nowack Lab Code Package
Brian Schaefer
David Low
Guen Prawiroatmodjo
Matt Ferguson

%%%

Explanation of Utilities:

%%%%%%%%%%
github.pth
%%%%%%%%%%
To allow Anaconda to import modules, create a github.pth file with the github directory (e.g. C:\Users\Hemlock\Documents\GitHub) as contents in the Anaconda site-packages directory.
Then you can import like: from "Nowack_Lab.Procedures import touchdown"
or just "from Nowack_Lab.Procedures import *" to import everything in "Procedures"

%%%%%%%%%%
custom.css
%%%%%%%%%%
To add a bottom border, find your custom.css file (…/site-packages/notebook/static/custom/ or thereabouts) and replace it with this one. This will add some padding so you can scroll down a bit more and watch plots as they come in.