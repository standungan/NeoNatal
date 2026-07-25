#!/usr/bin/env bash
# One-time TLS bootstrap.
#
# Chicken-and-egg: nginx refuses to start when its config references cert files
# that do not exist, but certbot's webroot challenge needs nginx already serving
# /.well-known/. So: stage throwaway self-signed certs, boot nginx, swap in the
# real ones, reload.
#
# Run once from the repo root, after both DNS A records point at this VPS:
#   ./deploy/init-letsencrypt.sh
#
# Renewal afterwards is automatic — the certbot service loops on `certbot renew`
# and nginx reloads every 6h to pick up rotated certs.

set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "✗ .env missing — copy .env.example and fill it in first" >&2; exit 1; }
set -a; . ./.env; set +a
: "${APP_DOMAIN:?set APP_DOMAIN in .env}"
: "${API_DOMAIN:?set API_DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?set LETSENCRYPT_EMAIL in .env}"
STAGING="${STAGING:-}"

domains=("$APP_DOMAIN" "$API_DOMAIN")

echo "▸ staging self-signed certs so nginx can boot"
for d in "${domains[@]}"; do
  docker compose run --rm --entrypoint sh certbot -c "
    mkdir -p /etc/letsencrypt/live/$d &&
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout /etc/letsencrypt/live/$d/privkey.pem \
      -out    /etc/letsencrypt/live/$d/fullchain.pem \
      -subj '/CN=localhost' 2>/dev/null"
done

echo "▸ starting the stack (nginx pulls in web, backend, db)"
docker compose up -d nginx

# Give nginx a moment to bind :80 before certbot asks Let's Encrypt to hit it.
sleep 5

echo "▸ requesting real certificates"
[ -n "$STAGING" ] && echo "  (staging CA — certs will NOT be browser-trusted)"
for d in "${domains[@]}"; do
  # Drop the placeholder, or certbot treats it as an existing cert to renew.
  docker compose run --rm --entrypoint sh certbot -c "
    rm -rf /etc/letsencrypt/live/$d /etc/letsencrypt/archive/$d /etc/letsencrypt/renewal/$d.conf"

  docker compose run --rm certbot certonly \
    --webroot -w /var/www/certbot \
    --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email \
    ${STAGING:+--staging} \
    -d "$d"
done

echo "▸ reloading nginx with the real certs"
docker compose exec nginx nginx -s reload

echo "✅ TLS ready — https://$APP_DOMAIN"
