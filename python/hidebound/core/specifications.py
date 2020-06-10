from schematics.types import IntType, ListType, StringType

import hidebound.core.validators as vd
import hidebound.core.traits as tr
from hidebound.core.specification_base import SequenceSpecificationBase
# ------------------------------------------------------------------------------


'''
The specifications module house all the specifications for all hidebound projects.

All specifications used in production should be subclassed from the base classes
found in the specification_base module. All class attributes must have a
"get_[attribute]" function in the traits module and should have one or more
validators related to the value of that trait (especially if required).
'''


class Raw001(SequenceSpecificationBase):
    '''
    Raw JPEG sequences with 1 or 3 channels.

    Attributes:
        filename_fields (list[str]): project, specification, descriptor,
            version, frame, extension
        asset_name_fields (list[str]): project, specification, descriptor,
            version,
        height (int): Image height. Must be 1024.
        width (int): Image width. Must be 1024.
        extension (str): File extension. Must be "png".
    '''
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'frame',
        'extension'
    ]
    height = ListType(IntType(), required=True)
    width = ListType(IntType(), required=True)
    frame = ListType(IntType(), required=True, validators=[vd.is_frame])
    channels = ListType(
        IntType(), required=True, validators=[lambda x: vd.is_in(x, [1, 3])]
    )
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'jpg')]
    )
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels,
    )


class Raw002(SequenceSpecificationBase):
    '''
    Raw JPEG sequences with 1 or 3 channels and coordinates.

    Attributes:
        filename_fields (list[str]): project, specification, descriptor,
            version, frame, extension
        asset_name_fields (list[str]): project, specification, descriptor,
            version,
        height (int): Image height. Must be 1024.
        width (int): Image width. Must be 1024.
        extension (str): File extension. Must be "png".
    '''
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'coordinate',
        'frame', 'extension'
    ]
    height = ListType(IntType(), required=True)
    width = ListType(IntType(), required=True)
    frame = ListType(IntType(), required=True, validators=[vd.is_frame])
    coordinate = ListType(
        ListType(IntType(), validators=[vd.is_coordinate]), required=True,
    )
    channels = ListType(
        IntType(), required=True, validators=[lambda x: vd.is_in(x, [1, 3])]
    )
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'jpg')]
    )
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels,
    )


SPECIFICATIONS = [
    Raw001,
    Raw002,
]
