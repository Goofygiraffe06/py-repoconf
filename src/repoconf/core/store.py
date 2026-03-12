"""
Virtual store logic for direct Object Database (ODB) manipulation.
"""

import os
import tempfile
from typing import Optional
from repoconf.providers.protocol import GitProvider, GitCmdException


class VirtualStore:
    """
    Manages atomic updates to a virtual configuration branch.
    Uses pure Git plumbing to avoid modifying the current HEAD or working directory.
    """

    def __init__(self, provider: GitProvider, branch: str = "refs/heads/__repoconf/default/main"):
        self.provider = provider
        self.branch = branch

    def clone(self) -> 'VirtualStore':
        """
        Implements the Clone Pattern for immutability.
        
        >>> from repoconf.providers.shell import ShellGitProvider
        >>> store1 = VirtualStore(ShellGitProvider())
        >>> store2 = store1.clone()
        >>> store1 is not store2
        True
        """
        return VirtualStore(self.provider, self.branch)

    def _get_parent_commit(self) -> Optional[str]:
        """Gets the current commit SHA of the branch if it exists."""
        try:
            return self.provider.run_unchecked(["rev-parse", "-q", "--verify", self.branch]).strip()
        except GitCmdException:
            return None

    def commit_file(self, local_file_path: str, target_path: str, message: str) -> 'VirtualStore':
        """
        Commits a local file directly to the virtual branch.

        Steps:
        1. hash-object -w
        2. update-index --add --cacheinfo
        3. write-tree
        4. commit-tree
        5. update-ref

        Returns:
            A new instance of VirtualStore (implements Builder/Clone pattern).
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file {local_file_path} not found.")

        # 1. hash-object
        blob_sha = self.provider.run_unchecked(["hash-object", "-w", local_file_path]).strip()

        # Create a temporary index file
        fd, temp_index_path = tempfile.mkstemp(prefix="repoconf_idx_")
        os.close(fd)
        
        env = {"GIT_INDEX_FILE": temp_index_path}

        try:
            parent_sha = self._get_parent_commit()
            if parent_sha:
                # Load existing branch tree into the index
                self.provider.run_unchecked(["read-tree", parent_sha], env=env)

            # 2. update-index
            self.provider.run_unchecked(
                ["update-index", "--add", "--cacheinfo", "100644", blob_sha, target_path],
                env=env
            )

            # 3. write-tree
            tree_sha = self.provider.run_unchecked(["write-tree"], env=env).strip()

            # 4. commit-tree
            commit_args = ["commit-tree", tree_sha, "-m", message]
            if parent_sha:
                commit_args.extend(["-p", parent_sha])
            
            commit_sha = self.provider.run_unchecked(commit_args).strip()

            # 5. update-ref
            self.provider.update_ref(self.branch, commit_sha)

        finally:
            # Cleanup temp index
            if os.path.exists(temp_index_path):
                os.remove(temp_index_path)

        return self.clone()

    def get_file_content(self, path: str) -> Optional[str]:
        """
        Reads a file from the virtual branch.

        >>> from repoconf.providers.shell import ShellGitProvider
        >>> store = VirtualStore(ShellGitProvider(), "refs/heads/invalid_branch_xyz")
        >>> store.get_file_content("test.xy") is None
        True
        """
        return self.provider.read_blob(self.branch, path)
