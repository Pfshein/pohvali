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

# Write $content (already fully rendered) to $ENV_FILE atomically at
# mode 600: temp file in the same directory, then rename. Never overwrites
# an existing .env — callers must check beforehand.
write_env_atomic() {
  local content="$1" tmp
  [[ ! -e "$ENV_FILE" ]] || die "refusing to overwrite existing $ENV_FILE"
  umask 077
  tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
  printf '%s\n' "$content" > "$tmp"
  chmod 600 "$tmp"
  mv -f -- "$tmp" "$ENV_FILE"
}

# ---------------------------------------------------------------------------
# Input validation (pure — no prompting, so these are directly testable)
# ---------------------------------------------------------------------------

# Normalize a user-entered domain to "https://host", rejecting anything that
# is not a plausible public HTTPS hostname. A bare host ("app.example.com")
# is accepted and gets "https://" prepended; an explicit non-https scheme
# ("http://…") is rejected rather than silently rewritten.
normalize_domain() {
  local raw="$1" domain host
  raw="${raw%"${raw##*[![:space:]]}"}"   # trim trailing whitespace
  raw="${raw#"${raw%%[![:space:]]*}"}"   # trim leading whitespace
  [[ -n "$raw" ]] || return 1

  if [[ "$raw" =~ ^[A-Za-z][A-Za-z0-9+.-]*:// ]]; then
    [[ "$raw" == https://* ]] || return 1
    domain="$raw"
  else
    domain="https://${raw}"
  fi
  domain="${domain%/}"

  host="${domain#https://}"
  [[ -n "$host" && "$host" != *"/"* ]] || return 1
  [[ "$host" != *"localhost"* ]] || return 1
  [[ "$host" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$ ]] || return 1

  printf '%s\n' "$domain"
}

# A BotFather token is non-empty, whitespace-free, and shaped "digits:rest".
validate_token() {
  local token="$1"
  [[ -n "$token" && "$token" != *[[:space:]]* && "$token" == *:* ]]
}

# Empty is valid (skip first-admin assignment); otherwise a positive integer.
validate_admin_id() {
  local raw="$1"
  [[ -z "$raw" ]] && return 0
  [[ "$raw" =~ ^[0-9]+$ ]] || return 1
  (( 10#$raw > 0 ))
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

# Query GitHub's combined status API for a commit; returns via $?:
#   0  green (or API unreachable — degrade to a warning, never block)
#   1  red/pending and not overridden — caller must die
check_ci_status() {
  local sha="$1" repo="${DEPLOY_GITHUB_REPO:-Pfshein/pohvali}" response state
  if ! response="$(curl -fsS --max-time 10 -H 'Accept: application/vnd.github+json' \
      "https://api.github.com/repos/${repo}/commits/${sha}/status" 2>/dev/null)"; then
    log "WARNING: GitHub API unreachable — skipping the CI gate for ${sha:0:12}."
    return 0
  fi
  state="$(printf '%s' "$response" | grep -o '"state":"[a-z]*"' | head -n1 | cut -d'"' -f4)"
  case "$state" in
    success | "")
      [[ -n "$state" ]] || log "WARNING: no CI status found for ${sha:0:12} — continuing."
      return 0
      ;;
    *)
      if [[ "${ALLOW_RED:-0}" == "1" ]]; then
        log "CI status is '${state}' for ${sha:0:12} — continuing (--allow-red)."
        return 0
      fi
      log "CI status is '${state}' for ${sha:0:12}."
      return 1
      ;;
  esac
}

# Best-effort: drop local pohvala-{backend,frontend} images except the ones
# tagged with the given SHAs (plus :latest, used by local dev).
prune_old_images() {
  local repo image_id tag keep_sha keep
  for repo in pohvala-backend pohvala-frontend; do
    while IFS=$'\t' read -r image_id tag; do
      [[ -z "$tag" || "$tag" == "<none>" || "$tag" == "latest" ]] && continue
      keep=0
      for keep_sha in "$@"; do
        [[ "$tag" == "$keep_sha" ]] && { keep=1; break; }
      done
      [[ "$keep" -eq 1 ]] || docker rmi "${repo}:${tag}" >/dev/null 2>&1 || true
      : "$image_id"
    done < <(docker images "$repo" --format '{{.ID}}	{{.Tag}}' 2>/dev/null || true)
  done
}
