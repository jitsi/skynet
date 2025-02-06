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
        import boto3

        try:
            self.s3 = boto3.resource(
                's3',
                aws_access_key_id=skynet_s3_access_key,
                aws_secret_access_key=skynet_s3_secret_key,
                endpoint_url=skynet_s3_endpoint,
                region_name=skynet_s3_region,
            )
        except Exception as e:
            log.error(f'Failed to connect to S3: {e}')

    def download_file(self, filename):
        if not self.s3:
            return

        try:
            obj = self.s3.Object(bucket_name=skynet_s3_bucket, key=filename)

            with open(filename, 'wb') as data:
                obj.download_fileobj(data)
                log.info(f'Downloaded file from S3: {filename}')
        except Exception as e:
            log.error(f'Failed to download file from S3: {e}')

    def upload_file(self, filename):
        if not self.s3:
            return

        try:
            bucket = self.s3.Bucket(skynet_s3_bucket)

            with open(filename, 'rb') as data:
                bucket.upload_fileobj(data, filename)
                log.info(f'Uploaded file to S3: {filename}')
        except Exception as e:
            log.error(f'Failed to upload file to S3: {e}')

    def delete_file(self, filename):
        if not self.s3:
            return

        try:
            obj = self.s3.Object(bucket_name=skynet_s3_bucket, key=filename)
            obj.delete()
            log.info(f'Deleted file from S3: {filename}')
        except Exception as e:
            log.error(f'Failed to delete file from S3: {e}')


__all__ = ['S3']
