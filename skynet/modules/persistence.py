import redis as redis_sync
import redis.asyncio as redis
import boto3
import json

from typing import Tuple, Union
from skynet.env import redis_host, redis_namespace, redis_port, redis_secret_id, use_aws_secrets_manager

class SecretsManagerProvider(redis_sync.CredentialProvider):
    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        secret = boto3.client('secretsmanager').get_secret_value(redis_secret_id)
        creds = json.loads(secret['SecretString'])

        return creds['username'], creds['password']

class Persistence:
    def __init__(self):
        try:
            self.db = redis.Redis(
                host=redis_host,
                port=redis_port,
                credential_provider=SecretsManagerProvider() if use_aws_secrets_manager else None,
                decode_responses=True)

            self.db.ping()
            print('Successfully connected to redis')

        except redis.exceptions.ConnectionError as r_con_error:
            print('Redis connection error', r_con_error)

    def __get_namespaced_key(self, key):
        return f'{redis_namespace}:{key}'

    async def get(self, key):
        return await self.db.get(self.__get_namespaced_key(key))

    async def set(self, key, value):
        return await self.db.set(self.__get_namespaced_key(key), value)

    async def delete(self, key):
        return await self.db.delete(self.__get_namespaced_key(key))

db = Persistence()
