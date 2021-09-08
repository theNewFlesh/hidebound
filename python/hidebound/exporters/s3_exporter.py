from typing import Dict

from io import BytesIO
import json

from schematics import Model
from schematics.types import StringType
import boto3 as boto

from hidebound.exporters.exporter_base import ExporterBase
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class S3Config(Model):
    '''
    A class for validating configurations supplied to S3Exporter.

    Attributes:
        access_key (str): AWS access key.
        secret_key (str): AWS secret key.
        bucket (str): AWS bucket name.
        region (str): AWS region name. Default: us-east-1.
    '''
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
        # type: (Dict) -> S3Exporter
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
    ):
        # type: (str, str, str, str) -> None
        '''
        Constructs a S3Exporter instances and creates a bucket with given name
        if it does not exist.

        Args:
            access_key (str): AWS access key.
            secret_key (str): AWS secret key.
            bucket (str): AWS bucket name.
            region (str): AWS region.

        Raises:
            DataError: If config is invalid.
        '''
        config = dict(
            access_key=access_key,
            secret_key=secret_key,
            bucket=bucket,
            region=region,
        )
        S3Config(config).validate()
        # ----------------------------------------------------------------------

        session = boto.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._bucket = session.resource('s3').Bucket(bucket)
        if self._bucket.creation_date is None:
            self._bucket.create(
                CreateBucketConfiguration={'LocationConstraint': region}
            )

    def _export_asset(self, metadata):
        # type: (Dict) -> None
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
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        self._bucket.upload_fileobj(
            BytesIO(json.dumps(metadata, indent=4).encode('utf-8')),
            'hidebound/metadata/file/' + metadata['file_id'] + '.json',
        )
        self._bucket.upload_file(
            metadata['filepath'],
            'hidebound/content/' + metadata['filepath_relative'],
        )

    def _export_asset_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from single asset log in hidebound/logs/asset.

        Args:
            metadata (dict): Asset log.
        '''
        self._bucket.upload_fileobj(
            BytesIO(metadata['content'].encode('utf-8')),
            'hidebound/logs/asset/' + metadata['filename'],
        )

    def _export_file_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from single file log in hidebound/logs/file.

        Args:
            metadata (dict): Asset log.
        '''
        self._bucket.upload_fileobj(
            BytesIO(metadata['content'].encode('utf-8')),
            'hidebound/logs/file/' + metadata['filename'],
        )
