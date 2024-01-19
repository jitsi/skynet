import redis.asyncio as redis

from skynet.env import (
    redis_aws_region,
    redis_aws_secret_id,
    redis_db_no,
    redis_host,
    redis_namespace,
    redis_port,
    redis_pwd,
    redis_use_secrets_manager,
    redis_use_tls,
    redis_usr,
)
from skynet.logs import get_logger

log = get_logger(__name__)


class Redis:
    def __init__(self):
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
            import boto3
            from botocore.config import Config

            aws_conf = Config(region_name=redis_aws_region)
            aws_client = boto3.client('secretsmanager', config=aws_conf)
            redis_aws_pass = aws_client.get_secret_value(SecretId=redis_aws_secret_id)['SecretString']
            connection_options['password'] = redis_aws_pass
        else:
            connection_options['username'] = redis_usr
            connection_options['password'] = redis_pwd

        self.db = redis.Redis(**connection_options)
        self.initialized = False

    @staticmethod
    def __get_namespaced_key(key):
        return f'{redis_namespace}:{key}'

    async def initialize(self):
        if self.initialized:
            return

        try:
            await self.db.ping()
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f'Failed to initialize Redis: {e}')

    async def client_list(self):
        return await self.db.client_list()

    async def mget(self, keys):
        return await self.db.mget([self.__get_namespaced_key(key) for key in keys])

    async def get(self, key):
        return await self.db.get(self.__get_namespaced_key(key))

    async def set(self, key, *args, **kwargs):
        return await self.db.set(self.__get_namespaced_key(key), *args, **kwargs)

    async def lpush(self, key, *values):
        return await self.db.lpush(self.__get_namespaced_key(key), *values)

    async def rpush(self, key, *values):
        return await self.db.rpush(self.__get_namespaced_key(key), *values)

    async def llen(self, key):
        return await self.db.llen(self.__get_namespaced_key(key))

    async def lpop(self, key):
        return await self.db.lpop(self.__get_namespaced_key(key))

    async def lrange(self, key, start, end):
        return await self.db.lrange(self.__get_namespaced_key(key), start, end)

    async def lrem(self, key, count, value):
        return await self.db.lrem(self.__get_namespaced_key(key), count, value)


db = Redis()
