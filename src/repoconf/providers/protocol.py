"""Git provider protocol contracts."""

from pathlib import Path
from typing import Protocol

from repoconf.exceptions import GitCmdException

__all__ = ["GitCmdException", "GitProvider"]


class GitProvider(Protocol):
    """Protocol defining the interface for Git backend providers."""

    git_root_dir: Path
    git_dir: Path

    # region Direct Commands
    def run_unchecked(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        input: str | None = None,
    ) -> str:
        """
        Executes a Git command directly.

        Args:
            args: The git command arguments (without the word ``git``).
            env: Optional environment variables to merge with the existing environment.
            input: Optional standard input to pass to the command.

        Returns:
            str: The standard output of the command.

        Raises:
            GitCmdException: If the command returns a non-zero exit code.

        >>> class DummyProvider:
        ...     def run_unchecked(self, args: list[str], env: dict[str, str] | None = None, input: str | None = None) -> str:
        ...         return "dummy output\\n"
        >>> p = DummyProvider()
        >>> p.run_unchecked(["version"])
        'dummy output\\n'
        """
        ...

    # endregion

    # region Worktree Lifecycle
    def ensure_worktree(self, branch: str, path: Path) -> None:
        """
        Idempotently ensures a detached administrative worktree exists.

        Args:
            branch: The configuration branch to manage.
            path: The administrative worktree path.

        Raises:
            GitCmdException: If the worktree cannot be prepared.
        """
        ...

    # endregion

    # region Virtual Tree Access
    def read_blob(self, branch: str, path: str) -> str | None:
        """
        Reads a tracked blob from a branch or ref without touching the worktree.

        Args:
            branch: The branch or ref name to inspect.
            path: The file path within that tree.

        Returns:
            The blob content, or ``None`` when the ref/path does not exist.
        """
        ...

    def update_ref(self, ref: str, new_sha: str) -> None:
        """
        Atomically updates a Git ref to a new commit SHA.

        Args:
            ref: The full reference name.
            new_sha: The commit SHA to write.
        """
        ...

    # endregion

    # region Persistence
    def commit_and_push(self, path: Path, message: str) -> None:
        """
        Stages and commits the managed configuration in provider scope.

        Args:
            path: The stable proxy config path.
            message: The commit message.

        Raises:
            GitCmdException: If the persistence operation fails.

        >>> class DummyProvider:
        ...     def commit_and_push(self, path: Path, message: str) -> None:
        ...         pass
        >>> p = DummyProvider()
        >>> p.commit_and_push(Path("./repoconf.config"), "msg")
        """
        ...

    # endregion
