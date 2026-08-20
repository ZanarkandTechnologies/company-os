#!/usr/bin/env bash

set -euo pipefail

HOSTNAME_VALUE=""
RUN_USER="kamdar"
PROFILE_NAME="kamdar-ai"

usage() {
  cat <<'EOF'
Usage: verify-vps.sh --hostname HOST [--run-user USER] [--profile-name NAME]

Runs redacted service, secret-name, local-health, public-health, and Notion API
checks. It never prints secret values or the captured verification token.
EOF
}

while (($#)); do
  case "$1" in
    --hostname) HOSTNAME_VALUE="${2:-}"; shift 2 ;;
    --run-user) RUN_USER="${2:-}"; shift 2 ;;
    --profile-name) PROFILE_NAME="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -z "$HOSTNAME_VALUE" ]]; then
  usage >&2
  exit 2
fi
if ((EUID != 0)); then
  printf 'Run this verification as root (for example with sudo).\n' >&2
  exit 1
fi

RUN_HOME=$(getent passwd "$RUN_USER" | cut -d: -f6)
PROFILE_HOME="$RUN_HOME/.hermes/profiles/$PROFILE_NAME"
DOPPLER_BIN=$(command -v doppler)
HERMES_BIN=""
for candidate in "$RUN_HOME/.local/bin/hermes" "$RUN_HOME/.hermes/bin/hermes" /usr/local/bin/hermes /usr/bin/hermes; do
  if [[ -x "$candidate" ]]; then HERMES_BIN="$candidate"; break; fi
done
if [[ -z "$RUN_HOME" || -z "$HERMES_BIN" || -z "$DOPPLER_BIN" ]]; then
  printf 'Runtime user, Hermes, or Doppler is unavailable.\n' >&2
  exit 1
fi

run_as_user() {
  runuser -u "$RUN_USER" -- env \
    HOME="$RUN_HOME" \
    PATH="$RUN_HOME/.local/bin:$RUN_HOME/.hermes/bin:/usr/local/bin:/usr/bin:/bin" \
    "$@"
}

systemctl is-active --quiet kamdar-hermes.service
printf 'service_active=true\n'

SECRET_NAMES=$(run_as_user "$DOPPLER_BIN" secrets --only-names --json --scope "$PROFILE_HOME")
for secret_name in OPENROUTER_API_KEY NOTION_TOKEN NOTION_WEBHOOK_PUBLIC_URL NOTION_ROOT_PAGE_ID NOTION_ALLOWED_DATA_SOURCES NOTION_COMMENT_TRIGGER; do
  jq -e --arg name "$secret_name" 'has($name)' <<<"$SECRET_NAMES" >/dev/null
done
printf 'required_secret_names_present=true\n'

curl -fsS --max-time 5 http://127.0.0.1:8645/notion/health \
  | jq '{local_health: .ok, verification_token_captured}'
PUBLIC_WEBHOOK_STATUS=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
  "https://$HOSTNAME_VALUE/notion/webhook")
if [[ "$PUBLIC_WEBHOOK_STATUS" != "405" ]]; then
  printf 'public_webhook_status=%s (expected 405 for GET)\n' "$PUBLIC_WEBHOOK_STATUS" >&2
  exit 1
fi
printf 'public_webhook_status=405\n'

NOTION_STATUS=$(run_as_user "$DOPPLER_BIN" run --scope "$PROFILE_HOME" -- \
  sh -c 'curl -sS -o /dev/null -w "%{http_code}" https://api.notion.com/v1/users/me -H "Authorization: Bearer $NOTION_TOKEN" -H "Notion-Version: ${NOTION_API_VERSION:-2026-03-11}"')
if [[ "$NOTION_STATUS" != "200" ]]; then
  printf 'notion_api_status=%s\n' "$NOTION_STATUS" >&2
  exit 1
fi
printf 'notion_api_status=200\n'

run_as_user "$DOPPLER_BIN" run --scope "$PROFILE_HOME" -- \
  "$HERMES_BIN" -p "$PROFILE_NAME" notion-webhook status
printf 'verification_status=pass\n'
