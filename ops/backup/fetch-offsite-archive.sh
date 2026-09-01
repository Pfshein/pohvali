#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# < 1 || $# > 2 )); then
  printf 'usage: %s DEST_DIR [ARCHIVE_NAME]\n' "${0##*/}" >&2
  exit 2
fi

destination_dir="$1"
archive_name="${2:-}"

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

if [[ "$destination_dir" != /* ]]; then
  printf 'destination directory must be absolute\n' >&2
  exit 2
fi

if [[ ! -d "$destination_dir" ]]; then
  printf 'destination directory does not exist: %s\n' "$destination_dir" >&2
  exit 2
fi

archive_name_pattern='^pohvala-postgres-[0-9]{8}T[0-9]{6}Z[.]dump[.]age$'
if [[ -n "$archive_name" ]] && ! [[ "$archive_name" =~ $archive_name_pattern ]]; then
  printf 'archive name does not match the backup naming scheme\n' >&2
  exit 2
fi

for dependency in rclone sort chmod; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf 'required command is missing: %s\n' "$dependency" >&2
    exit 2
  fi
done

remote_root="$(offsite_remote_root)"

if [[ -z "$archive_name" ]]; then
  listing=""
  if ! listing="$(offsite_rclone lsf --files-only "$remote_root")"; then
    printf 'offsite listing failed\n' >&2
    exit 1
  fi
  candidates=()
  while IFS= read -r candidate; do
    if [[ "$candidate" =~ $archive_name_pattern ]]; then
      candidates+=("$candidate")
    fi
  done <<< "$listing"
  if (( ${#candidates[@]} == 0 )); then
    printf 'no offsite archives found\n' >&2
    exit 1
  fi
  mapfile -t candidates < <(printf '%s\n' "${candidates[@]}" | sort -r)
  archive_name="${candidates[0]}"
fi

target_path="$destination_dir/$archive_name"
if [[ -e "$target_path" ]]; then
  printf 'target file already exists: %s\n' "$target_path" >&2
  exit 1
fi

if ! offsite_rclone copyto "$remote_root/$archive_name" "$target_path"; then
  printf 'offsite download failed\n' >&2
  exit 1
fi

if [[ ! -s "$target_path" ]]; then
  rm -f -- "$target_path"
  printf 'downloaded archive is empty\n' >&2
  exit 1
fi

chmod 0600 -- "$target_path"
printf '%s\n' "$target_path"
