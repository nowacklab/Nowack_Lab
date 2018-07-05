"""Python API for composing notebook elements

The Python representation of a notebook is a nested structure of
dictionary subclasses that support attribute access
(ipython_genutils.ipstruct.Struct). The functions in this module are merely
helpers to build the structs in the right form.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from ..notebooknode import from_dict, NotebookNode

# Change this when incrementing the nbformat version
nbformat = 4
nbformat_minor = 0
nbformat_schema = 'nbformat.v4.schema.json'


def validate(node, ref=None):
    """validate a v4 node"""
    from .. import validate
    return validate(node, ref=ref, version=nbformat)


def new_output(output_type, data=None, **kwargs):
    """Create a new output, to go in the ``cell.outputs`` list of a code cell."""
    output = NotebookNode(output_type=output_type)

    # populate defaults:
    if output_type == 'stream':
        output.name = u'stdout'
        output.text = u''
    elif output_type in {'execute_result', 'display_data'}:
        output.metadata = NotebookNode()
        output.data = NotebookNode()
    # load from args:
    output.update(from_dict(kwargs))
    if data is not None:
        output.data = from_dict(data)
    # validate
    validate(output, output_type)
    return output


def output_from_msg(msg):
    """Create a NotebookNode for an output from a kernel's IOPub message.

    Returns
    -------

    NotebookNode: the output as a notebook node.

    Raises
    ------

    ValueError: if the message is not an output message.

    """
    msg_type = msg['header']['msg_type']
    content = msg['content']

    if msg_type == 'execute_result':
        return new_output(output_type=msg_type,
            metadata=content['metadata'],
            data=content['data'],
            execution_count=content['execution_count'],
        )
    elif msg_type == 'stream':
        return new_output(output_type=msg_type,
            name=content['name'],
            text=content['text'],
        )
    elif msg_type == 'display_data':
        return new_output(output_type=msg_type,
            metadata=content['metadata'],
            data=content['data'],
        )
    elif msg_type == 'error':
        return new_output(output_type=msg_type,
            ename=content['ename'],
            evalue=content['evalue'],
            traceback=content['traceback'],
        )
    else:
        raise ValueError("Unrecognized output msg type: %r" % msg_type)


def new_code_cell(source='', **kwargs):
    """Create a new code cell"""
    cell = NotebookNode(
        cell_type='code',
        metadata=NotebookNode(),
        execution_count=None,
        source=source,
        outputs=[],
    )
    cell.update(from_dict(kwargs))

    validate(cell, 'code_cell')
    return cell

def new_markdown_cell(source='', **kwargs):
    """Create a new markdown cell"""
    cell = NotebookNode(
        cell_type='markdown',
        source=source,
        metadata=NotebookNode(),
    )
    cell.update(from_dict(kwargs))

    validate(cell, 'markdown_cell')
    return cell

def new_raw_cell(source='', **kwargs):
    """Create a new raw cell"""
    cell = NotebookNode(
        cell_type='raw',
        source=source,
        metadata=NotebookNode(),
    )
    cell.update(from_dict(kwargs))

    validate(cell, 'raw_cell')
    return cell

def new_notebook(**kwargs):
    """Create a new notebook. Customization by BTS, 8/19/2016"""
### START EDITS
    md0 = new_markdown_cell('# Setup')
    md1 = new_markdown_cell('## Import everything and set up notebook for plotting')
    cc1 = new_code_cell('\
from Nowack_Lab.Instruments import *\n\
from Nowack_Lab.Measurements import *\n\
from Nowack_Lab.Utilities import *\n\
%matplotlib notebook\
')
    md2 = new_markdown_cell('## Create instrument objects')
    cc2 = new_code_cell('\
daq = nidaq.NIDAQ()\n\
li = lockin.SR830(\'GPIB::08::INSTR\')\n\
pz = piezos.Piezos(daq, chan_out = {\'x\': 1, \'y\':2, \'z\':0})\n\
mont = montana.Montana()\n\
atto = attocube.ANC350(mont)\n\
array = squidarray.SquidArray()\n\
instruments = dict(\n\
                    nidaq = daq,\n\
                    lockin = li,\n\
                    piezos = pz,\n\
                    montana = mont,\n\
                    attocube = atto,\n\
                    squidarray = array\n\
                )\
')
    md3 = new_markdown_cell('## Reload plane and array (on kernel restart)')
    cc3 = new_code_cell('\
plane = planefit.load_last(instruments)\n\
array = squidarray.SquidArray(load=True)\n\
instruments[\'squidarray\'] = array\
')
    md4 = new_markdown_cell('# Find the surface')
    md5 = new_markdown_cell('## Approach with attocubes\n(Edit with desired amount of movement)')
    cc5 = new_code_cell('atto.z.move(100)')
    md6 = new_markdown_cell('## Do a touchdown (if you want)')
    cc6 = new_code_cell('td = touchdown.Touchdown(instruments, cap_input = 0)\ntd.do()')
    md7 = new_markdown_cell('## Take a plane')
    cc7 = new_code_cell('plane = planefit.Planefit(instruments, cap_input=0)\nplane.do()')
    md8 = new_markdown_cell('# Start scanning')
    cc8 = new_code_cell('\
scan = scanplane.Scanplane(\n\
                            instruments,\n\
                            span = [400, 400],\n\
                            center = [0,0],\n\
                            numpts = [20,20],\n\
                            plane = plane,\n\
                            scanheight = 5,\n\
                            sig_in = 1,\n\
                            cap_in = 0,\n\
                            sig_in_ac_x = 2,\n\
                            sig_in_ac_y = 3\n\
)\n\
scan.do()\
')
### END EDITS BUT LOOK BELOW
    nb = NotebookNode(
        nbformat=nbformat,
        nbformat_minor=nbformat_minor,
        metadata=NotebookNode(),
        # cells=[],
        cells=[md0, md1, cc1, md2, cc2, md3, cc3, md4, md5, cc5, md6, cc6, md7, cc7, md8, cc8], #EDITED BTS 8/19/16
    )
    nb.update(from_dict(kwargs))
    validate(nb)
    return nb
