import os

llama_path = os.environ.get('LLAMA_PATH')

# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'
asap_pub_keys_url = os.getenv('ASAP_PUB_KEYS_REPO_URL', None)

if not bypass_auth and not asap_pub_keys_url:
    raise RuntimeError('The ASAP public keys repo url must be set')
