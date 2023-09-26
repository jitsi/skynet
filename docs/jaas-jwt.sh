#!/usr/bin/env bash

set -e

#
# The following code generates a JaaS JWT for use with Skynet.
#

if [[ $# -ne 2 ]]; then
    echo "Usage: jaas-jwt.sh private_key.pk jaas-api-key"
    exit 1
fi

PRIVATE_KEY=$1
API_KEY=$2
APP_ID=$(echo $API_KEY | cut -d/ -f1)

timeNow=`date +%s` # Sets to current local time
expTimeDelay=7200 # No real need to modify this

header='{
    "typ": "JWT",
    "alg": "RS256",
    "kid": "'$API_KEY'"
}'

payload='{
    "aud": "jitsi",
    "iss": "skynet",
    "sub": "'$APP_ID'",
    "exp": '$(($timeNow+$expTimeDelay))'
}'

#################
# $1 String to base64 encode
#################
encodeBase64() {
    echo -n $1 | base64 | sed s/\+/-/ | sed -E s/=+$//
}

#################
# $1 path of the rsa private key
# $2 jwt payload including header
#################
signWithKey() {
    echo -n "$2" | openssl dgst -sha256 -binary -sign "$1"  | openssl enc -base64 | tr -d '\n=[:space:]' | tr -- '+/' '-_'
}

################
generateJaaSJwt() {
    encodedHeader=$(echo `encodeBase64 "$header"`)
    encodedPayload=$(echo `encodeBase64 "$payload"`)
    encodedData=$encodedHeader"."$encodedPayload
    signature=$(echo `signWithKey "$PRIVATE_KEY" $encodedData`)
    echo $encodedData"."$signature
}

generateJaaSJwt

