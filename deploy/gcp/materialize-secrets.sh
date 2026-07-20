#!/bin/sh
set -eu

PROJECT_ID="${GCP_PROJECT_ID:-myma-496119}"
RUNTIME_DIR="${RUNTIME_SECRET_DIR:-/run/myma/asignar-folder}"
APP_UID="${APP_UID:-10001}"
APP_GID="${APP_GID:-10001}"

install -d -o root -g root -m 0700 "$RUNTIME_DIR"

fetch_secret() {
  secret_name="$1"
  target_name="$2"
  mode="$3"
  tmp_file="$(mktemp "$RUNTIME_DIR/.${target_name}.XXXXXX")"
  trap 'rm -f "$tmp_file"' EXIT INT TERM

  gcloud secrets versions access latest \
    --project="$PROJECT_ID" \
    --secret="$secret_name" > "$tmp_file"

  chown "$APP_UID:$APP_GID" "$tmp_file"
  chmod "$mode" "$tmp_file"
  mv -f "$tmp_file" "$RUNTIME_DIR/$target_name"
  trap - EXIT INT TERM
}

fetch_secret \
  acreditacion-asignar-folder-supabase-key \
  supabase-key \
  0400
fetch_secret \
  acreditacion-asignar-folder-google-client-secret \
  google-client-secret.json \
  0400
fetch_secret \
  acreditacion-asignar-folder-google-token \
  google-token.json \
  0600
fetch_secret \
  acreditacion-asignar-folder-api-token \
  asignar-folder-api-token \
  0400

printf '%s\n' "Secretos materializados en $RUNTIME_DIR"
