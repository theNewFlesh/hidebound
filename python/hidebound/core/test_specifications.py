from schematics.types import IntType, ListType, StringType

from hidebound.core.specification_base import FileSpecificationBase
from hidebound.core.specification_base import SequenceSpecificationBase
import hidebound.core.traits as tr
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class Spec001(SequenceSpecificationBase):
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'coordinate',
        'frame', 'extension'
    ]
    descriptor = ListType(
        StringType(),
        required=True,
        validators=[vd.is_descriptor, vd.is_homogenous]
    )
    frame = ListType(
        IntType(),
        required=True,
        validators=[vd.is_frame]
    )
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'png')]
    )
    coordinate = ListType(
        ListType(IntType(), required=True, validators=[vd.is_coordinate])
    )

    height = ListType(IntType(), required=True)
    width = ListType(IntType(), required=True)
    channels = ListType(IntType(), required=True)
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels
    )


class Spec002(SequenceSpecificationBase):
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'frame',
        'extension'
    ]
    frame = ListType(
        IntType(),
        required=True,
        validators=[vd.is_frame, lambda x: vd.is_gt(x, -1)]
    )
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'jpg')]
    )
    width = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 1024)]
    )
    height = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 1024)]
    )
    channels = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 3)]
    )
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels
    )


class Vdb001(FileSpecificationBase):
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'extension'
    ]
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'vdb')]
    )
# ------------------------------------------------------------------------------


SPECIFICATIONS = [
    Spec001,
    Spec002,
    Vdb001,
]
