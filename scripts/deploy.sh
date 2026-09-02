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
# Bootstrap prompts (interactive; validation itself is pure, see deploy.lib.sh)
# ---------------------------------------------------------------------------

prompt_domain() {
  local raw domain
  while true; do
    read -r -p "Production domain (e.g. app.example.com): " raw
    if domain="$(normalize_domain "$raw")"; then
      printf '%s\n' "$domain"
      return 0
    fi
    echo "Invalid domain — must be a public https hostname (no localhost, no path)." >&2
  done
}

prompt_token() {
  local token
  while true; do
    read -rs -p "Telegram bot token from @BotFather: " token
    echo >&2
    if validate_token "$token"; then
      printf '%s\n' "$token"
      return 0
    fi
    echo "Invalid token — cannot be empty and must look like a BotFather token." >&2
  done
}

prompt_admin_id() {
  local raw
  read -r -p "First admin Telegram ID (optional, leave blank to skip): " raw
  if ! validate_admin_id "$raw"; then
    echo "Telegram ID must be a positive integer — skipping admin assignment." >&2
    raw=""
  fi
  printf '%s\n' "$raw"
}

# ---------------------------------------------------------------------------
# Bootstrap (Task 4)
# ---------------------------------------------------------------------------

bootstrap() {
  log "No .env found — starting first-time bootstrap."

  local domain token admin_id
  domain="$(prompt_domain)"
  token="$(prompt_token)"
  admin_id="$(prompt_admin_id)"

  local pg_password webhook_secret webhook_path database_url
  pg_password="$(openssl rand -hex 32)"
  webhook_secret="$(openssl rand -hex 32)"
  webhook_path="$(openssl rand -hex 24)"
  database_url="postgresql+asyncpg://pohvala:${pg_password}@postgres:5432/pohvala"

  write_env_atomic "APP_ENV=production
APP_DOMAIN=${domain}
VITE_TELEGRAM_MODE=telegram

BOT_TOKEN=${token}
TELEGRAM_WEBHOOK_SECRET=${webhook_secret}
TELEGRAM_WEBHOOK_PATH=${webhook_path}

POSTGRES_DB=pohvala
POSTGRES_USER=pohvala
POSTGRES_PASSWORD=${pg_password}
DATABASE_URL=${database_url}

CORS_ORIGINS=${domain}"
  log "Wrote .env (mode 600)."

  load_env
  compose_config_check

  local sha
  sha="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
  deploy_up "$sha" --build

  wait_for_health
  wait_for_https "$domain"

  log "Confirming the bot token with Telegram..."
  telegram_cmd get-me
  log "Registering the webhook (first run — dropping any stray pending updates)..."
  telegram_cmd set-webhook --drop-pending
  telegram_cmd set-menu-button
  telegram_cmd get-webhook-info

  if [[ -n "$admin_id" ]]; then
    assign_first_admin "$admin_id"
  fi

  printf '%s\n' "$sha" > "$CURRENT_FILE"
  log "Bootstrap complete. Domain: $domain"
}

# Loop until the admin's account exists (they must open the bot/Mini App
# once first) or the operator interrupts with Ctrl-C.
assign_first_admin() {
  local admin_id="$1"
  log "Waiting for the admin to open the bot or Mini App at least once..."
  while true; do
    if docker compose exec -T backend python -m app.modules.users.set_role "$admin_id" admin; then
      log "Admin role assigned."
      return 0
    fi
    log "Account not found yet — ask them to open the bot or Mini App, then press Enter to retry (Ctrl-C to skip)."
    read -r -p "" _ || true
  done
}

# ---------------------------------------------------------------------------
# Release (Task 5)
# ---------------------------------------------------------------------------

backup_before_migrate() {
  local backup_script="$PROJECT_DIR/ops/backup/backup.sh"
  local recipient_file="${POHVALA_AGE_RECIPIENT_FILE:-/etc/pohvali-backup/recipients.txt}"

  if [[ -x "$backup_script" && -r "$recipient_file" ]]; then
    log "Running the configured encrypted backup before migrating..."
    "$backup_script"
    return 0
  fi

  log "No configured encrypted backup found — falling back to a local pg_dump."
  local backup_dir="$PROJECT_DIR/.deploy-backups" ts dump_path
  install -d -m 0700 "$backup_dir"
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  dump_path="$backup_dir/pre-migrate-${ts}.dump"
  if ! docker compose exec -T postgres sh -eu -c \
      'exec pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
      > "$dump_path"; then
    rm -f -- "$dump_path"
    die "pre-migration backup failed"
  fi
  if [[ ! -s "$dump_path" ]]; then
    rm -f -- "$dump_path"
    die "pre-migration backup is empty"
  fi
  chmod 0600 "$dump_path"
  log "Pre-migration backup saved: $(basename -- "$dump_path")"
}

release() {
  log "Existing .env found — checking for a release."
  load_env

  git -C "$PROJECT_DIR" fetch --quiet origin main

  if [[ -n "$(git -C "$PROJECT_DIR" status --porcelain)" ]]; then
    die "worktree is dirty — commit or stash local changes before deploying"
  fi

  local head_sha origin_sha
  head_sha="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
  origin_sha="$(git -C "$PROJECT_DIR" rev-parse origin/main)"

  if [[ "$head_sha" == "$origin_sha" ]]; then
    log "origin/main has no new commits — nothing to deploy."
    log "Current release: ${head_sha:0:12}"
    return 0
  fi

  if ! check_ci_status "$origin_sha"; then
    die "CI is not green for ${origin_sha:0:12}. Re-run with --allow-red or DEPLOY_ALLOW_RED=1 to override."
  fi

  printf '%s\n' "$head_sha" > "$PREVIOUS_FILE"

  backup_before_migrate

  git -C "$PROJECT_DIR" merge --ff-only origin/main \
    || die "fast-forward merge failed — local main has diverged from origin/main"

  compose_config_check
  deploy_up "$origin_sha" --build

  wait_for_health
  wait_for_https "$(current_domain)"

  log "Refreshing the webhook (keeping pending updates)..."
  telegram_cmd set-webhook --keep-pending
  telegram_cmd get-webhook-info

  printf '%s\n' "$origin_sha" > "$CURRENT_FILE"
  prune_old_images "$head_sha" "$origin_sha"

  log "Release complete: ${head_sha:0:12} -> ${origin_sha:0:12}"
}

# ---------------------------------------------------------------------------
# Subcommands (status/logs/rollback/rotate-secrets filled in by the next
# PH-803 checkpoint)
# ---------------------------------------------------------------------------

cmd_deploy() {
  ALLOW_RED=0
  local arg
  for arg in "$@"; do
    case "$arg" in
      --allow-red) ALLOW_RED=1 ;;
      *) die "unknown deploy option: $arg" ;;
    esac
  done
  [[ "${DEPLOY_ALLOW_RED:-0}" == "1" ]] && ALLOW_RED=1

  if [[ -f "$ENV_FILE" ]]; then
    release
  else
    bootstrap
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
