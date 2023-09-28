import redis
import boto3
import cachetools.func
import json

from typing import Tuple, Union
from skynet.env import redis_host, redis_port, redis_secret_id, use_aws_secrets_manager

class SecretsManagerProvider(redis.CredentialProvider):
    def __init__(self):
        self.sm_client = boto3.client('secretsmanager')
        self.secret_id = redis_secret_id
        self.version_id = None
        self.version_stage = 'AWSCURRENT'

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        @cachetools.func.ttl_cache(maxsize=128, ttl=24 * 60 * 60) #24h
        def get_sm_user_credentials(secret_id, version_id, version_stage):
            secret = self.sm_client.get_secret_value(secret_id, version_id, version_stage)
            return json.loads(secret['SecretString'])
        creds = get_sm_user_credentials(self.secret_id, self.version_id, self.version_stage)
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

    def get(self, key):
        return self.db.get(key)

    def set(self, key, value):
        return self.db.set(key, value)

    def delete(self, key):
        return self.db.delete(key)

db = Persistence()
