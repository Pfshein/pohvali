#!/usr/bin/env bash
# Shared helpers for scripts/deploy.sh (PH-803).
#
# Sourced, never executed directly — kept free of top-level side effects so
# it can also be sourced by shellcheck/tests. Every function here must obey
# the same rule as the rest of the deploy tooling: never print a secret
# (bot token, DB password, webhook secret/path) to stdout or stderr.

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log() {
  printf '[deploy] %s\n' "$*"
}

die() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "this must run as root — try: sudo ./scripts/deploy.sh"
  fi
}

require_commands() {
  local missing=() cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if (( ${#missing[@]} > 0 )); then
    die "missing required commands: ${missing[*]}"
  fi
}

# ---------------------------------------------------------------------------
# .env handling — read without ever printing it, write atomically at 600
# ---------------------------------------------------------------------------

# Print a single key's value from an env file (default: $ENV_FILE) without
# printing anything else from the file. Returns 1 if the key is absent.
read_env_value() {
  local key="$1" file="${2:-$ENV_FILE}" line
  [[ -f "$file" ]] || return 1
  line="$(grep -E "^${key}=" -- "$file" | tail -n1)" || return 1
  [[ -n "$line" ]] || return 1
  printf '%s\n' "${line#*=}"
}

# Load every KEY=value from $ENV_FILE into the current shell's environment.
# The file is written only by this script (see write_env_atomic) so it is
# safe to source; still restricted to simple KEY=value lines, no command
# substitution is possible from a sourced assignment list.
load_env() {
  [[ -f "$ENV_FILE" ]] || die ".env not found at $ENV_FILE — run 'sudo ./scripts/deploy.sh' to bootstrap first"
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
}

current_domain() {
  printf '%s\n' "${APP_DOMAIN%/}"
}

# ---------------------------------------------------------------------------
# Docker Compose / release-state helpers
# ---------------------------------------------------------------------------

compose_config_check() {
  if ! docker compose config --quiet; then
    die "docker compose config is invalid — check .env"
  fi
}

# Build (optional) and start the stack tagged at $1. $2, if "--build",
# rebuilds images first; rollback calls this with an empty $2 so it never
# rebuilds a previous release's images.
deploy_up() {
  local sha="$1" build_flag="${2:-}"
  if [[ "$build_flag" == "--build" ]]; then
    log "Building and starting release ${sha:0:12}..."
    POHVALA_IMAGE_TAG="$sha" docker compose up -d --build --remove-orphans
  else
    log "Starting release ${sha:0:12} (no rebuild)..."
    POHVALA_IMAGE_TAG="$sha" docker compose up -d --remove-orphans
  fi
}

# Wait for the one-shot `migrate` service to exit 0, then for `backend`'s
# healthcheck to report healthy. Dies with a clear message on failure.
wait_for_health() {
  local timeout="${1:-240}" waited=0 cid status code

  while (( waited < timeout )); do
    cid="$(docker compose ps -a -q migrate 2>/dev/null || true)"
    [[ -n "$cid" ]] && break
    sleep 2
    (( waited += 2 ))
  done
  if [[ -n "$cid" ]]; then
    waited=0
    while (( waited < timeout )); do
      status="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || true)"
      if [[ "$status" == "exited" ]]; then
        code="$(docker inspect --format '{{.State.ExitCode}}' "$cid" 2>/dev/null || echo 1)"
        [[ "$code" == "0" ]] || die "migrate service failed (exit $code) — check: docker compose logs migrate"
        break
      fi
      sleep 2
      (( waited += 2 ))
    done
    (( waited < timeout )) || die "migrate did not finish within ${timeout}s"
  fi

  waited=0
  while (( waited < timeout )); do
    cid="$(docker compose ps -q backend 2>/dev/null || true)"
    if [[ -n "$cid" ]]; then
      status="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
      [[ "$status" == "healthy" ]] && return 0
      [[ "$status" == "unhealthy" ]] && die "backend is unhealthy — check: docker compose logs backend"
    fi
    sleep 3
    (( waited += 3 ))
  done
  die "backend did not become healthy within ${timeout}s"
}

# Wait for the public HTTPS health endpoint to return {"status":"ok"}.
wait_for_https() {
  local domain="$1" timeout="${2:-180}" waited=0
  while (( waited < timeout )); do
    if curl -fsS --max-time 5 "${domain%/}/api/v1/health" 2>/dev/null | grep -q '"status":"ok"'; then
      return 0
    fi
    sleep 3
    (( waited += 3 ))
  done
  die "HTTPS health check did not succeed within ${timeout}s: ${domain%/}/api/v1/health"
}

# Run a Telegram setup subcommand inside the already-running backend
# container. Never called before wait_for_health.
telegram_cmd() {
  docker compose exec -T backend python -m app.modules.telegram.setup "$@"
}
