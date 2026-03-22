"""Worktree-based Git provider implementation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from repoconf.providers.protocol import GitCmdException


class WorktreeGitProvider:
    """Default provider using a hidden administrative worktree under ``.git``."""

    # region Setup
    def __init__(
        self,
        branch: str = "__repoconf/default/main",
        backend_dir_name: str = "repoconf_backend",
        managed_file_name: str = "repoconf.config",
    ) -> None:
        self.branch = branch
        self.backend_dir_name = backend_dir_name
        self.managed_file_name = managed_file_name

    @property
    def git_dir(self) -> Path:
        """Return the current repository git directory path.

        Returns:
            The absolute path to the git directory.
        """
        if not hasattr(self, "_git_dir"):
            raw = self.run_unchecked(["rev-parse", "--git-dir"]).strip()
            self._git_dir = Path(raw).resolve()
        return self._git_dir

    @property
    def backend_path(self) -> Path:
        """Return the administrative worktree path."""
        return self.git_dir / self.backend_dir_name

    @property
    def proxy_path(self) -> Path:
        """Return the stable local proxy file path."""
        return self.git_dir / self.managed_file_name
    # endregion

    # region Protocol Methods
    def run_unchecked(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        input: str | None = None,
    ) -> str:
        """Run a git command and return stdout.

        Args:
            args: Git command arguments without the ``git`` executable.
            env: Optional environment variables merged into current process env.
            input: Optional stdin payload.

        Returns:
            Stdout text from git.

        Raises:
            GitCmdException: If git exits with non-zero status.
        """
        command = ["git"] + args
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            completed = subprocess.run(
                command,
                env=merged_env,
                input=input,
                text=True,
                capture_output=True,
                check=False,
            )
        except Exception as exc:
            raise GitCmdException(f"Failed to execute git command: {exc}") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise GitCmdException(f"Git command failed with exit code {completed.returncode}: {stderr}")
        return completed.stdout

    def ensure_worktree(self, branch: str, path: Path) -> None:
        """Ensure the hidden administrative worktree exists and tracks the branch.

        Args:
            branch: The config branch name.
            path: Target administrative worktree path.
        """
        worktree_path = Path(path)
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        if not (worktree_path / ".git").exists():
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
            self.run_unchecked(["worktree", "add", "--force", "--detach", str(worktree_path)])

        has_branch = True
        try:
            self.run_unchecked(["show-ref", "--verify", f"refs/heads/{branch}"])
        except GitCmdException:
            has_branch = False

        if has_branch:
            self.run_unchecked(["-C", str(worktree_path), "checkout", branch])
        else:
            self.run_unchecked(["-C", str(worktree_path), "checkout", "--orphan", branch])

        # Ensure the managed file exists in the backend worktree.
        backend_file = worktree_path / self.managed_file_name
        if not backend_file.exists():
            backend_file.write_text("", encoding="utf-8")

    def read_blob(self, branch: str, path: str) -> str | None:
        """Read the content of a blob from a branch or ref."""
        try:
            ls_tree_output = self.run_unchecked(["ls-tree", branch, path])
            if not ls_tree_output.strip():
                return None

            return self.run_unchecked(["cat-file", "blob", f"{branch}:{path}"])
        except GitCmdException as exc:
            if "Not a valid object name" in str(exc) or "bad revision" in str(exc):
                return None
            raise

    def update_ref(self, ref: str, new_sha: str) -> None:
        """Atomically update a Git ref."""
        self.run_unchecked(["update-ref", ref, new_sha])

    def commit_and_push(self, path: Path, message: str) -> None:
        """Persist managed config updates to the worktree branch.

        Args:
            path: Stable proxy file path under ``.git``.
            message: Commit message.
        """
        self.ensure_worktree(self.branch, self.backend_path)

        proxy_path = Path(path)
        backend_file = self.backend_path / self.managed_file_name
        backend_file.parent.mkdir(parents=True, exist_ok=True)

        if proxy_path.exists():
            shutil.copyfile(proxy_path, backend_file)
        else:
            backend_file.write_text("", encoding="utf-8")

        self.run_unchecked(["-C", str(self.backend_path), "add", self.managed_file_name])

        # Skip commit when there is no staged diff.
        diff = self.run_unchecked(["-C", str(self.backend_path), "diff", "--cached", "--name-only"]).strip()
        if not diff:
            return

        env = {
            "GIT_AUTHOR_NAME": "repoconf",
            "GIT_AUTHOR_EMAIL": "repoconf@local",
            "GIT_COMMITTER_NAME": "repoconf",
            "GIT_COMMITTER_EMAIL": "repoconf@local",
        }
        self.run_unchecked(["-C", str(self.backend_path), "commit", "-m", message], env=env)

        # Push is best-effort because many repos have no default push target.
        try:
            self.run_unchecked(["-C", str(self.backend_path), "push", "-u", "origin", self.branch])
        except GitCmdException:
            pass
    # endregion
