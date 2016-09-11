import bokeh.io, numpy as np, os, datetime
import IPython.display as disp
from ..utilities import reject_outliers_quick, nanmin, nanmax

class Figure():
    '''
    Figure class. Contains a bokeh figure and notebook handle for plotting.
    '''
    def __init__(self, fig):
        self.fig = fig
        self.nb_handle = None


def init_notebook():
    '''
    Tell Bokeh to plot things in the notebook.
    Not necessary if you use the show function defined here.
    '''
    bokeh.io.output_notebook(hide_banner=True)


def auto_bounds(fig,x,y, square=False, hard_bounds=False):
    '''
    fig = a Figure object
    Given x-y data, sets the x and y axis ranges on the figure.
    If square=True, Makes x and y ranges the same, taking the larger of the two.
    '''
    from bokeh.models.ranges import Range1d

    ## If lists, convert to arrays
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)
    xmin = x.min()
    ymin = y.min()
    xmax = x.max()
    ymax = y.max()

    x_range = xmax-xmin
    y_range = ymax-ymin
    if square:
        bigger_range = max(x_range, y_range)
        x_bound_l = xmin - (bigger_range-x_range)/2
        x_bound_u = xmax + (bigger_range-x_range)/2
        y_bound_l = ymin - (bigger_range-y_range)/2
        y_bound_u = ymax + (bigger_range-y_range)/2
    else:
        x_bound_l = xmin
        x_bound_u = xmax
        y_bound_l = ymin
        y_bound_u = ymax

    # fig.fig.x_range.set(start=x_bound_l, end=x_bound_u)
    # fig.fig.y_range.set(start=y_bound_l, end=y_bound_u)

    if hard_bounds:
        fig.fig.x_range.set(bounds = (x_bound_l,x_bound_u))
        fig.fig.y_range.set(bounds = (y_bound_l,y_bound_u))

    fig.fig.x_range.start = -10
    fig.fig.x_range.end = 10
    fig.fig.y_range.start = -10 # NEEDS TO DO THIS TO UPDATE PROPERLY... DUMB DUMB DUMB
    fig.fig.y_range.end = 10
    import time
    time.sleep(.05) # Needs to be here. I KNOW, SO DUMB. WAT. JUST WOW.

    fig.fig.x_range.start = x_bound_l
    fig.fig.x_range.end = x_bound_u
    fig.fig.y_range.start = y_bound_l
    fig.fig.y_range.end = y_bound_u
    update(fig)

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


def clim(fig, l=None, u=None):
    '''
    fig = a Figure object
    Update colorscale limits for a bokeh figure.
    `l` and `u` are lower and upper bounds.
    If None, will autoscale the limits.
    '''
    # Get the plot data
    data = get_image_data(fig.fig)
    # filtered_data = reject_outliers(data) # takes a long time...
    filtered_data = reject_outliers_quick(data)

    # Set lower and upper automatically if not specified
    if l == None:
        l = nanmin(filtered_data) # ignore nans

    if u == None:
        u = nanmax(filtered_data) # ignore nans

    im = get_glyph_renderer(fig.fig) # Get image renderer

    # Set color limits in image
    im.glyph.color_mapper.low = l
    im.glyph.color_mapper.high = u

    cb = get_colorbar_renderer(fig.fig) # Get colorbar renderer

    # Set colorbar limits
    if cb:
        cb.color_mapper.low = l
        cb.color_mapper.high = u

    # Update everything
    update(fig)


def colorbar(fig, cmap, title=None):
    '''
    Adds a colorbar to a bokeh figure.
    fig: the Figure object
    title: title for colorbar
    cmap: name of desired bokeh or mpl colormap
    '''
    from bokeh.models import LinearColorMapper
    from bokeh.models.annotations import ColorBar

    data = get_image_data(fig.fig)

    color_mapper = LinearColorMapper(low=data.min(), high=data.max(), palette=choose_cmap(cmap))

    cb = ColorBar(color_mapper=color_mapper,
                    location=(0,0),
                    orientation='vertical',
                    padding=20,
                    margin=0,
                    title=title)

    cb.major_label_text_font_size = '12pt'
    cb.major_label_text_align = 'left'

    fig.fig.add_layout(cb, 'left') # 'right' make plot squished with widgets

    return cb


def colorbar_slider(fig):
    '''
    fig = a Figure object
    Adds interactive sliders and text input boxes for the colorbar.
    Returns a layout object to be put into a gridplot
    '''
    cb = get_colorbar_renderer(fig.fig)
    data = get_image_data(fig.fig)
    data = reject_outliers_quick(data)
    datamin = nanmin(data)
    datamax = nanmax(data)
    im = get_glyph_renderer(fig.fig) # Get image renderer

    from bokeh.models import CustomJS, Slider, TextInput
    from bokeh.models.widgets import Button
    from bokeh.layouts import widgetbox

    model = Slider() # trick it into letting datamin and datamax into CustomJS
    model.tags.append(datamin) # Hide these in here
    model.tags.append(datamax)

    callback_u = CustomJS(args=dict(cb=cb, im=im, model=model), code="""
        var cm = cb.color_mapper;
        var upp = upper_slider.get('value');
        upper_input.value = upp.toString()
        lower_slider.end = upp
        cm.high = upp;
        im.glyph.color_mapper.high = upp;
        if (cm.low >= cm.high){
        cm.low = upp/1.1 // to prevent limits being the same
        im.glyph.color_mapper.low = low/1.1;
        }
        if (upp > model.tags[1]){
            upper_slider.end = upp
        }
        """)

    callback_l = CustomJS(args=dict(cb=cb, im=im, model=model), code="""
        var cm = cb.color_mapper;
        var low = lower_slider.get('value');
        lower_input.value = low.toString()
        upper_slider.start = low
        cm.low = low;
        im.glyph.color_mapper.low = low;
        if (cm.high <=  cm.low){
        cm.high = low*1.1 // to prevent limits being the same
        im.glyph.color_mapper.high = low*1.1;
        }
        if (low < model.tags[0]){
            lower_slider.start = low
        }""")

    callback_ut = CustomJS(args=dict(cb=cb, im=im, model=model), code="""
        var cm = cb.color_mapper;
        var upp = parseFloat(upper_input.get('value'));
        upper_slider.value = upp
        cm.high = upp;
        im.glyph.color_mapper.high = upp;
        if (cm.low >=  cm.high){
        cm.low = upp/1.1 // to prevent limits being the same
        im.glyph.color_mapper.low = upp/1.1;
        }
        if (upp > model.tags[1]){
            upper_slider.end = upp
        }
        """)

    callback_lt = CustomJS(args=dict(cb=cb, im=im, model=model), code="""
        var cm = cb.color_mapper;
        var low = parseFloat(lower_input.get('value'));
        lower_slider.value = low
        cm.low = low;
        im.glyph.color_mapper.low = low;
        if (cm.high <=  cm.low){
        cm.high = low*1.1 // to prevent limits being the same
        im.glyph.color_mapper.high = low*1.1;
        }
        if (low < model.tags[0]){
            lower_slider.start = low
        }
        """)

    callback_reset_js = CustomJS(args=dict(cb=cb, im=im, model=model), code="""
        var cm = cb.color_mapper;
        var low = model.tags[0];
        var high = model.tags[1];
        low = parseFloat(low.toPrecision(3)) // 3 sig figs
        high = parseFloat(high.toPrecision(3)) // 3 sig figs
        lower_slider.value = low;
        lower_slider.set('step', (high-low)/50);
        cm.low = low;
        upper_slider.value = high;
        upper_slider.set('step', (high-low)/50);
        cm.high = high;
        im.glyph.color_mapper.low = low;
        im.glyph.color_mapper.high = high;
        lower_input.value = low.toString();
        upper_input.value = high.toString();
        lower_slider.start = low;
        lower_slider.end = high;
        upper_slider.start = low;
        upper_slider.end = high;
        model.trigger('change')
        cb_obj.trigger('change)')
    """)

    reset_button = Button(label='Reset', callback = callback_reset_js)

    def callback_reset(*args, **kwargs):
        from IPython.display import Javascript, display

        # display(callback_reset_js)
        # callback_reset_js.name = None
        # callback_reset_js.name = 'test'
        # display('Plot updated, press reset to rescale!')
        # cb.color_mapper.low = datamin
        # cb.color_mapper.high = datamax
        # im.glyph.color_mapper.low = datamin
        # im.glyph.color_mapper.high = datamax
        # lower_slider.start = datamin
        # lower_slider.end = datamax
        # lower_slider.value = datamin
        # upper_slider.start = datamin
        # upper_slider.end = datamax
        # lower_slider.value = datamax
        # lower_input.value = str(datamin)
        # upper_input.value = str(datamax)
        # update()
        # fig.text(x=0,y=0,text='Plot updated, press reset to rescale!')
        # reset_button.label='Reset: Data changed! Press me!'

    # reset_button.trigger('clicks',0,1)
    reset_button.on_click(callback_reset)

    # def callback_die(attr, old, new):
    #     from IPython.display import display
    #     display('yoooo')
    #     display(old)
    #     display(new)
    #     raise Exception()
    # exception_button = Button(label='KILL ME')
    # exception_button.on_click(callback_die)

    lower_slider = Slider(start=datamin, end=datamax, value=datamin, step=(datamax-datamin)/50, # smallest step is 1e-5
                        title="Lower lim", callback=callback_l)
    lower_slider.width=100

    upper_slider = Slider(start=datamin, end=datamax, value=datamax, step=(datamax-datamin)/50,
                         title="Upper lim", callback=callback_u)
    upper_slider.width=100

    lower_input = TextInput(callback=callback_lt, value = str(datamin), width=50)
    upper_input = TextInput(callback=callback_ut, value = str(datamax), width=50)

    # add all of these widgets as arguments to the callback functions
    for callback in ['l', 'u', 'lt', 'ut', 'reset_js']:
        for widget in ['lower_slider', 'upper_slider','lower_input','upper_input', 'reset_button']:
            exec('callback_%s.args["%s"] = %s' %(callback, widget, widget))

    wb = widgetbox([upper_slider, upper_input, lower_slider, lower_input, reset_button], width=100, sizing_mode = 'stretch_both')
    return wb


def figure(title=None, xlabel=None, ylabel=None, show_legend=True, x_axis_type='linear', y_axis_type='log'):
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
                toolbar_sticky=False,
                x_axis_type=x_axis_type,
                y_axis_type=y_axis_type
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
    fig.title.text_font_size = '20pt'
    # X
    fig.xaxis.axis_label = xlabel
    fig.xaxis.axis_label_text_font_size = '14pt'
    fig.xaxis.major_label_text_font_size = '10pt'
    fig.xaxis.axis_label_text_font_style = 'bold'
    # Y
    fig.yaxis.axis_label = ylabel
    fig.yaxis.axis_label_text_font_size = '14pt'
    fig.yaxis.major_label_text_font_size = '10pt'
    fig.yaxis.axis_label_text_font_style = 'bold'


    fig.min_border_bottom = 100 # add some padding for gridplots

    ## Add legend
    if show_legend:
        legend(fig)

    return Figure(fig)


def get_colorbar_renderer(fig):
    '''
    Returns the colorbar for a given Figure.
    '''
    from bokeh.models.annotations import ColorBar

    for r in fig.fig.renderers:
        if type(r) == ColorBar:
            cb = r
            return cb


def get_glyph_renderer(fig):
    '''
    Gets one glyph renderer for a given Figure.
    Useful for when you have one thing plotted (like an image).
    Not useful if multipl glyph renderers
    '''
    from bokeh.models import GlyphRenderer

    for r in fig.fig.renderers:
        if type(r) == GlyphRenderer:
            im = r
            return im

def get_image_data(fig):
    '''
    Returns the data array for a plotted image.
    '''
    im = get_glyph_renderer(fig.fig)
    return im.data_source.data['image'][0]


def image(fig, x, y, z, show_colorbar = True, z_title=None, im_handle=None, cmap='Viridis256', name=None, slider_handle=None):
    '''
    Adds a 2D image to a Bokeh plot
    fig: Figure to plot on
    x,y,z: x and y are from np.meshgrid, 2D matrix in Z
    colorbar: whether or not to plot the colorbar
    z_title: title for colorbar
    im_handle: Pass the handle for an existing image to update it.
    cmap: colormap. Can use either bokeh palette or matplotlib colormap names
    name: name for the image
    slider_handle: slider widgets handle, will update this as well
    '''
    cb_handle = None


    if im_handle:
        im_handle.data_source.data['image'][0] = z
        im_handle.data_source.update()
    else:

        ## If lists, convert to arrays
        if type(x) == list:
            x = np.array(x)
        if type(y) == list:
            y = np.array(y)
        xmin = x.min()
        ymin = y.min()
        xmax = x.max()
        ymax = y.max()

        ## Fix axis limits ## Temporary aspect ratio fix: make a squarish plot and make x/y equal lengths
        auto_bounds(fig, x, y, square=True, hard_bounds=True)

        ## Plot it
        im_handle = fig.fig.image(image=[z], x=xmin, y =ymin, dw=(xmax-xmin), dh=(ymax-ymin), palette = choose_cmap(cmap), name=name)

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
            cb_handle = colorbar(fig.fig, cmap, title=z_title)

    if slider_handle:
        data = get_image_data(fig.fig)
        data = reject_outliers_quick(data)
        for child in slider_handle.children[0:-1]: #exclude the button
            child.callback.args['model'].tags[0] = nanmin(data)
            child.callback.args['model'].tags[1] = nanmax(data)
        # slider_handle.children[-1].callback.trigger('name','old','new')
        slider_handle.children[-1].clicks = 0
        slider_handle.children[-1].clicks = 1 # Fake button click for callback
        slider_handle.children[-1].callback.args['model'].tags.append('hey')

    ## Fix colors
    clim(fig.fig) # autoscale colors (filtering outliers)

    return im_handle


def legend(fig, labels=None):
    '''
    Adds a legend to a Bokeh plot.
    fig: Figure the legend will be plotted next to
    labels: list of labels for all lines (in order of plotting them). By default, uses the "name" of each line plotted.
    loc: location of legend relative to plot
    '''
    from bokeh.models.annotations import Legend
    from bokeh.models.renderers import GlyphRenderer
    from bokeh.models.glyphs import Line

    lines = []
    for r in fig.fig.renderers: # This finds all the lines or scatter plots
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

    fig.fig.add_layout(leg, 'right')

    return leg


def line(fig, x, y, line_handle=None, color='black', linestyle='-', name=None):
    '''
    Adds a line to a Bokeh plot.
    Must specify Figure and x and y data.
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

    new_line = True
    if line_handle: # if updating an existing line
        line_handle.data_source.data['x'] = x
        line_handle.data_source.data['y'] = y
        new_line = False

    else: # create a new line
        from bokeh.models import ColumnDataSource
        source = ColumnDataSource(data=dict(x=x,y=y, name=[name]*len(x))) # an array of "name"s will have "name" show up on hover tooltip
        if linestyle in linestyles.keys(): # plot a line
            line_handle = fig.fig.line(x, y, source = source)

        else: # plot scatter
            line_handle = fig.fig.scatter(x, y, marker=markerstyles[linestyle],
            source = source)

    if linestyle in linestyles.keys():
        line_handle.glyph.line_dash = linestyles[linestyle]
        line_handle.glyph.line_width = 2
    else:
        if not new_line:
            print('Unfortunately can\'t change marker type!')
        line_handle.glyph.size = 10
    line_handle.glyph.line_color = color
    line_handle.name = name

    update(fig)

    auto_bounds(fig, x, y)


    # update() # refresh plots in the notebook, doesn't work when adding new lines unfortunately
    return line_handle


def plot_grid(figs, width=700, height=700):
    '''
    Sets up a grid of bokeh plots.
    `figs` is a list of rows of figures or widgets. (not Figure object defined here)
    For example, a 2x2 grid of plots is [[f1, f2],[f3,f4]]
    Width and height are the dimensions of the whole grid.
    Doesn't quite work well with widgets or colorbars. Best to plot these separately.
    '''
    from bokeh.layouts import gridplot
    from bokeh.plotting.figure import Figure as Fig

    # Scale all plots, keeping aspect ratio constant.
    numrows = len(figs)
    for row in figs:
        numfigs = 0
        for fig in row: #count the number of figures (excluding widgets)
            numfigs += 1 if type(fig) is Fig else 0
        for fig in row:
            try:
                max_width = fig.plot_width
                max_height = fig.plot_height
                if fig.plot_width > int(width/numfigs):
                    max_width = int(width/numfigs)
                if fig.plot_height > int(height/numrows):
                    max_height = int(height/numrows)

                scale_factor_width = max_width/fig.plot_width
                scale_factor_height = max_height/fig.plot_height
                scale_factor = min(scale_factor_width, scale_factor_height)

                fig.plot_width = int(scale_factor*fig.plot_width)
                fig.plot_height = int(scale_factor*fig.plot_height)
            except:
                pass # do nothing with widgets and cross fingers

    ## Center plots - NOT WORKING
    # for row in figs:
    #     numfigs = len(row)
    #     total_width = 0
    #     for fig in row:
    #         total_width += fig.plot_width
    #     row[0].min_border_left = int((width-total_width)/2) # pad left
    #     row[-1].min_border_right = int((width-total_width)/2) # pad right

    return Figure(gridplot(figs, merge_tools=True))


def plot_html(fig):
    '''
    Plots a bokeh figure.
    fig = Figure
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
    bokeh.io.save(fig.fig)
    show_html(figfile)

    fig.fig.name = figfile


def save(fig, figfile=None):
    '''
    Saves bokeh plots to HTML. By default, in ./Bokeh_plots
    '''
    if figfile is None:
        ## Set up directory for the plot files
        plots_dir = os.path.join('.','Bokeh_plots')
        if not os.path.exists(plots_dir):
            os.makedirs(plots_dir)
        filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.html'
        figfile = os.path.join(plots_dir, filename)

    ## Save and show figure
    from jinja2 import Template

    from bokeh.embed import components
    from bokeh.resources import INLINE

    plots = {'fig':fig.fig}
    script, div = components(plots)

    template = Template('''<!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Bokeh Scatter Plots</title>
            {{ js_resources }}
            {{ css_resources }}
            {{ script }}
            <style>
                .embed-wrapper {
                    width: 50%;
                    height: 400px;
                    margin: auto;
                }
            </style>
        </head>
        <body>
            {% for key in div.keys() %}
                <div class="embed-wrapper">
                {{ div[key] }}
                </div>
            {% endfor %}
        </body>
    </html>
    ''')
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    bokeh_html = template.render(js_resources=js_resources,
                       css_resources=css_resources,
                       script=script,
                       div=div)

    with open(figfile, 'w') as f:
        f.write(bokeh_html)


def show(fig, show_legend=True):
    '''
    Shows a bokeh plot or gridplot using the normal show function.
    '''
    fig.nb_handle = bokeh.io.show(fig.fig, notebook_handle=True)


def show_html(figfile, width=700, height=700):
    '''
    Shows a bokeh html figure in the notebook.
    This shouldn't be necessary after bokeh 0.12.2dev8
    '''
    disp.display(disp.HTML('<iframe src=%s width=%i height=%i></iframe>' %(figfile, width, height)))


def update(fig):
    '''
    Replots a bokeh Figure if it has been changed using bokeh.io.push_notebook.
    Note: changes pushed to the notebook will NOT stay there when reopening a saved notebook.
    Once done updating, make sure you `show` again.
    '''
    try:
        bokeh.io.push_notebook(handle=fig.nb_handle)
    except:
        print('nb_handle note found... possibly you need to look in the grid object?')
