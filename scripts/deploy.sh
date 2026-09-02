#!/usr/bin/env bash
# One-command production deploy for Похвали себя (PH-803).
#
# Usage: sudo ./scripts/deploy.sh [command] [options]
#
# With no .env present this bootstraps a fresh VPS: prompts for the domain
# and bot token, generates secrets, writes .env, builds and starts the
# stack, and configures the Telegram webhook. With an existing .env it
# releases the latest origin/main. See docs/deploy.md.
#
# Secrets are never regenerated or reprinted on an ordinary deploy; secret
# rotation lives only in the `rotate-secrets` subcommand.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="$PROJECT_DIR/.env"
CURRENT_FILE="$PROJECT_DIR/.deploy-current"
PREVIOUS_FILE="$PROJECT_DIR/.deploy-previous"
LOCK_FILE="$PROJECT_DIR/.deploy.lock"

# shellcheck source=./deploy.lib.sh
source "$SCRIPT_DIR/deploy.lib.sh"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/deploy.sh [command] [options]

Commands:
  deploy            Bootstrap (no .env yet) or release origin/main (default)
  status            Container status, current/previous SHA, health, webhook
  logs [args...]    docker compose logs (default: --tail=100 backend caddy migrate)
  rollback          Re-point to the previous release's images (no rebuild)
  rotate-secrets    Rotate webhook secret/path; add --rotate-db-password to
                     also rotate the PostgreSQL password (restarts postgres)
  help              Show this help

Options for 'deploy':
  --allow-red       Deploy even if CI status for origin/main is not green
                     (same as DEPLOY_ALLOW_RED=1)

An existing .env is never regenerated or overwritten by 'deploy'. Secret
rotation only happens via the 'rotate-secrets' subcommand.
EOF
}

# ---------------------------------------------------------------------------
# Subcommands (filled in by later PH-803 checkpoints)
# ---------------------------------------------------------------------------

cmd_deploy() {
  if [[ -f "$ENV_FILE" ]]; then
    die "release flow not implemented yet"
  else
    die "bootstrap flow not implemented yet"
  fi
}

cmd_status() { die "status not implemented yet"; }
cmd_logs() { die "logs not implemented yet"; }
cmd_rollback() { die "rollback not implemented yet"; }
cmd_rotate_secrets() { die "rotate-secrets not implemented yet"; }

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

main() {
  local command="${1:-deploy}"
  if [[ "$command" == "help" || "$command" == "-h" || "$command" == "--help" ]]; then
    usage
    return 0
  fi
  shift || true

  require_root
  require_commands docker git openssl curl flock

  cd -- "$PROJECT_DIR"

  exec 200>"$LOCK_FILE"
  flock -n 200 || die "another deploy.sh run is already in progress (lock: $LOCK_FILE)"

  case "$command" in
    deploy) cmd_deploy "$@" ;;
    status) cmd_status "$@" ;;
    logs) cmd_logs "$@" ;;
    rollback) cmd_rollback "$@" ;;
    rotate-secrets) cmd_rotate_secrets "$@" ;;
    *)
      usage >&2
      die "unknown command: $command"
      ;;
  esac
}

main "$@"
