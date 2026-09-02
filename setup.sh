#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
export COMPANY_OS_PROFILE_HOME="${HOME}/.hermes/profiles/company-os"
export HERMES_HOME="$COMPANY_OS_PROFILE_HOME"
HERMES_PYTHON="${HOME}/.hermes/hermes-agent/venv/bin/python"

run_setup() { "$HERMES_PYTHON" "$(pwd)/setup.py" "$@"; }

selected_gateway_running() {
  hermes gateway status 2>&1 | grep -Fq "Gateway is running (PID:"
}

start_runtime() {
  selected_gateway_running && return 0
  mkdir -p "$COMPANY_OS_PROFILE_HOME/logs"
  nohup hermes gateway run >"$COMPANY_OS_PROFILE_HOME/logs/setup-gateway.log" 2>&1 &
  sleep 3
  selected_gateway_running && return 0
  echo "The selected Hermes profile gateway did not become ready: $COMPANY_OS_PROFILE_HOME" >&2
  echo "A gateway running for another profile is not accepted." >&2
  return 1
}

rollback_webhook() {
  run_setup webhook-rollback || true
  docker compose --profile webhook stop ngrok >/dev/null 2>&1 || true
}

start_webhook_if_enabled() {
  run_setup webhook-enabled >/dev/null 2>&1 || return 0
  docker compose --profile webhook up -d --force-recreate ngrok || { rollback_webhook; return 1; }
  run_setup webhook-ingress-ready --wait 30 || { rollback_webhook; return 1; }
  docker compose --profile webhook ps --status running --services ngrok | grep -qx ngrok \
    || { rollback_webhook; return 1; }
  run_setup webhook-commit || { rollback_webhook; return 1; }
}

command -v hermes >/dev/null 2>&1 || { echo "Host Hermes is required."; exit 2; }
test -x "$HERMES_PYTHON" || { echo "Hermes bundled Python was not found."; exit 2; }
docker info >/dev/null 2>&1 || { echo "Docker Desktop is not ready."; exit 2; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose is unavailable."; exit 2; }

echo "Opening setup in the host Hermes profile..."
run_setup launch
action=$?
case "$action" in
  0) exit 0 ;;
  10)
    start_runtime \
      && start_webhook_if_enabled \
      && run_setup verify --live \
      && run_setup doctor preflight \
      && run_setup doctor eval --open \
      && run_setup doctor activate
    result=$?
    ;;
  12) start_runtime && start_webhook_if_enabled && run_setup verify --live; result=$? ;;
  11) start_runtime && run_setup verify; result=$? ;;
  13)
    start_runtime || exit 2
    nohup "$HERMES_PYTHON" "$COMPANY_OS_PROFILE_HOME/apps/installer/dashboard.py" \
      >"$COMPANY_OS_PROFILE_HOME/logs/setup-dashboard.log" 2>&1 &
    open "http://localhost:9119"
    exit 0
    ;;
  14) run_setup certify; result=$? ;;
  15) run_setup doctor preflight; result=$? ;;
  16) run_setup doctor eval --open; result=$? ;;
  17) run_setup doctor open; result=$? ;;
  130) exit 0 ;;
  *) exit 2 ;;
esac
exit "$result"
