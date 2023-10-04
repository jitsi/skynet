import redis as redis_sync
import redis.asyncio as redis
import boto3
import json

from typing import Tuple, Union
from skynet.env import redis_host, redis_namespace, redis_port, redis_secret_id, use_aws_secrets_manager
from skynet.logs import get_logger

log = get_logger('skynet.redis')

class SecretsManagerProvider(redis_sync.CredentialProvider):
    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        secret = boto3.client('secretsmanager').get_secret_value(redis_secret_id)
        creds = json.loads(secret['SecretString'])

        return creds['username'], creds['password']

class Redis:
    def __init__(self):
        self.db = redis.Redis(
            host=redis_host,
            port=redis_port,
            credential_provider=SecretsManagerProvider() if use_aws_secrets_manager else None,
            decode_responses=True)

    def __get_namespaced_key(self, key):
        return f'{redis_namespace}:{key}'

    def initialize(self):
        return self.db.ping()

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

    async def lpop(self, key):
        return await self.db.lpop(self.__get_namespaced_key(key))

    async def lrange(self, key, start, end):
        return await self.db.lrange(self.__get_namespaced_key(key), start, end)

    async def lrem(self, key, count, value):
        return await self.db.lrem(self.__get_namespaced_key(key), count, value)

db = Redis()
