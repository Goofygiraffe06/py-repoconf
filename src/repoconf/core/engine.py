"""
Native Integration and Config Engine.
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional, Any

from repoconf.providers.protocol import GitProvider, GitCmdException
from repoconf.core.store import VirtualStore
from repoconf.core.registry import SetCommandValidator, RepoConfigSchema

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack


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

    INCLUDE_PATH = "../repoconf.config"

    def __init__(self, provider: GitProvider, store: Optional[VirtualStore] = None):
        self.provider = provider
        self.store = store or VirtualStore(provider)

    def clone(self) -> 'ConfigEngine':
        """
        Implements the Clone Pattern for immutability.
        
        >>> from repoconf.providers.shell import ShellGitProvider
        >>> engine1 = ConfigEngine(ShellGitProvider())
        >>> engine2 = engine1.clone()
        >>> engine1 is not engine2
        True
        """
        return ConfigEngine(self.provider, self.store.clone())

    @property
    def git_dir(self) -> str:
        """Dynamically resolve the absolute git directory path."""
        if not hasattr(self, '_git_dir'):
            git_dir = self.provider.run_unchecked(["rev-parse", "--git-dir"]).strip()
            self._git_dir = os.path.abspath(git_dir)
        return self._git_dir

    @property
    def proxy_file(self) -> str:
        """The absolute path to the proxy file inside the git directory."""
        return os.path.join(self.git_dir, "repoconf.config").replace("\\", "/")

    def _setup_native_resolution(self) -> None:
        """
        Idempotently sets up git config --local include.path.
        """
        try:
            # Check if it's already set
            current_includes = self.provider.run_unchecked(["config", "--local", "--get-all", "include.path"]).splitlines()
            if self.proxy_file in current_includes:
                return
        except GitCmdException:
            pass  # Key doesn't exist
            
        self.provider.run_unchecked(["config", "--local", "--add", "include.path", self.proxy_file])

    def _ensure_proxy_file(self) -> None:
        """
        Ensures the local proxy file exists, syncing from the store if it's empty locally
        but exists remotely.
        """
        if os.path.exists(self.proxy_file):
            return

        os.makedirs(os.path.dirname(self.proxy_file), exist_ok=True)

        content = self.store.get_file_content("repoconf.config")
        if content is not None:
            with open(self.proxy_file, "w") as f:
                f.write(content)
        else:
            with open(self.proxy_file, "w") as f:
                pass # Create empty file

    def execute_set(self, cmd: SetSubcommand) -> 'ConfigEngine':
        """
        Executes a SetSubcommand:
        1. Ensures proxy and resolution are set up.
        2. Writes to the local proxy file using standard git config.
        3. Commits the proxy file to the virtual store.
        """
        self._ensure_proxy_file()
        self._setup_native_resolution()

        # Local write via proxy using Git config file manipulation
        self.provider.run_unchecked(["config", "--file", self.proxy_file, cmd.key, cmd.value])

        # Commit proxy file to the store
        new_store = self.store.commit_file(self.proxy_file, "repoconf.config", f"Update {cmd.key} to {cmd.value}")
        
        # Return a new engine with the new store
        return ConfigEngine(self.provider, new_store)

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

        engine = self
        for prop, value in kwargs.items():
            # Convert python kwargs format back to git config format (user_name -> user.name)
            key = prop.replace('_', '.')
            cmd = SetSubcommand(key=key, value=str(value)) # Ensure value is string
            engine = engine.execute_set(cmd)
            
        return engine

    def execute_get(self, cmd: GetSubcommand) -> Optional[str]:
        """
        Executes a GetSubcommand.
        """
        try:
            return self.provider.run_unchecked(["config", "--get", cmd.key]).strip()
        except GitCmdException:
            return None

    def get(self, prop: str) -> Optional[str]:
        """
        Helper method to get a config value using pythonic property names.
        """
        key = prop.replace('_', '.')
        return self.execute_get(GetSubcommand(key=key))
