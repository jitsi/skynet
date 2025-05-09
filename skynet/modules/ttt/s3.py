from botocore.config import Config

from skynet.env import (
    skynet_s3_access_key,
    skynet_s3_bucket,
    skynet_s3_endpoint,
    skynet_s3_region,
    skynet_s3_secret_key,
)
from skynet.logs import get_logger

log = get_logger(__name__)


class S3:
    def __init__(self):
        import aioboto3

        self.session = aioboto3.Session(
            aws_access_key_id=skynet_s3_access_key,
            aws_secret_access_key=skynet_s3_secret_key,
            region_name=skynet_s3_region,
        )

    async def download_file(self, filename):
        try:
            async with self.session.resource('s3', endpoint_url=skynet_s3_endpoint) as s3:
                obj = await s3.Object(bucket_name=skynet_s3_bucket, key=filename)

                with open(filename, 'wb') as data:
                    await obj.download_fileobj(data)
                    log.info(f'Downloaded file from S3: {filename}')
        except Exception as e:
            log.error(f'Failed to download file {filename} from S3: {e}')

    async def upload_file(self, filename):
        try:
            async with self.session.resource(
                's3',
                endpoint_url=skynet_s3_endpoint,
                # https://github.com/boto/boto3/issues/4398
                config=Config(
                    request_checksum_calculation='WHEN_REQUIRED', response_checksum_validation='WHEN_REQUIRED'
                ),
            ) as s3:
                bucket = await s3.Bucket(skynet_s3_bucket)

                with open(filename, 'rb') as data:
                    await bucket.upload_fileobj(data, filename)
                    log.info(f'Uploaded file to S3: {filename}')
        except Exception as e:
            log.error(f'Failed to upload file {filename} to S3: {e}')

    async def delete_file(self, filename):
        try:
            async with self.session.resource('s3', endpoint_url=skynet_s3_endpoint) as s3:
                obj = await s3.Object(bucket_name=skynet_s3_bucket, key=filename)
                await obj.delete()
                log.info(f'Deleted file from S3: {filename}')
        except Exception as e:
            log.error(f'Failed to delete file {filename} from S3: {e}')


__all__ = ['S3']
