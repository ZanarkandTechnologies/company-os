#!/usr/bin/env bash

set -euo pipefail

PROFILE_NAME="kamdar-ai"
RUN_USER="kamdar"
HOSTNAME_VALUE=""
READ_DOPPLER_TOKEN=false
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: bootstrap-vps.sh --hostname HOST [options]

Options:
  --hostname HOST          Dedicated public hostname for the Notion webhook
  --run-user USER          Unprivileged runtime user (default: kamdar)
  --profile-name NAME      Hermes profile name (default: kamdar-ai)
  --doppler-token-stdin    Read one Doppler service token line from stdin
  --dry-run                Validate the package and inputs without changing the VPS
  -h, --help               Show this help

Run as root on Debian 11+ or Ubuntu 22.04+.
EOF
}

while (($#)); do
  case "$1" in
    --hostname)
      HOSTNAME_VALUE="${2:-}"
      shift 2
      ;;
    --run-user)
      RUN_USER="${2:-}"
      shift 2
      ;;
    --profile-name)
      PROFILE_NAME="${2:-}"
      shift 2
      ;;
    --doppler-token-stdin)
      READ_DOPPLER_TOKEN=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$HOSTNAME_VALUE" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]] || [[ "$HOSTNAME_VALUE" != *.* ]]; then
  printf 'A valid dedicated hostname is required.\n' >&2
  exit 2
fi
if [[ ! "$RUN_USER" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  printf 'Invalid run user.\n' >&2
  exit 2
fi
if [[ ! "$PROFILE_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
  printf 'Invalid profile name.\n' >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

for required in distribution.yaml config.yaml SOUL.md plugins/platforms/notion/plugin.yaml; do
  if [[ ! -f "$SOURCE_ROOT/$required" ]]; then
    printf 'Distribution is incomplete: missing %s\n' "$required" >&2
    exit 1
  fi
done

if "$DRY_RUN"; then
  printf 'dry_run=pass\n'
  printf 'profile=%s\n' "$PROFILE_NAME"
  printf 'hostname=%s\n' "$HOSTNAME_VALUE"
  printf 'source=%s\n' "$SOURCE_ROOT"
  exit 0
fi

if ((EUID != 0)); then
  printf 'Run this bootstrap as root (for example with sudo).\n' >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  printf 'Cannot identify this Linux distribution.\n' >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
  debian|ubuntu) ;;
  *)
    printf 'Supported VPS operating systems: Debian and Ubuntu. Found: %s\n' "${ID:-unknown}" >&2
    exit 1
    ;;
esac

DOPPLER_SERVICE_TOKEN=""
if "$READ_DOPPLER_TOKEN"; then
  IFS= read -r DOPPLER_SERVICE_TOKEN
elif [[ -n "${DOPPLER_TOKEN:-}" ]]; then
  DOPPLER_SERVICE_TOKEN="$DOPPLER_TOKEN"
fi
if [[ -z "$DOPPLER_SERVICE_TOKEN" ]]; then
  printf 'Supply a read-only Doppler service token with --doppler-token-stdin.\n' >&2
  exit 1
fi

apt-get update
apt-get install -y apt-transport-https ca-certificates curl debian-archive-keyring debian-keyring git gnupg jq rsync

if ! command -v doppler >/dev/null 2>&1; then
  curl -sLf --retry 3 --tlsv1.2 --proto '=https' \
    'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' \
    | gpg --batch --yes --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg
  printf '%s\n' \
    'deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main' \
    > /etc/apt/sources.list.d/doppler-cli.list
  apt-get update
  apt-get install -y doppler
fi

if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  chmod o+r /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-get install -y caddy
fi

if ! id "$RUN_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$RUN_USER"
fi
RUN_HOME=$(getent passwd "$RUN_USER" | cut -d: -f6)
if [[ -z "$RUN_HOME" || "$RUN_HOME" == "/" ]]; then
  printf 'Unsafe home directory resolved for %s.\n' "$RUN_USER" >&2
  exit 1
fi

run_as_user() {
  runuser -u "$RUN_USER" -- env \
    HOME="$RUN_HOME" \
    PATH="$RUN_HOME/.local/bin:$RUN_HOME/.hermes/bin:/usr/local/bin:/usr/bin:/bin" \
    "$@"
}

HERMES_BIN=""
for candidate in "$RUN_HOME/.local/bin/hermes" "$RUN_HOME/.hermes/bin/hermes" /usr/local/bin/hermes /usr/bin/hermes; do
  if [[ -x "$candidate" ]]; then
    HERMES_BIN="$candidate"
    break
  fi
done
if [[ -z "$HERMES_BIN" ]]; then
  run_as_user bash -c "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
  for candidate in "$RUN_HOME/.local/bin/hermes" "$RUN_HOME/.hermes/bin/hermes"; do
    if [[ -x "$candidate" ]]; then
      HERMES_BIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$HERMES_BIN" ]]; then
  printf 'Hermes installation completed without a discoverable executable.\n' >&2
  exit 1
fi

DIST_ROOT=/opt/kamdar-ai-distribution
install -d -m 0755 -o "$RUN_USER" -g "$RUN_USER" "$DIST_ROOT"
rsync -a --delete --exclude .git/ "$SOURCE_ROOT/" "$DIST_ROOT/"
chown -R "$RUN_USER:$RUN_USER" "$DIST_ROOT"

PROFILE_HOME="$RUN_HOME/.hermes/profiles/$PROFILE_NAME"
if [[ -f "$PROFILE_HOME/distribution.yaml" ]]; then
  run_as_user "$HERMES_BIN" profile update "$PROFILE_NAME" --yes
elif [[ -e "$PROFILE_HOME" ]]; then
  printf 'Refusing to overwrite non-distribution profile: %s\n' "$PROFILE_HOME" >&2
  exit 1
else
  run_as_user "$HERMES_BIN" profile install "$DIST_ROOT" --name "$PROFILE_NAME" --alias --yes
fi

DOPPLER_BIN=$(command -v doppler)
printf '%s\n' "$DOPPLER_SERVICE_TOKEN" \
  | run_as_user "$DOPPLER_BIN" configure set token --scope "$PROFILE_HOME" >/dev/null
unset DOPPLER_SERVICE_TOKEN DOPPLER_TOKEN

SECRET_NAMES=$(run_as_user "$DOPPLER_BIN" secrets --only-names --json --scope "$PROFILE_HOME")
for secret_name in OPENROUTER_API_KEY NOTION_TOKEN NOTION_WEBHOOK_PUBLIC_URL NOTION_ROOT_PAGE_ID NOTION_ALLOWED_DATA_SOURCES NOTION_COMMENT_TRIGGER; do
  if ! jq -e --arg name "$secret_name" 'has($name)' <<<"$SECRET_NAMES" >/dev/null; then
    printf 'Doppler config is missing required key: %s\n' "$secret_name" >&2
    exit 1
  fi
done

UNIT_PATH=/etc/systemd/system/kamdar-hermes.service
UNIT_TMP=$(mktemp /tmp/kamdar-hermes.service.XXXXXX)
trap 'rm -f "$UNIT_TMP"' EXIT
sed \
  -e "s|__RUN_USER__|$RUN_USER|g" \
  -e "s|__RUN_HOME__|$RUN_HOME|g" \
  -e "s|__PROFILE_HOME__|$PROFILE_HOME|g" \
  -e "s|__DOPPLER_BIN__|$DOPPLER_BIN|g" \
  -e "s|__HERMES_BIN__|$HERMES_BIN|g" \
  -e "s|__PROFILE_NAME__|$PROFILE_NAME|g" \
  "$DIST_ROOT/deploy/kamdar-hermes.service.template" > "$UNIT_TMP"
install -m 0644 "$UNIT_TMP" "$UNIT_PATH"
systemd-analyze verify "$UNIT_PATH"

CADDY_MAIN=/etc/caddy/Caddyfile
CADDY_DIR=/etc/caddy/Caddyfile.d
CADDY_SITE="$CADDY_DIR/kamdar-notion.caddy"
CADDY_BACKUP=$(mktemp /etc/caddy/Caddyfile.kamdar-backup.XXXXXX)
SITE_BACKUP=""
install -d -m 0755 "$CADDY_DIR"
cp -p "$CADDY_MAIN" "$CADDY_BACKUP"
if [[ -f "$CADDY_SITE" ]]; then
  SITE_BACKUP=$(mktemp /tmp/kamdar-notion.caddy.XXXXXX)
  cp -p "$CADDY_SITE" "$SITE_BACKUP"
fi
sed "s|__HOSTNAME__|$HOSTNAME_VALUE|g" \
  "$DIST_ROOT/deploy/kamdar-notion.caddy.template" > "$CADDY_SITE"
if ! grep -Fqx 'import Caddyfile.d/*.caddy' "$CADDY_MAIN"; then
  printf '\nimport Caddyfile.d/*.caddy\n' >> "$CADDY_MAIN"
fi
if ! caddy validate --config "$CADDY_MAIN" --adapter caddyfile; then
  cp -p "$CADDY_BACKUP" "$CADDY_MAIN"
  if [[ -n "$SITE_BACKUP" ]]; then
    cp -p "$SITE_BACKUP" "$CADDY_SITE"
  else
    rm -f "$CADDY_SITE"
  fi
  printf 'Caddy validation failed; previous configuration restored.\n' >&2
  exit 1
fi
[[ -z "$SITE_BACKUP" ]] || rm -f "$SITE_BACKUP"

systemctl daemon-reload
systemctl enable --now kamdar-hermes.service
systemctl reload caddy

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 3 http://127.0.0.1:8645/notion/health >/dev/null; then
    break
  fi
  sleep 2
done
curl -fsS --max-time 5 http://127.0.0.1:8645/notion/health \
  | jq '{ok, verification_token_captured}'

PUBLIC_READY=false
for _ in 1 2 3 4 5 6; do
  if curl -fsS --max-time 8 "https://$HOSTNAME_VALUE/notion/health" >/dev/null; then
    PUBLIC_READY=true
    break
  fi
  sleep 5
done

printf 'runtime_status=configured\n'
printf 'service=kamdar-hermes.service\n'
printf 'webhook=https://%s/notion/webhook\n' "$HOSTNAME_VALUE"
printf 'caddy_backup=%s\n' "$CADDY_BACKUP"
if "$PUBLIC_READY"; then
  printf 'public_https_status=configured\n'
  printf 'notion_subscription_status=human_required\n'
  printf 'next=Create and verify the Notion webhook subscription.\n'
else
  printf 'public_https_status=human_required\n'
  printf 'next=Point the hostname at this VPS, then rerun verify-vps.sh.\n'
  exit 3
fi
