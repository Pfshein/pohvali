# Shared PH-704B offsite upload helpers (private S3-compatible object storage).
# Sourced by backup.sh and fetch-offsite-archive.sh; not a standalone executable.

OFFSITE_ARCHIVE_PATTERN='pohvala-postgres-*.dump.age'

offsite_load_config() {
  OFFSITE_ENABLED="${POHVALA_OFFSITE_ENABLED:-0}"
  OFFSITE_ENDPOINT="${POHVALA_OFFSITE_ENDPOINT:-}"
  OFFSITE_REGION="${POHVALA_OFFSITE_REGION:-}"
  OFFSITE_BUCKET="${POHVALA_OFFSITE_BUCKET:-}"
  OFFSITE_PREFIX="${POHVALA_OFFSITE_PREFIX:-}"
  OFFSITE_RETENTION_COUNT="${POHVALA_OFFSITE_RETENTION_COUNT:-14}"
  OFFSITE_ACCESS_KEY_ID="${POHVALA_OFFSITE_ACCESS_KEY_ID:-}"
  OFFSITE_SECRET_ACCESS_KEY="${POHVALA_OFFSITE_SECRET_ACCESS_KEY:-}"
}

offsite_validate() {
  if [[ "$OFFSITE_ENABLED" != "0" && "$OFFSITE_ENABLED" != "1" ]]; then
    printf 'offsite enabled flag must be 0 or 1\n' >&2
    exit 2
  fi
  if [[ "$OFFSITE_ENABLED" != "1" ]]; then
    return 0
  fi
  if [[ "$OFFSITE_ENDPOINT" != https://* ]]; then
    printf 'offsite endpoint must be an https URL\n' >&2
    exit 2
  fi
  if [[ ! "$OFFSITE_REGION" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    printf 'offsite region is invalid\n' >&2
    exit 2
  fi
  if [[ ! "$OFFSITE_BUCKET" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]]; then
    printf 'offsite bucket name is invalid\n' >&2
    exit 2
  fi
  if [[ ! "$OFFSITE_PREFIX" =~ ^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$ ]]; then
    printf 'offsite prefix must be a relative path like postgres\n' >&2
    exit 2
  fi
  if [[ ! "$OFFSITE_RETENTION_COUNT" =~ ^[0-9]+$ ]] \
    || (( OFFSITE_RETENTION_COUNT < 2 || OFFSITE_RETENTION_COUNT > 365 )); then
    printf 'offsite retention must be an integer from 2 to 365\n' >&2
    exit 2
  fi
  if [[ -z "$OFFSITE_ACCESS_KEY_ID" ]]; then
    printf 'offsite access key id is empty\n' >&2
    exit 2
  fi
  if [[ -z "$OFFSITE_SECRET_ACCESS_KEY" ]]; then
    printf 'offsite secret access key is empty\n' >&2
    exit 2
  fi
}

offsite_remote_root() {
  printf 'POHVALA:%s/%s' "$OFFSITE_BUCKET" "$OFFSITE_PREFIX"
}

offsite_rclone() {
  XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp}" \
    RCLONE_CONFIG_POHVALA_TYPE=s3 \
    RCLONE_CONFIG_POHVALA_PROVIDER=Other \
    RCLONE_CONFIG_POHVALA_ENDPOINT="$OFFSITE_ENDPOINT" \
    RCLONE_CONFIG_POHVALA_REGION="$OFFSITE_REGION" \
    RCLONE_CONFIG_POHVALA_LOCATION_CONSTRAINT="$OFFSITE_REGION" \
    RCLONE_CONFIG_POHVALA_ACCESS_KEY_ID="$OFFSITE_ACCESS_KEY_ID" \
    RCLONE_CONFIG_POHVALA_SECRET_ACCESS_KEY="$OFFSITE_SECRET_ACCESS_KEY" \
    rclone "$@"
}
