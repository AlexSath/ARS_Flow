from typing import Union
from types import NoneType

import numpy as np
import seaborn as sns
from seaborn.palettes import _ColorPalette
from matplotlib import colors
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def flow_violin(
    data, x, y,
    hue: Union[NoneType, str]=None,
    palette: Union[NoneType, _ColorPalette]=None,
    color: Union[NoneType, str, tuple]=None,
    order: Union[NoneType, list[str]]=None, #Pass list of values in desired order for plotting. 
    split: bool=False, #whether to split violin pairs (should be combined with hue)
    log_y_axis: bool=False,
    native_scale: bool=False, #make both axes plot numbers on a line (instead of categories)
    inner_kws: Union[bool, dict]=None,
    density_norm: str='count',
    xlabel: Union[NoneType, str]=None, 
    ylabel: Union[NoneType, str]=None,
    legend_labels: Union[NoneType, list[str]]=None,
    shift: float=0.03, # the shift that the whiskers are subjected to
    violin_linewidth: float=1,
    hue_order: Union[NoneType, list[str]]=None,
    ylim: Union[NoneType, tuple[float]]=None,
    ax: Union[NoneType, Axes]=None,
):
    if log_y_axis: data.loc[:,'log_y'] = np.log10(data[y])
    #TODO: Does log_y column need to be deleted? probably if the data dataframe is a pointer to real object (almost certainly true)

    # Need to get regular and dark palettes for violins and IQR lines, respectively
    # Will rely on whether hue is being passed
    # If hue is passed, a color palette is needed.
    # If no hue is passed, a single color is needed.
    if hue is None:
        if color is None: this_palette = sns.color_palette("pastel")
        else: this_palette = [colors.to_rgb(color)]
    else:
        if palette is None: this_palette = sns.color_palette("pastel")
        else: this_palette = palette
    dark_palette = np.clip(np.array(this_palette)-[0.25, 0.25, 0.25], a_min=0, a_max=1)

    if hue is not None and split == False: raise ValueError(f"If hues are requested, violins must be split")

    g = sns.violinplot(
        data=data,
        x=x, hue=hue,
        palette=None if hue is None else this_palette,
        color=None if hue is not None else this_palette[0],
        y='log_y' if log_y_axis else y,
        order=order, split=split,
        density_norm=density_norm,
        native_scale=native_scale,
        inner_kws={'box_width': 1.5, 'whis_width': 0} if inner_kws is None else inner_kws,
        ax=ax,
        linewidth=violin_linewidth,
        hue_order=hue_order,
    )

    if log_y_axis:
        def log_formatter(x, pos):
            return f'$10^{{{int(x)}}}$'
        # g.yaxis.set_major_locator(LogLocator(base=10))
        g.yaxis.set_major_formatter(FuncFormatter(log_formatter))
    
    if split:
        for idx, line in enumerate(g.lines):
            # idx+1 % 3 is median line; idx+2 % 3 is IQR line
            if (idx + 1) % 3 == 0: # median line
                xval, yval = line.get_data()[0], line.get_data()[1]
                line.set_visible(False)
                if idx % 2 == 0: g.scatter(x=xval-shift-0.0075, y=yval, color=dark_palette[0])
                else: g.scatter(x=xval+shift+0.0075, y=yval, color=dark_palette[1])

            if (idx + 2) % 3 == 0: # IQR line
                if idx % 2 == 1: 
                    line.set_color(dark_palette[0])
                    line.set_data(np.array(line.get_data()) - shift)
                else: 
                    line.set_color(dark_palette[1])
                    line.set_data(np.array(line.get_data()) + shift)
    else: #NOTE: Will break if there are multiple hues and no split
        for idx, line in enumerate(g.lines):
            if (idx + 1) % 3 == 0:
                xval, yval = line.get_data()[0], line.get_data()[1]
                line.set_visible(False)
                g.scatter(x=xval, y=yval, color=dark_palette[0])
            if (idx + 2) % 3 == 0: line.set_color(dark_palette[0])

    if ylim is not None:
        g.set_ybound(*ylim)
        
    if xlabel is not None: g.set_xlabel(xlabel)
    if ylabel is not None: g.set_ylabel(ylabel)
    if legend_labels is not None: g.legend(handles=g.get_legend_handles_labels()[0], labels=legend_labels)