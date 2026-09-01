from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKUP_SCRIPT = ROOT / "ops" / "backup" / "backup.sh"
RESTORE_SCRIPT = ROOT / "ops" / "backup" / "restore-drill.sh"


def _bash() -> Path:
    if os.name == "nt":
        candidate = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git/bin/bash.exe"
        if candidate.exists():
            return candidate
    return Path("bash")


def _bash_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if os.name == "nt" and len(resolved) >= 3 and resolved[1:3] == ":/":
        return f"/{resolved[0].lower()}{resolved[2:]}"
    return resolved


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\nset -eu\n{body}", encoding="utf-8", newline="\n")
    path.chmod(0o755)


def _run(
    script: Path,
    fake_bin: Path,
    env: dict[str, str],
    *args: Path,
) -> subprocess.CompletedProcess[str]:
    command = 'export PATH="$1:/usr/bin:/bin:$PATH"; script="$2"; shift 2; exec bash "$script" "$@"'
    return subprocess.run(
        [
            str(_bash()),
            "--noprofile",
            "--norc",
            "-c",
            command,
            "backup-test",
            _bash_path(fake_bin),
            _bash_path(script),
            *(_bash_path(arg) for arg in args),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **env},
    )


def _backup_fixture(
    tmp_path: Path,
    *,
    docker_body: str = "printf 'custom-dump'",
    age_body: str | None = None,
    flock_body: str = "exit 0",
    find_body: str | None = None,
) -> tuple[Path, Path, dict[str, str]]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "docker", docker_body)
    _write_executable(
        fake_bin / "age",
        age_body
        or """
output=''
while (( $# )); do
  if [[ "$1" == "--output" ]]; then
    output="$2"
    shift 2
  else
    shift
  fi
done
payload="$(cat)"
printf 'encrypted:%s' "$payload" > "$output"
""",
    )
    _write_executable(fake_bin / "flock", flock_body)
    _write_executable(fake_bin / "install", 'mkdir -p "${@: -1}"')
    _write_executable(fake_bin / "chmod", "exit 0")
    if find_body is not None:
        _write_executable(fake_bin / "find", find_body)

    project_dir = tmp_path / "project"
    backup_dir = tmp_path / "backups"
    recipient_file = tmp_path / "recipient.txt"
    project_dir.mkdir()
    recipient_file.write_text("age1testrecipient\n", encoding="utf-8")

    env = {
        "POHVALA_PROJECT_DIR": _bash_path(project_dir),
        "POHVALA_BACKUP_DIR": _bash_path(backup_dir),
        "POHVALA_AGE_RECIPIENT_FILE": _bash_path(recipient_file),
        "POHVALA_BACKUP_LOCK_FILE": _bash_path(tmp_path / "backup.lock"),
    }
    return fake_bin, backup_dir, env


def test_backup_streams_dump_into_encrypted_archive_without_plaintext(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(tmp_path)

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode == 0, f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    archives = list(backup_dir.glob("pohvala-postgres-*.dump.age"))
    assert len(archives) == 1
    assert archives[0].read_text(encoding="utf-8") == "encrypted:custom-dump"
    assert not list(backup_dir.glob("*.partial"))
    assert not list(backup_dir.glob("*.dump"))


def test_backup_failure_removes_partial_and_preserves_existing_archives(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(
        tmp_path,
        docker_body="printf 'truncated-dump'; exit 42",
    )
    backup_dir.mkdir()
    existing = backup_dir / "pohvala-postgres-20260801T031500Z.dump.age"
    existing.write_text("existing", encoding="utf-8")

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode != 0
    assert existing.read_text(encoding="utf-8") == "existing"
    assert list(backup_dir.glob("*.dump.age")) == [existing]
    assert not list(backup_dir.glob("*.partial"))


def test_backup_fails_when_encryption_fails(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(
        tmp_path,
        age_body="cat >/dev/null; exit 23",
    )

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode != 0
    assert not list(backup_dir.glob("*.dump.age"))
    assert not list(backup_dir.glob("*.partial"))


def test_backup_keeps_seven_newest_archives_and_unrelated_files(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(tmp_path)
    backup_dir.mkdir()
    for day in range(1, 9):
        archive = backup_dir / f"pohvala-postgres-202608{day:02d}T031500Z.dump.age"
        archive.write_text(str(day), encoding="utf-8")
    unrelated = backup_dir / "keep-me.txt"
    unrelated.write_text("unrelated", encoding="utf-8")

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode == 0, result.stderr
    archives = sorted(backup_dir.glob("pohvala-postgres-*.dump.age"), reverse=True)
    assert len(archives) == 7
    assert archives[-1].name == "pohvala-postgres-20260803T031500Z.dump.age"
    assert unrelated.read_text(encoding="utf-8") == "unrelated"


def test_backup_rejects_invalid_retention_before_creating_archive(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(tmp_path)
    env["POHVALA_BACKUP_RETENTION_COUNT"] = "1"

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode == 2
    assert "retention" in result.stderr.lower()
    assert not list(backup_dir.glob("*.dump.age"))


def test_backup_rejects_parallel_run(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(tmp_path, flock_body="exit 1")

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode != 0
    assert "already active" in result.stderr
    assert not list(backup_dir.glob("*.dump.age"))


def test_backup_reports_retention_scan_failure(tmp_path: Path) -> None:
    fake_bin, backup_dir, env = _backup_fixture(tmp_path, find_body="exit 31")

    result = _run(BACKUP_SCRIPT, fake_bin, env)

    assert result.returncode != 0
    assert "retention scan failed" in result.stderr.lower()
    assert len(list(backup_dir.glob("*.dump.age"))) == 1
    assert not list(backup_dir.glob(".retention.*"))


def _restore_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "docker",
        """
printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
case "$1" in
  run)
    printf 'fake-container-id\n'
    exit 0
    ;;
  exec)
    if [[ "$*" == *pg_isready* ]]; then
      if [[ "${FAKE_READY_FAIL:-0}" == "1" ]]; then
        exit 1
      fi
      exit 0
    fi
    if [[ "$*" == *pg_restore* ]]; then
      cat > "$FAKE_RESTORE_PAYLOAD"
      if [[ "${FAKE_RESTORE_FAIL:-0}" == "1" ]]; then
        exit 55
      fi
      exit 0
    fi
    if [[ "$*" == *psql* ]]; then
      printf '%s\n' "${FAKE_TABLE_COUNT:-3}"
      exit 0
    fi
    ;;
  rm)
    if [[ "${FAKE_RM_FAIL:-0}" == "1" ]]; then
      exit 71
    fi
    exit 0
    ;;
esac
exit 64
""",
    )
    _write_executable(
        fake_bin / "age",
        """
if [[ "${FAKE_AGE_FAIL:-0}" == "1" ]]; then
  exit 72
fi
printf 'decrypted-dump'
""",
    )
    _write_executable(fake_bin / "sleep", "exit 0")

    archive = tmp_path / "pohvala-postgres-20260901T031500Z.dump.age"
    identity = tmp_path / "identity.txt"
    archive.write_text("encrypted", encoding="utf-8")
    identity.write_text("AGE-SECRET-KEY-1TEST\n", encoding="utf-8")
    docker_log = tmp_path / "docker.log"
    restore_payload = tmp_path / "restored.dump"
    env = {
        "FAKE_DOCKER_LOG": _bash_path(docker_log),
        "FAKE_RESTORE_PAYLOAD": _bash_path(restore_payload),
        "POHVALA_RESTORE_CONTAINER_NAME": "pohvala-test-restore",
    }
    return fake_bin, archive, identity, env


def test_restore_drill_restores_checks_schema_and_removes_container(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode == 0, f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    assert "restore drill passed" in result.stdout.lower()
    assert (tmp_path / "restored.dump").read_text(encoding="utf-8") == "decrypted-dump"
    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls[0] == (
        "run --detach --rm --name pohvala-test-restore "
        "--env POSTGRES_PASSWORD=restore-drill-only --env POSTGRES_DB=pohvala_restore "
        "postgres:17-alpine"
    )
    assert docker_calls[-1] == "rm -f pohvala-test-restore"


def test_restore_drill_propagates_restore_failure_and_removes_container(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)
    env["FAKE_RESTORE_FAIL"] = "1"

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode != 0
    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls[-1] == "rm -f pohvala-test-restore"


def test_restore_drill_fails_when_container_cannot_be_removed(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)
    env["FAKE_RM_FAIL"] = "1"

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode != 0
    assert "could not remove" in result.stderr.lower()
    assert "restore drill passed" not in result.stdout.lower()


def test_restore_drill_fails_when_decryption_fails_and_removes_container(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)
    env["FAKE_AGE_FAIL"] = "1"

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode != 0
    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls[-1] == "rm -f pohvala-test-restore"


def test_restore_drill_fails_when_required_tables_are_missing(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)
    env["FAKE_TABLE_COUNT"] = "2"

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode != 0
    assert "required tables are missing" in result.stderr.lower()
    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls[-1] == "rm -f pohvala-test-restore"


def test_restore_drill_times_out_when_postgres_never_becomes_ready(tmp_path: Path) -> None:
    fake_bin, archive, identity, env = _restore_fixture(tmp_path)
    env["FAKE_READY_FAIL"] = "1"

    result = _run(RESTORE_SCRIPT, fake_bin, env, archive, identity)

    assert result.returncode != 0
    assert "did not become ready" in result.stderr.lower()
    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls[-1] == "rm -f pohvala-test-restore"
