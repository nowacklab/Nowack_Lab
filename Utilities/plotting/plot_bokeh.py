import bokeh.io, numpy as np, os, datetime
import IPython.display as disp

global NB_HANDLE
NB_HANDLE = None

def init_notebook():
    '''
    Tell Bokeh to plot things in the notebook.
    Not necessary if you use the show function defined here.
    '''
    bokeh.io.output_notebook(hide_banner=True)


def choose_cmap(cmap_name):
    '''
    If cmap_name is a Bokeh palette, it is simply returned.
    Otherwise, converts a matplotlib colormap to bokeh palette
    '''
    try:
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        colormap = plt.cm.get_cmap(cmap_name)
        palette = [mpl.colors.rgb2hex(m) for m in colormap(np.arange(colormap.N))]
        return palette
    except:
        return cmap_name # if a Bokeh palette already

def clim(fig, l, u):
    '''
    Update colorscale limits for a bokeh figure.
    '''

    from bokeh.models.annotations import ColorBar
    from bokeh.models import GlyphRenderer


    # Get colorbar renderer
    for r in fig.renderers:
        if type(r) == ColorBar:
            cb = r
            break

    # Set colorbar limits
    cb.color_mapper.low = l
    cb.color_mapper.high = u

    # Get plot image renderer
    for r in fig.renderers:
        if type(r) == GlyphRenderer:
            im = r
            break

    # Set color limits in image
    im.glyph.color_mapper.low = l
    im.glyph.color_mapper.high = u

    # Update everything
    update()


def colorbar(fig, data, cmap, title=None):
    '''
    Adds a colorbar to a bokeh figure.
    fig: the figure
    data: 2D array of data values
    title: title for colorbar
    cmap: name of desired bokeh or mpl colormap
    '''
    from bokeh.models import LinearColorMapper
    from bokeh.models.annotations import ColorBar

    color_mapper = LinearColorMapper(low=data.min(), high=data.max(), palette=choose_cmap(cmap))

    cb = ColorBar(color_mapper=color_mapper,
                    location=(0,0),
                    orientation='vertical',
                    padding=20,
                    margin=0,
                    title=title)

    fig.add_layout(cb, 'right')

    # Add tool to interact with colorbar

    return cb


def figure(title=None, xlabel=None, ylabel=None):
    '''
    Sets up a bokeh figure.
    '''
    ## Set up the figure
    import bokeh.plotting as bplt
    fig = bplt.figure(plot_width = 500,
                plot_height = 500,
                tools = 'pan,reset,save,box_zoom,wheel_zoom,resize',
                title = title,
                toolbar_location='above',
                toolbar_sticky=False
            )

    ## Add data hover tool
    from bokeh.models import HoverTool
    hover = HoverTool(
        tooltips=[
            ('index', '$index'),
            ('x', '$x'),
            ('y', '$y'),
            ('name', '@name') # add this key in ColumnDataSource data dict
        ]
    )
    fig.add_tools(hover)

    ## Set up title and axis text
    # title
    fig.title.text_font_size = '30pt'
    # X
    fig.xaxis.axis_label = xlabel
    fig.xaxis.axis_label_text_font_size = '20pt'
    fig.xaxis.major_label_text_font_size = '12pt'
    # Y
    fig.yaxis.axis_label = ylabel
    fig.yaxis.axis_label_text_font_size = '20pt'
    fig.yaxis.major_label_text_font_size = '12pt'



    return fig


def image(fig, x, y, z, show_colorbar = True, z_title=None, im_handle=None, cmap='Viridis256', name=None):
    '''
    Adds a 2D image to a Bokeh plot
    fig: figure to plot on
    x,y,z: x and y are from np.meshgrid, 2D matrix in Z
    colorbar: whether or not to plot the colorbar
    z_title: title for colorbar
    im_handle: Pass the handle for an existing image to update it.
    cmap: colormap. Can use either bokeh palette or matplotlib colormap names
    name: name for the image

    '''
    ## If lists, convert to arrays
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)
    xmin = x.min()
    ymin = y.min()
    xmax = x.max()
    ymax = y.max()

    ## Plot it
    im_handle = fig.image(image=[z], x=0, y =0, dw=(xmax-xmin), dh=(ymax-ymin), palette = choose_cmap(cmap), name=name)

    ## Fix axis limits ## Temporary aspect ratio fix: make a squarish plot and make x/y equal lengths
    from bokeh.models.ranges import Range1d

    x_range = xmax-xmin
    y_range = ymax-ymin
    bigger_range = max(x_range, y_range)
    x_bound_l = xmin - (bigger_range-x_range)/2
    x_bound_u = xmax + (bigger_range-x_range)/2
    y_bound_l = ymin - (bigger_range-y_range)/2
    y_bound_u = ymax + (bigger_range-y_range)/2

    fig.x_range = Range1d(x_bound_l, x_bound_u, bounds = (x_bound_l,x_bound_u))
    fig.y_range = Range1d(y_bound_l, y_bound_u, bounds = (y_bound_l,y_bound_u))

    ## Make plot aspect ratio correct and adjust toolbar location

    # ### DOESN'T WORK: plot_height includes titles, axes, etc.
    # aspect = abs((ymin-ymax)/(xmin-xmax))
    #
    # if aspect > 1: # y range larger
    #     fig.height = fig.plot_height
    #     fig.width = int(fig.plot_height / aspect) # reduce the width
    #     fig.toolbar_location = 'left' # toolbar on long axis
    # else: # opposite
    #
    #     fig.height = int(fig.plot_width * aspect)
    #     fig.toolbar_location = 'above' # toolbar on long axis

    ## Set up ColorBar
    if show_colorbar:
        cb_handle = colorbar(fig, z, cmap, title=z_title)
        return im_handle, cb_handle

    return im_handle


def legend(fig, labels=None):
    '''
    Adds a legend to a Bokeh plot.
    fig: figure the legend will be plotted next to
    labels: list of labels for all lines (in order of plotting them). By default, uses the "name" of each line plotted.
    loc: location of legend relative to plot
    '''
    from bokeh.models.annotations import Legend
    from bokeh.models.renderers import GlyphRenderer
    from bokeh.models.glyphs import Line

    lines = []
    for r in fig.renderers: # This finds all the lines or scatter plots
        if type(r) == GlyphRenderer:
            if r.glyph.__module__ == 'bokeh.models.markers' or r.glyph == 'bokeh.models.glyphs.Line':
                lines.append(r)

    if labels == None:
        labels = [l.name for l in lines]

    legends = [(labels[i], [lines[i]]) for i in range(len(labels))]
    leg = Legend(legends = legends,
                location = (10, -30),
                background_fill_color='mediumpurple',
                background_fill_alpha = 0.2,
                label_text_font_size = '12pt'
            )

    fig.add_layout(leg, 'right')

    return leg


def line(fig, x, y, line_handle=None, color='black', linestyle='-', name=None):
    '''
    Adds a line to a Bokeh plot.
    Must specify figure and x and y data.
    Note: once figure is shown, will not add any new lines.
    Optional arguments:
    - line_handle: Pass in the handle for a line to update that line rather than create a new one.
    - color: any CSS colorname (http://www.crockford.com/wrrrld/color.html) or Hex RGB
    - linestyle: Mimicking matplotlib, can specify linestyle or markerstyle.
        Line types: - (solid), -- (dashed), : (dotted), .- (dotdash), -. (dashdot)
        Marker types: o (circle), s (square), v (inverted_triangle), ^ (triangle), x (x), + (cross), * (asterisk)
    - name: label for this line
    '''

    linestyles = {
        '-': 'solid',
        '--': 'dashed',
        ':': 'dotted',
        '.-': 'dotdash',
        '-.': 'dashdot'
    }
    markerstyles = {
        'o': 'circle',
        's': 'square',
        'v': 'inverted_triangle',
        '^': 'triangle',
        'x': 'x',
        '+': 'cross',
        '*': 'asterisk'
    }


    if line_handle: # if updating an existing line
        line_handle.data_source.data['x'] = x
        line_handle.data_source.data['y'] = y

    else: # create a new line
        from bokeh.models import ColumnDataSource
        source = ColumnDataSource(data=dict(x=x,y=y, name=[name]*len(x))) # an array of "name"s will have "name" show up on hover tooltip
        if linestyle in linestyles.keys(): # plot a line
            line_handle = fig.line(x, y,
                                    color = color,
                                    line_dash = linestyles[linestyle],
                                    line_width = 2,
                                    source = source,
                                    name = name,
                                )

        else: # plot scatter
            line_handle = fig.scatter(x, y,
                                    color = color,
                                    marker = markerstyles[linestyle],
                                    size = 10,
                                    source = source,
                                    name = name
                                )

    # update() # refresh plots in the notebook, doesn't work when adding new lines unfortunately
    return line_handle


def plot_html(fig):
    '''
    Plots a bokeh figure.
    Will save plot as html in a subdirectory named bokeh_plots
    Will then show the plot in an iframe in the notebook.
    This is done so plots show up again when reopening a notebook.
    You may have to "File > Trust" the notebook to see plots
    '''

    ## Set up directory for the plot files
    plots_dir = os.path.join('.','Bokeh_plots')
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.html'
    figfile = os.path.join(plots_dir, filename)

    ## Save and show figure
    bokeh.io.output_file(figfile)
    bokeh.io.save(fig)
    show_html(figfile)

    fig.name = figfile



def show(fig, show_legend=True):
    '''
    Adds a legend, then shows a bokeh plot using the normal show function.
    Uses the current kernel's ID as a dictionary key for NB_HANDLE.
    Should allow module to be used by two notebooks simultaneously.
    '''
    from bokeh.models.annotations import ColorBar

    # Check to see if plot has a colorbar
    has_colorbar = False
    for r in fig.renderers:
        if type(r) == ColorBar:
            has_colorbar = True
            break

    if show_legend and not has_colorbar:
        legend(fig)
    global NB_HANDLE
    NB_HANDLE = bokeh.io.show(fig, notebook_handle=True)
    return NB_HANDLE


def show_html(figfile, width=700, height=700):
    '''
    Shows a bokeh html figure in the notebook.
    This shouldn't be necessary after bokeh 0.12.2dev8
    '''
    disp.display(disp.HTML('<iframe src=%s width=%i height=%i></iframe>' %(figfile, width, height)))


def update():
    '''
    Replots a bokeh figure if it has been changed.
    '''
    try:
        bokeh.io.push_notebook(handle=NB_HANDLE)
    except:
        pass # This code reached if we haven't run show() yet!
