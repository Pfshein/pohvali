#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${POHVALA_PROJECT_DIR:-/opt/pohvali}"
BACKUP_DIR="${POHVALA_BACKUP_DIR:-/var/backups/pohvali/postgres}"
RECIPIENT_FILE="${POHVALA_AGE_RECIPIENT_FILE:-/etc/pohvali-backup/recipients.txt}"
RETENTION_COUNT="${POHVALA_BACKUP_RETENTION_COUNT:-7}"
LOCK_FILE="${POHVALA_BACKUP_LOCK_FILE:-$BACKUP_DIR/.backup.lock}"

for path in "$PROJECT_DIR" "$BACKUP_DIR" "$RECIPIENT_FILE" "$LOCK_FILE"; do
  if [[ "$path" != /* ]]; then
    printf 'backup configuration paths must be absolute\n' >&2
    exit 2
  fi
done

if [[ ! "$RETENTION_COUNT" =~ ^[0-9]+$ ]] \
  || (( RETENTION_COUNT < 2 || RETENTION_COUNT > 365 )); then
  printf 'backup retention must be an integer from 2 to 365\n' >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
offsite_common="$script_dir/offsite-common.sh"
if [[ ! -r "$offsite_common" ]]; then
  printf 'offsite helper is missing: %s\n' "$offsite_common" >&2
  exit 2
fi
# shellcheck source=offsite-common.sh
source "$offsite_common"
offsite_load_config
offsite_validate

dependencies=(docker age find flock mktemp sort)
if [[ "$OFFSITE_ENABLED" == 1 ]]; then
  dependencies+=(rclone)
fi
for dependency in "${dependencies[@]}"; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf 'required command is missing: %s\n' "$dependency" >&2
    exit 2
  fi
done

if [[ ! -d "$PROJECT_DIR" ]]; then
  printf 'project directory does not exist: %s\n' "$PROJECT_DIR" >&2
  exit 2
fi

if [[ ! -r "$RECIPIENT_FILE" ]]; then
  printf 'age recipient file is not readable: %s\n' "$RECIPIENT_FILE" >&2
  exit 2
fi

install -d -m 0700 "$BACKUP_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf 'another backup run is already active\n' >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_name="pohvala-postgres-${timestamp}.dump.age"
archive_path="$BACKUP_DIR/$archive_name"
partial_path="${archive_path}.partial"

if [[ -e "$archive_path" || -e "$partial_path" ]]; then
  printf 'backup path already exists for timestamp: %s\n' "$timestamp" >&2
  exit 1
fi

retention_path=""
cleanup_temporary_files() {
  if [[ -n "${partial_path:-}" && -e "$partial_path" ]]; then
    rm -f -- "$partial_path"
  fi
  if [[ -n "${retention_path:-}" && -e "$retention_path" ]]; then
    rm -f -- "$retention_path"
  fi
}
trap cleanup_temporary_files EXIT INT TERM

(
  cd "$PROJECT_DIR"
  docker compose exec -T postgres sh -eu -c \
    'exec pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-privileges'
) | age --encrypt --recipients-file "$RECIPIENT_FILE" --output "$partial_path"

if [[ ! -s "$partial_path" ]]; then
  printf 'encrypted backup is empty\n' >&2
  exit 1
fi

chmod 0600 "$partial_path"
mv -- "$partial_path" "$archive_path"
partial_path=""

retention_path="$(mktemp --tmpdir="$BACKUP_DIR" '.retention.XXXXXX')"
if ! (
  find "$BACKUP_DIR" -maxdepth 1 -type f \
    -name 'pohvala-postgres-*.dump.age' -print0 | sort -z -r
) > "$retention_path"; then
  printf 'backup retention scan failed\n' >&2
  exit 1
fi

mapfile -d '' scanned_archives < "$retention_path"
archives=("$archive_path")
for candidate in "${scanned_archives[@]}"; do
  if [[ "$candidate" != "$archive_path" ]]; then
    archives+=("$candidate")
  fi
done
for (( index = RETENTION_COUNT; index < ${#archives[@]}; index++ )); do
  rm -f -- "${archives[$index]}"
done

rm -f -- "$retention_path"
retention_path=""

if [[ "$OFFSITE_ENABLED" == 1 ]]; then
  offsite_remote="$(offsite_remote_root)"
  if ! offsite_rclone copy "$BACKUP_DIR" "$offsite_remote" \
    --s3-no-check-bucket --include "$OFFSITE_ARCHIVE_PATTERN"; then
    printf 'offsite upload failed\n' >&2
    exit 1
  fi
  offsite_listing=""
  if ! offsite_listing="$(offsite_rclone lsf --files-only "$offsite_remote")"; then
    printf 'offsite retention scan failed\n' >&2
    exit 1
  fi
  offsite_archives=()
  while IFS= read -r offsite_name; do
    if [[ "$offsite_name" == $OFFSITE_ARCHIVE_PATTERN ]]; then
      offsite_archives+=("$offsite_name")
    fi
  done <<< "$offsite_listing"
  if (( ${#offsite_archives[@]} > 0 )); then
    mapfile -t offsite_archives < <(printf '%s\n' "${offsite_archives[@]}" | sort -r)
  fi
  offsite_kept=0
  for offsite_name in "${offsite_archives[@]}"; do
    if (( offsite_kept >= OFFSITE_RETENTION_COUNT )); then
      if ! offsite_rclone deletefile "$offsite_remote/$offsite_name"; then
        printf 'offsite retention delete failed\n' >&2
        exit 1
      fi
    fi
    offsite_kept=$((offsite_kept + 1))
  done
fi

trap - EXIT INT TERM

archive_size="$(wc -c < "$archive_path")"
printf 'backup complete: %s (%s bytes)\n' "$archive_name" "$archive_size"
if [[ "$OFFSITE_ENABLED" == 1 ]]; then
  printf 'offsite upload complete: %s\n' "$offsite_remote"
fi
