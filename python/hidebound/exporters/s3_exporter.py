from typing import Any, List

from io import BytesIO
import json

from botocore.exceptions import ClientError
from schematics.types import StringType
import boto3 as boto

from hidebound.exporters.exporter_base import ExporterBase, ExporterConfigBase
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class S3Config(ExporterConfigBase):
    '''
    A class for validating configurations supplied to S3Exporter.

    Attributes:
        name (str): Name of exporter. Must be 's3'.
        access_key (str): AWS access key.
        secret_key (str): AWS secret key.
        bucket (str): AWS bucket name.
        region (str): AWS region name. Default: us-east-1.
    '''
    name = StringType(
        required=True, validators=[lambda x: vd.is_eq(x, 's3')]
    )  # type: StringType
    access_key = StringType(required=True)  # type: StringType
    secret_key = StringType(required=True)  # type: StringType
    bucket = StringType(
        required=True, validators=[vd.is_bucket_name]
    )  # type: StringType
    region = StringType(
        required=True, validators=[vd.is_aws_region]
    )  # type: StringType


class S3Exporter(ExporterBase):
    @staticmethod
    def from_config(config):
        # type: (dict) -> S3Exporter
        '''
        Construct a S3Exporter from a given config.

        Args:
            config (dict): Config dictionary.

        Raises:
            DataError: If config is invalid.

        Returns:
            S3Exporter: S3Exporter instance.
        '''
        return S3Exporter(**config)

    def __init__(
        self,
        access_key,
        secret_key,
        bucket,
        region,
        metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk'],
        **kwargs,
    ):
        # type: (str, str, str, str, List[str], Any) -> None
        '''
        Constructs a S3Exporter instances and creates a bucket with given name
        if it does not exist.

        Args:
            access_key (str): AWS access key.
            secret_key (str): AWS secret key.
            bucket (str): AWS bucket name.
            region (str): AWS region.
            metadata_types (list, optional): List of metadata types for export.
                Default: [asset, file, asset-chunk, file-chunk].

        Raises:
            DataError: If config is invalid.
        '''
        super().__init__(metadata_types=metadata_types)

        config = dict(
            name='s3',
            access_key=access_key,
            secret_key=secret_key,
            bucket=bucket,
            region=region,
            metadata_types=metadata_types,
        )
        S3Config(config).validate()
        # ----------------------------------------------------------------------

        session = boto.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._bucket = session.resource('s3').Bucket(bucket)

        try:
            session.resource('s3').meta.client.head_bucket(Bucket=bucket)
        except ClientError:
            self._bucket.create(
                CreateBucketConfiguration={'LocationConstraint': region}
            )

    def _export_content(self, metadata):
        # type: (dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        self._bucket.upload_file(
            metadata['filepath'],
            'hidebound/content/' + metadata['filepath_relative'],
        )

    def _export_asset(self, metadata):
        # type: (dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/asset.

        Args:
            metadata (dict): Asset metadata.
        '''
        self._bucket.upload_fileobj(
            BytesIO(json.dumps(metadata, indent=4).encode('utf-8')),
            'hidebound/metadata/asset/' + metadata['asset_id'] + '.json',
        )

    def _export_file(self, metadata):
        # type: (dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        self._bucket.upload_fileobj(
            BytesIO(json.dumps(metadata, indent=4).encode('utf-8')),
            'hidebound/metadata/file/' + metadata['file_id'] + '.json',
        )

    def _export_asset_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports list of asset metadata to a single file in
        hidebound/metadata/asset-chunk.

        Args:
            metadata (list[dict]): Asset metadata.
        '''
        self._bucket.upload_fileobj(
            BytesIO(json.dumps(metadata).encode('utf-8')),
            f'hidebound/metadata/asset-chunk/hidebound-asset-chunk_{self._time}.json',
        )

    def _export_file_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports list of file metadata to a single file in
        hidebound/metadata/file-chunk.

        Args:
            metadata (list[dict]): File metadata.
        '''
        self._bucket.upload_fileobj(
            BytesIO(json.dumps(metadata).encode('utf-8')),
            f'hidebound/metadata/file-chunk/hidebound-file-chunk_{self._time}.json',
        )
