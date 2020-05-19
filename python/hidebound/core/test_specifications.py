from schematics.types import IntType, ListType, StringType

from hidebound.core.specification_base import FileSpecificationBase
from hidebound.core.specification_base import SequenceSpecificationBase
import hidebound.core.traits as tr
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class Spec001(SequenceSpecificationBase):
    name = 'spec001'
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
#     file_traits = dict(
#         width=tr.get_image_width
#     )


class Spec002(SequenceSpecificationBase):
    name = 'spec002'
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'frame',
        'extension'
    ]
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
    frame = ListType(
        IntType(),
        required=True,
        validators=[vd.is_frame, lambda x: vd.is_gt(x, -1)]
    )
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'exr')]
    )
    file_traits = dict(
        width=tr.get_image_width
    )


class Vdb001(FileSpecificationBase):
    name = 'vdb001'
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'extension'
    ]
    extension = StringType(
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'vdb')]
    )
# ------------------------------------------------------------------------------


SPECIFICATIONS = [
    Spec001,
    Spec002,
    Vdb001,
]
