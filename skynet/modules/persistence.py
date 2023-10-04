import redis.asyncio as redis
import boto3
from skynet.env import (redis_host,
                        redis_namespace,
                        redis_port,
                        redis_aws_secret_id,
                        redis_use_secrets_manager,
                        redis_use_tls,
                        redis_db_no,
                        redis_exp_seconds,
                        redis_usr,
                        redis_pwd)


expire = redis_exp_seconds if redis_exp_seconds > 0 else None


def connect():
    connection_options = {
        'host': redis_host,
        'port': redis_port,
        'socket_connect_timeout': 4000,
        'decode_responses': True,
        'ssl': redis_use_tls,
        'db': redis_db_no,
        'ssl_cert_reqs': None
    }

    if redis_use_secrets_manager:
        try:
            aws_client = boto3.client('secretsmanager')
            redis_aws_pass = aws_client.get_secret_value(SecretId=redis_aws_secret_id)['SecretString']
            connection_options['password'] = redis_aws_pass
        except Exception as e:
            raise e
    else:
        connection_options['username'] = redis_usr
        connection_options['password'] = redis_pwd

    return redis.Redis(**connection_options)


def get_namespaced_key(key):
    return f'{redis_namespace}:{key}'


class Persistence:
    def __init__(self):
        self.db = connect()

    async def get(self, key):
        return await self.db.get(get_namespaced_key(key))

    async def set(self, key, value):
        return await self.db.set(get_namespaced_key(key), value, ex=expire)

    async def delete(self, key):
        return await self.db.delete(get_namespaced_key(key))


db = Persistence()
