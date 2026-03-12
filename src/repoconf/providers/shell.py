"""
ShellGitProvider implementation using subprocess.
"""

import subprocess
import os
from typing import Dict, Optional, List
from .protocol import GitCmdException


class ShellGitProvider:
    """
    GitProvider implementation that executes Git commands using subprocess.
    """

    def _get_env(self, custom_env: Optional[Dict[str, str]]) -> Dict[str, str]:
        env = os.environ.copy()
        if custom_env:
            env.update(custom_env)
        return env

    def run_unchecked(self, args: List[str], env: Optional[Dict[str, str]] = None, input: Optional[str] = None) -> str:
        """
        Executes a Git command directly via subprocess.

        Args:
            args: The git command arguments.
            env: Optional environment variables to merge.
            input: Optional standard input to pass.

        Returns:
            str: The standard output of the command.

        Raises:
            GitCmdException: If the command returns a non-zero exit code.

        >>> provider = ShellGitProvider()
        >>> version = provider.run_unchecked(["version"])
        >>> "git version" in version
        True
        """
        cmd = ["git"] + args
        merged_env = self._get_env(env)
        
        try:
            result = subprocess.run(
                cmd,
                env=merged_env,
                input=input,
                text=True,
                capture_output=True,
                check=False
            )
        except Exception as e:
            raise GitCmdException(f"Failed to execute git command: {e}")

        if result.returncode != 0:
            raise GitCmdException(f"Git command failed with exit code {result.returncode}: {result.stderr.strip()}")
            
        return result.stdout

    def read_blob(self, branch: str, path: str) -> Optional[str]:
        """
        Reads the content of a blob at a specific path on a branch.

        Args:
            branch: The branch name.
            path: The file path within the branch.

        Returns:
            str: The content of the file, or None if the path/branch does not exist.

        Raises:
            GitCmdException: If an unexpected error occurs during reading.
        """
        try:
            # First check if the path exists in the branch using ls-tree
            ls_tree_output = self.run_unchecked(["ls-tree", branch, path])
            if not ls_tree_output.strip():
                return None
            
            # Read the content using cat-file
            content = self.run_unchecked(["cat-file", "blob", f"{branch}:{path}"])
            return content
        except GitCmdException as e:
            # If the branch doesn't exist or isn't a valid object name, return None.
            # E.g. fatal: Not a valid object name __repoconf/default/main
            if "Not a valid object name" in str(e) or "bad revision" in str(e):
                return None
            raise

    def update_ref(self, ref: str, new_sha: str) -> None:
        """
        Updates a branch pointer (reference) to a new commit SHA.

        Args:
            ref: The full reference name.
            new_sha: The commit SHA.

        Raises:
            GitCmdException: If the update fails.
        """
        self.run_unchecked(["update-ref", ref, new_sha])
