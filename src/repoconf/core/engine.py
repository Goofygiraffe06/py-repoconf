"""Native integration and immutable configuration engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Unpack

from repoconf.core.registry import CommandBuilder, RepoConfigSchema, SetCommandValidator
from repoconf.providers.protocol import GitCmdException, GitProvider
from repoconf.providers.worktree import WorktreeGitProvider


@dataclass
class SetSubcommand:
    """Represents a validated 'set' action."""
    key: str
    value: str


@dataclass
class GetSubcommand:
    """Represents a 'get' action."""
    key: str


class ConfigEngine:
    """
    Bridges the virtual configuration branch with the local repository
    via Git's native configuration stack and a proxy file.
    """

    # region Constants
    INCLUDE_PATH = "../repoconf.config"
    CONFIG_BRANCH = "__repoconf/default/main"
    BACKEND_DIR_NAME = "repoconf_backend"
    MANAGED_FILE_NAME = "repoconf.config"
    # endregion

    # region Lifecycle
    def __init__(self, provider: GitProvider | None = None):
        self.provider = provider or WorktreeGitProvider()

    def clone(self) -> 'ConfigEngine':
        """
        Implements the Clone Pattern for immutability.
        
        >>> engine1 = ConfigEngine()
        >>> engine2 = engine1.clone()
        >>> engine1 is not engine2
        True
        """
        return ConfigEngine(self.provider)
    # endregion

    # region Paths
    @property
    def git_dir(self) -> Path:
        """Dynamically resolve the absolute git directory path."""
        if not hasattr(self, '_git_dir'):
            git_dir = self.provider.run_unchecked(["rev-parse", "--git-dir"]).strip()
            self._git_dir = Path(git_dir).resolve()
        return self._git_dir

    @property
    def proxy_file(self) -> Path:
        """The absolute path to the proxy file inside the git directory."""
        return self.git_dir / self.MANAGED_FILE_NAME

    @property
    def backend_worktree(self) -> Path:
        """Path for the hidden administrative worktree."""
        return self.git_dir / self.BACKEND_DIR_NAME
    # endregion

    # region Internal Setup
    def _setup_native_resolution(self) -> None:
        """
        Idempotently sets up git config --local include.path.
        """
        try:
            # Check if it's already set
            current_includes = self.provider.run_unchecked(["config", "--local", "--get-all", "include.path"]).splitlines()
            if self.INCLUDE_PATH in current_includes:
                return
        except GitCmdException:
            pass  # Key doesn't exist

        self.provider.run_unchecked(["config", "--local", "--add", "include.path", self.INCLUDE_PATH])

    def _ensure_proxy_file(self) -> None:
        """Ensure the stable local proxy file exists under ``.git``."""
        if self.proxy_file.exists():
            return

        self.proxy_file.parent.mkdir(parents=True, exist_ok=True)
        self.proxy_file.write_text("", encoding="utf-8")

    def _ensure_backend(self) -> None:
        """Ensure the administrative worktree is ready."""
        self.provider.ensure_worktree(self.CONFIG_BRANCH, self.backend_worktree)
    # endregion

    # region Commands
    def execute_set(self, cmd: SetSubcommand) -> 'ConfigEngine':
        """
        Execute a single set command against the stable proxy.
        """
        self._ensure_backend()
        self._ensure_proxy_file()
        self._setup_native_resolution()

        # Local write via proxy using Git config file manipulation
        self.provider.run_unchecked(["config", "--file", str(self.proxy_file), cmd.key, cmd.value])

        return self.clone()

    def set(self, **kwargs: Unpack[RepoConfigSchema]) -> 'ConfigEngine':
        """
        High-level Builder method to set configurations.
        Includes built-in validation using the schema registry.

        Returns:
            A new ConfigEngine instance (Clone Pattern).
        """
        # Validate arguments according to schema
        validator = SetCommandValidator(**kwargs)
        validator.validate()

        engine = self.clone()
        commands: list[SetSubcommand] = []
        for prop, value in kwargs.items():
            payload = CommandBuilder.build_set_command(prop=prop, value=value)
            commands.append(SetSubcommand(**payload))

        for cmd in commands:
            engine = engine.execute_set(cmd)

        if commands:
            keys = ", ".join(cmd.key for cmd in commands)
            engine.provider.commit_and_push(engine.proxy_file, f"Update repoconf keys: {keys}")

        return engine

    def execute_get(self, cmd: GetSubcommand) -> str | None:
        """
        Executes a GetSubcommand.
        """
        try:
            return self.provider.run_unchecked(["config", "--get", cmd.key]).strip()
        except GitCmdException:
            return None

    def get(self, prop: str) -> str | None:
        """
        Helper method to get a config value using pythonic property names.
        """
        payload = CommandBuilder.build_get_command(prop=prop)
        return self.execute_get(GetSubcommand(**payload))
    # endregion
