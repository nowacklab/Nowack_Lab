# Based off of https://github.com/jupyter/notebook/blob/master/docs/source/extending/savehooks.rst
# Belongs in jupyter_path = os.path.join(home, '.jupyter', 'jupyter_notebook_config.py')

## Use firefox (if Chrome runs out of memory))
import webbrowser
ffpath = 'C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe'
webbrowser.register('firefox', None, webbrowser.BackgroundBrowser(ffpath), 1)
c.NotebookApp.browser = 'firefox'


import io, os, sys
from notebook.utils import to_api_path
from IPython.paths import get_ipython_dir

## Try to load notebook extensions
ipythondir = get_ipython_dir()
extensions = os.path.join(ipythondir,'extensions')
sys.path.append(extensions)

# # _script_exporter = None
# _html_exporter = None
#
# def script_post_save(model, os_path, contents_manager, **kwargs):
#     """convert notebooks to Python script after save with nbconvert
#     replaces `ipython notebook --script`
#     """
#     # from nbconvert.exporters.script import ScriptExporter
#     from nbconvert.exporters.html import HTMLExporter
#
#     if model['type'] != 'notebook':
#         return
#
#     # global _script_exporter
#     # if _script_exporter is None:
#     #     _script_exporter = ScriptExporter(parent=contents_manager)
#     # log = contents_manager.log
#
#     global _html_exporter
#     if _html_exporter is None:
#         _html_exporter = HTMLExporter(parent=contents_manager)
#     log = contents_manager.log
#
#     # # save .py file
#     # base, ext = os.path.splitext(os_path)
#     # script, resources = _script_exporter.from_filename(os_path)
#     # script_fname = base + resources.get('output_extension', '.txt')
#     # log.info("Saving script /%s", to_api_path(script_fname, contents_manager.root_dir))
#     # with io.open(script_fname, 'w', encoding='utf-8') as f:
#     #     f.write(script)
#
#     # save html
#     base, ext = os.path.splitext(os_path)
#     script, resources = _html_exporter.from_filename(os_path)
#     script_fname = base + resources.get('output_extension', '.txt')
#     log.info("Saving html /%s", to_api_path(script_fname, contents_manager.root_dir))
#     with io.open(script_fname, 'w', encoding='utf-8') as f:
#         f.write(script)
# c.FileContentsManager.post_save_hook = script_post_save
