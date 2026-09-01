#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# != 2 )); then
  printf 'usage: %s BACKUP_FILE AGE_IDENTITY_FILE\n' "${0##*/}" >&2
  exit 2
fi

archive_path="$1"
identity_path="$2"
postgres_image="${POHVALA_RESTORE_POSTGRES_IMAGE:-postgres:17-alpine}"
container_name="${POHVALA_RESTORE_CONTAINER_NAME:-pohvala-restore-${$}-${RANDOM}}"

if [[ "$archive_path" != /* || "$identity_path" != /* ]]; then
  printf 'backup and identity paths must be absolute\n' >&2
  exit 2
fi

if [[ ! "$container_name" =~ ^pohvala-[a-zA-Z0-9_.-]+$ ]]; then
  printf 'invalid restore container name\n' >&2
  exit 2
fi

if [[ ! -r "$archive_path" ]]; then
  printf 'encrypted backup is not readable: %s\n' "$archive_path" >&2
  exit 2
fi

if [[ ! -r "$identity_path" ]]; then
  printf 'age identity is not readable: %s\n' "$identity_path" >&2
  exit 2
fi

for dependency in docker age; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf 'required command is missing: %s\n' "$dependency" >&2
    exit 2
  fi
done

container_started=0
remove_container() {
  if (( container_started == 1 )); then
    if docker rm -f "$container_name" >/dev/null 2>&1; then
      container_started=0
      return 0
    fi
    return 1
  fi
  return 0
}

cleanup_on_exit() {
  status=$?
  trap - EXIT INT TERM
  if ! remove_container; then
    printf 'warning: could not remove restore container: %s\n' "$container_name" >&2
    if (( status == 0 )); then
      status=1
    fi
  fi
  exit "$status"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker run --detach --rm \
  --name "$container_name" \
  --env POSTGRES_PASSWORD=restore-drill-only \
  --env POSTGRES_DB=pohvala_restore \
  "$postgres_image" >/dev/null
container_started=1

ready=0
for _attempt in {1..30}; do
  if docker exec "$container_name" \
    pg_isready --username=postgres --dbname=pohvala_restore >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if (( ready != 1 )); then
  printf 'temporary PostgreSQL did not become ready\n' >&2
  exit 1
fi

age --decrypt --identity "$identity_path" "$archive_path" \
  | docker exec -i "$container_name" \
    pg_restore --username=postgres --dbname=pohvala_restore \
      --no-owner --no-privileges --exit-on-error

required_table_count="$(
  docker exec "$container_name" \
    psql --username=postgres --dbname=pohvala_restore \
      --tuples-only --no-align --set=ON_ERROR_STOP=1 \
      --command="SELECT count(DISTINCT table_name) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('alembic_version', 'users', 'praises');"
)"
required_table_count="${required_table_count//[[:space:]]/}"

if [[ "$required_table_count" != "3" ]]; then
  printf 'restore verification failed: required tables are missing\n' >&2
  exit 1
fi

if ! remove_container; then
  printf 'could not remove restore container: %s\n' "$container_name" >&2
  exit 1
fi

printf 'restore drill passed: archive restored into isolated PostgreSQL\n'
