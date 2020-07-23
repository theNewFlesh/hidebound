from typing import Any, Dict, List

from schematics.types import IntType, ListType, StringType

from hidebound.core.specification_base import FileSpecificationBase
from hidebound.core.specification_base import SequenceSpecificationBase
import hidebound.core.traits as tr
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class Spec001(SequenceSpecificationBase):
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']  # type: List[str]
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'coordinate',
        'frame', 'extension'
    ]  # type: List[str]
    descriptor = ListType(
        StringType(),
        required=True,
        validators=[vd.is_descriptor, vd.is_homogenous]
    )  # type: ListType
    frame = ListType(
        IntType(),
        required=True,
        validators=[vd.is_frame]
    )  # type: ListType
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'png')]
    )  # type: ListType
    coordinate = ListType(
        ListType(IntType(), required=True, validators=[vd.is_coordinate])
    )  # type: ListType

    height = ListType(IntType(), required=True)  # type: ListType
    width = ListType(IntType(), required=True)  # type: ListType
    channels = ListType(IntType(), required=True)  # type: ListType
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels
    )  # type: Dict[str, Any]


class Spec002(SequenceSpecificationBase):
    asset_name_fields = ['project', 'specification', 'descriptor', 'version']  # type: List[str]
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'frame',
        'extension'
    ]  # type: List[str]
    frame = ListType(
        IntType(),
        required=True,
        validators=[vd.is_frame, lambda x: vd.is_gt(x, -1)]
    )  # type: ListType
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'jpg')]
    )  # type: ListType
    width = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 1024)]
    )  # type: ListType
    height = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 1024)]
    )  # type: ListType
    channels = ListType(
        IntType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 3)]
    )  # type: ListType
    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_image_channels
    )  # type: Dict[str, Any]


class Vdb001(FileSpecificationBase):
    filename_fields = [
        'project', 'specification', 'descriptor', 'version', 'extension'
    ]  # type: List[str]
    extension = ListType(
        StringType(),
        required=True,
        validators=[vd.is_extension, lambda x: vd.is_eq(x, 'vdb')]
    )  # type: ListType
# ------------------------------------------------------------------------------


SPECIFICATIONS = [
    Spec001,
    Spec002,
    Vdb001,
]  # type: List[type]
