"""Engine tests covering branch-to-proxy synchronization behavior."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Generator

import pytest

from repoconf.constants import INCLUDE_PATH
from repoconf.core.engine import ConfigEngine
from repoconf.providers.protocol import GitCmdException


def write_git_config_value(path: Path, key: str, value: str) -> None:
    """Write a Git-style ``section.key`` value to a config file."""
    parser = configparser.ConfigParser()
    parser.optionxform = lambda optionstr: optionstr
    if path.exists():
        parser.read(path, encoding="utf-8")

    section, option = key.split(".", 1)
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, option, value)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def read_git_config_value(path: Path, key: str) -> str:
    """Read a Git-style ``section.key`` value from a config file."""
    parser = configparser.ConfigParser()
    parser.optionxform = lambda optionstr: optionstr
    parser.read(path, encoding="utf-8")

    section, option = key.split(".", 1)
    return parser.get(section, option)


class FakeGitProvider:
    """Minimal provider that emulates the engine-facing Git behavior."""

    def __init__(
        self,
        git_dir: Path,
        branch: str = "__repoconf/default/main",
        managed_file_name: str = "repoconf.config",
    ) -> None:
        self.git_root_dir = git_dir
        self.git_dir = git_dir
        self.branch = branch
        self.managed_file_name = managed_file_name
        self.include_paths: list[str] = []
        self.branch_blobs: dict[tuple[str, str], str] = {}
        self.commit_messages: list[str] = []

    @property
    def proxy_path(self) -> Path:
        return self.git_dir / self.managed_file_name

    @property
    def backend_path(self) -> Path:
        return self.git_dir / "repoconf_backend"

    def seed_branch_value(self, key: str, value: str) -> None:
        """Seed a value directly in the managed branch snapshot."""
        seed_path = self.git_dir / "branch_seed.config"
        seed_path.unlink(missing_ok=True)
        existing_content = self.branch_blobs.get((self.branch, self.managed_file_name))
        if existing_content is not None:
            seed_path.write_text(existing_content, encoding="utf-8")
        write_git_config_value(seed_path, key, value)
        self.branch_blobs[(self.branch, self.managed_file_name)] = seed_path.read_text(
            encoding="utf-8"
        )
        seed_path.unlink(missing_ok=True)

    def run_unchecked(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        input: str | None = None,
    ) -> str:
        del env, input

        if args == ["rev-parse", "--git-dir"]:
            return f"{self.git_dir}\n"

        if args[:4] == ["config", "--local", "--get-all", "include.path"]:
            if not self.include_paths:
                raise GitCmdException("include.path is not set")
            return "\n".join(self.include_paths) + "\n"

        if args[:4] == ["config", "--local", "--add", "include.path"]:
            self.include_paths.append(args[4])
            return ""

        if len(args) == 5 and args[:2] == ["config", "--file"]:
            write_git_config_value(Path(args[2]), args[3], args[4])
            return ""

        if args[:2] == ["config", "--get"]:
            if not self.proxy_path.exists():
                raise GitCmdException(f"Key {args[2]} not found")
            try:
                return read_git_config_value(self.proxy_path, args[2]) + "\n"
            except (configparser.Error, ValueError):
                raise GitCmdException(f"Key {args[2]} not found") from None

        raise AssertionError(f"Unexpected git command: {args}")

    def ensure_worktree(self, branch: str, path: Path) -> None:
        del branch, path

    def read_blob(self, branch: str, path: str) -> str | None:
        return self.branch_blobs.get((branch, path))

    def update_ref(self, ref: str, new_sha: str) -> None:
        del ref, new_sha

    def commit_and_push(self, path: Path, message: str) -> None:
        self.branch_blobs[(self.branch, self.managed_file_name)] = path.read_text(
            encoding="utf-8"
        )
        self.commit_messages.append(message)


@pytest.fixture
def fake_provider_dir() -> Generator[Path, None, None]:
    """Reuse the workspace root and clean up test artifacts around each test."""
    base_dir = Path.cwd()
    managed_files = [
        base_dir / "repoconf.config",
        base_dir / "branch_seed.config",
        base_dir / "branch_result.config",
    ]
    backups = {
        path: path.read_text(encoding="utf-8")
        for path in managed_files
        if path.exists() and path.is_file()
    }

    for path in managed_files:
        path.unlink(missing_ok=True)

    try:
        yield base_dir
    finally:
        for path in managed_files:
            path.unlink(missing_ok=True)

        for path, content in backups.items():
            path.write_text(content, encoding="utf-8")


def test_engine_get_syncs_proxy_from_branch(fake_provider_dir: Path) -> None:
    provider = FakeGitProvider(fake_provider_dir)
    provider.seed_branch_value("repoconf.version", "2")
    engine = ConfigEngine(provider)

    engine.proxy_file.write_text("", encoding="utf-8")

    assert engine.get("repoconf_version") == "2"
    assert read_git_config_value(engine.proxy_file, "repoconf.version") == "2"
    assert provider.include_paths == [INCLUDE_PATH]


def test_engine_set_preserves_branch_state_when_proxy_is_stale(
    fake_provider_dir: Path,
) -> None:
    provider = FakeGitProvider(fake_provider_dir)
    provider.seed_branch_value("repoconf.version", "1")
    engine = ConfigEngine(provider)

    engine.proxy_file.write_text("", encoding="utf-8")

    engine.set(core_editor="nano")

    branch_path = fake_provider_dir / "branch_result.config"
    branch_path.write_text(
        provider.branch_blobs[(provider.branch, provider.managed_file_name)],
        encoding="utf-8",
    )

    assert read_git_config_value(branch_path, "repoconf.version") == "1"
    assert read_git_config_value(branch_path, "core.editor") == "nano"
    assert provider.commit_messages == ["Update repoconf keys: core.editor"]


def test_engine_set_preserves_all_keys_in_multi_write_batch(
    fake_provider_dir: Path,
) -> None:
    provider = FakeGitProvider(fake_provider_dir)
    provider.seed_branch_value("repoconf.version", "1")
    engine = ConfigEngine(provider)

    engine.set(repoconf_version="2", core_editor="nano")

    branch_path = fake_provider_dir / "branch_result.config"
    branch_path.write_text(
        provider.branch_blobs[(provider.branch, provider.managed_file_name)],
        encoding="utf-8",
    )

    assert read_git_config_value(branch_path, "repoconf.version") == "2"
    assert read_git_config_value(branch_path, "core.editor") == "nano"
    assert provider.commit_messages == [
        "Update repoconf keys: repoconf.version, core.editor"
    ]
