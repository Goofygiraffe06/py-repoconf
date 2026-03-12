"""
GitProvider protocol definition.
"""

from typing import Protocol, Dict, Optional, List


class GitCmdException(Exception):
    """Exception raised when a Git command fails."""
    pass


class GitProvider(Protocol):
    """Protocol defining the interface for Git backend providers."""

    def run_unchecked(self, args: List[str], env: Optional[Dict[str, str]] = None, input: Optional[str] = None) -> str:
        """
        Executes a Git command directly.

        Args:
            args: The git command arguments (e.g., ['config', '--get', 'user.name']).
                  The word 'git' should not be included.
            env: Optional environment variables to merge with the existing environment.
            input: Optional standard input to pass to the command.

        Returns:
            str: The standard output of the command.

        Raises:
            GitCmdException: If the command returns a non-zero exit code.

        >>> class DummyProvider:
        ...     def run_unchecked(self, args: List[str], env: Optional[Dict[str, str]] = None, input: Optional[str] = None) -> str:
        ...         return "dummy output\\n"
        >>> p = DummyProvider()
        >>> p.run_unchecked(["version"])
        'dummy output\\n'
        """
        ...

    def read_blob(self, branch: str, path: str) -> Optional[str]:
        """
        Reads the content of a blob at a specific path on a branch.
        Uses `ls-tree` and `cat-file` to get content.

        Args:
            branch: The branch name (e.g., '__repoconf/default/main').
            path: The file path within the branch.

        Returns:
            str: The content of the file, or None if the path/branch does not exist.

        Raises:
            GitCmdException: If an unexpected error occurs during reading.

        >>> class DummyProvider:
        ...     def read_blob(self, branch: str, path: str) -> Optional[str]:
        ...         if branch == "main" and path == "file.txt":
        ...             return "content"
        ...         return None
        >>> p = DummyProvider()
        >>> p.read_blob("main", "file.txt")
        'content'
        """
        ...

    def update_ref(self, ref: str, new_sha: str) -> None:
        """
        Updates a branch pointer (reference) to a new commit SHA.

        Args:
            ref: The full reference name (e.g., 'refs/heads/__repoconf/default/main').
            new_sha: The commit SHA to point the reference to.

        Raises:
            GitCmdException: If the update fails.

        >>> class DummyProvider:
        ...     def update_ref(self, ref: str, new_sha: str) -> None:
        ...         pass
        >>> p = DummyProvider()
        >>> p.update_ref("refs/heads/main", "abcdef123456")
        """
        ...
