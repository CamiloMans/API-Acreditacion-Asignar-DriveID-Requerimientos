#!/bin/sh
set -eu

CERTBOT="${CERTBOT_BIN:-/opt/certbot-ip/bin/certbot}"
IP_ADDRESS="${IP_ADDRESS:-34.24.174.159}"
EMAIL="${LETSENCRYPT_EMAIL:-lab@myma.cl}"
WEBROOT="${ACME_WEBROOT:-/var/www/letsencrypt}"

"$CERTBOT" certonly \
  --staging \
  --non-interactive \
  --agree-tos \
  --no-eff-email \
  --email "$EMAIL" \
  --preferred-profile shortlived \
  --webroot \
  --webroot-path "$WEBROOT" \
  --ip-address "$IP_ADDRESS" \
  --cert-name "$IP_ADDRESS-staging"

"$CERTBOT" certonly \
  --non-interactive \
  --agree-tos \
  --no-eff-email \
  --email "$EMAIL" \
  --preferred-profile shortlived \
  --webroot \
  --webroot-path "$WEBROOT" \
  --ip-address "$IP_ADDRESS" \
  --cert-name "$IP_ADDRESS"
