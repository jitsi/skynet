import os

llama_path = os.environ.get('LLAMA_PATH')

# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'

sso_pubkey = bytes(os.environ.get('SSO_PUBKEY', ''), 'utf-8')
sso_issuer = os.environ.get('SSO_ISSUER')
sso_algorithm = os.environ.get('SSO_ALGORITHM', 'RS256')

if not bypass_auth and (not sso_pubkey or not sso_issuer):
    raise RuntimeError('The SSO_PUBKEY and SSO_ISSUER environment variables must be set')
