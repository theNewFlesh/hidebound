from typing import Union

from pathlib import Path

import skimage.io
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
    img = skimage.io.imread(Path(filepath).as_posix())
    if len(img.shape) > 2:
        return img.shape[2]
    return 1
