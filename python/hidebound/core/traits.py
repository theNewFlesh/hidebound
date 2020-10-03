from typing import Union

import os
from pathlib import Path
import re

import skimage.io

import hidebound.core.tools as tools
# ------------------------------------------------------------------------------


'''
The traits module contains functions that return file traits give a filepath.
These traits are used for validation of specifications.
'''


def get_image_width(filepath):
    # type: (Union[str, Path]) -> int
    '''
    Gets the width of the given image.

    Args:
        filepath (str or Path): filepath to image file.

    Returns:
        int: Image width.
    '''
    if re.search('exr', os.path.split(filepath)[-1], re.I):
        metadata = tools.read_exr_header(filepath)
        win = metadata['dataWindow']
        return (win.max.x - win.min.x) + 1

    img = skimage.io.imread(Path(filepath).as_posix())
    return img.shape[1]


def get_image_height(filepath):
    # type: (Union[str, Path]) -> int
    '''
    Gets the height of the given image.

    Args:
        filepath (str or Path): filepath to image file.

    Returns:
        int: Image height.
    '''
    if re.search('exr', os.path.split(filepath)[-1], re.I):
        metadata = tools.read_exr_header(filepath)
        win = metadata['dataWindow']
        return (win.max.y - win.min.y) + 1

    img = skimage.io.imread(Path(filepath).as_posix())
    return img.shape[0]


def get_num_image_channels(filepath):
    # type: (Union[str, Path]) -> int
    '''
    Gets the number of channels of the given image.

    Args:
        filepath (str or Path): filepath to image file.

    Returns:
        int: Number of channels.
    '''
    if re.search('exr', os.path.split(filepath)[-1], re.I):
        metadata = tools.read_exr_header(filepath)
        return len(metadata['channels'])

    img = skimage.io.imread(Path(filepath).as_posix())
    if len(img.shape) > 2:
        return img.shape[2]
    return 1
