// disable autosave
$([IPython.events]).on("notebook_loaded.Notebook", function () {
  IPython.notebook.set_autosave_interval(0);
});
