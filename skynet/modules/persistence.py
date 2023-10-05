import redis.asyncio as redis
import boto3
from botocore.config import Config
from skynet.env import (
    redis_host,
    redis_port,
    redis_aws_secret_id,
    redis_use_secrets_manager,
    redis_use_tls,
    redis_db_no,
    redis_usr,
    redis_pwd,
    redis_aws_region,
)


def initialize_redis():
    connection_options = {
        'host': redis_host,
        'port': redis_port,
        'socket_connect_timeout': 4000,
        'decode_responses': True,
        'ssl': redis_use_tls,
        'db': redis_db_no,
        'ssl_cert_reqs': None,
    }

    if redis_use_secrets_manager:
        aws_conf = Config(region=redis_aws_region)
        aws_client = boto3.client('secretsmanager', config=aws_conf)
        redis_aws_pass = aws_client.get_secret_value(SecretId=redis_aws_secret_id)['SecretString']
        connection_options['password'] = redis_aws_pass
    else:
        connection_options['username'] = redis_usr
        connection_options['password'] = redis_pwd

    return redis.Redis(**connection_options)


db = initialize_redis()
