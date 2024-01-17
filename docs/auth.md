# Skynet Authorization

Skynet uses a JWT signed with an asymmetric key, just like [**Jitsi as a Service**](https://jaas.8x8.vc) does.

The authorization is performed by downloading the public key advertised in the JWT's `kid` header from a well-known location and checking if the JWT signature and the audiences match.

> Authorization can be disabled all together by setting the `BYPASS_AUTHORIZATION` env var to `true`. 


## Creating a keypair

Generate an `RS256` keypair with the command below and upload the public key to a web server.

```bash
ssh-keygen -m PKCS8 -b 2048 -t rsa
```

Pick a key id (`kid`), e.g. `my-awesome-service`, and rename the public key to its `SHA256` sum.

```bash
echo -n "my-awesome-service" | shasum -a 256
# cf83fb2ffe64d959f93c3ade60a1c45421f016be3dcbbeda9ea7f1b78afdb698 -
```

So you would rename `id_rsa.pub`, or whatever your public key's name is, to `cf83fb2ffe64d959f93c3ade60a1c45421f016be3dcbbeda9ea7f1b78afdb698.pub` and upload
it to a http server of your liking.

> **N.B.** The web service url and root path should be specified as environment variables, check `ASAP_PUB_KEYS_REPO_URL` and `ASAP_PUB_KEYS_FOLDER` in [Environment Variables](./env_vars.md).

## Creating JWTs

The JWT unencrypted header should look like this, note the mandatory `kid` with the name we picked earlier.

```json
{
  "alg": "RS256",
  "kid": "my-awesome-service",
  "typ": "JWT"
}
```

The only mandatory field in the body is the `aud` claim, which must match at least one of the audiences defined in the `ASAP_PUB_KEYS_AUDS` environment variable, check [Environment Variables](./env_vars.md).

Once you have your JWT, sign it with the private key and use it to access any of the services provided by Skynet.

## Authorization Flow

1. Skynet receives the JWT and reads the unencrypted header
2. It extracts the `kid` and performs a `SHA256` sum on the string
3. It then attempts to download the public key from `ASAP_PUB_KEYS_REPO_URL/ASAP_PUB_KEYS_FOLDER/{sha-sum-of-kid}.pem` if it cannot find it in the local cache
4. It checks if the signature and the audience match 

## Helper script

Use this [bash script](jaas-jwt.sh) to quickly generate JWTs. Please note that you will still need to upload the public key somewhere and generate the key pair.

```bash
./docs/jaas-jwt.sh PrivateKey.pk API-Key
# The generated token has a validity of 7200 seconds
```

## Examples

### Issue a JWT in Java

```java
private String getJWT() throws NoSuchAlgorithmException, InvalidKeySpecException
    {
        long nowMillis = System.currentTimeMillis();
        Date now = new Date(nowMillis);
        KeyFactory kf = KeyFactory.getInstance("RSA");
        PKCS8EncodedKeySpec keySpecPKCS8 = new PKCS8EncodedKeySpec(Base64.getDecoder().decode(privateKey));
        PrivateKey finalPrivateKey = kf.generatePrivate(keySpecPKCS8);
        JwtBuilder builder = Jwts.builder()
                .setHeaderParam("kid", "my-awesome-service")
                .setIssuedAt(now)
                .setIssuer("myCoolApp")
                .setAudience("my-audience")
                .signWith(SignatureAlgorithm.RS256, finalPrivateKey);
        long expires = nowMillis + (60 * 60 * 1000);
        Date expiry = new Date(expires);
        builder.setExpiration(expiry);
        return builder.compact();
    }
```

### Issue a JWT in Python

```python
import time
import os
import sys
import jwt

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

dir_path = os.path.dirname(os.path.realpath(__file__))

header = {
    'alg': 'RS256',
    'kid': 'my-awesome-service',
    'typ': 'JWT'
}

claims = {
    'iss': 'myAwesomeApp',
    'exp': time.time() + 300,
    'user': 'me',
    'aud': 'my-audience'
}

def create_jwt(claims: dict, headers: dict, secret_key: str) -> str:
    return jwt.encode(claims, secret_key, headers=headers)

with open(f'{dir_path}/keys/private.key', 'r') as f:
    private_key = f.read()

jwt = create_jwt(claims, header, private_key)

print(jwt)
```
