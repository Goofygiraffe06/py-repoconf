"""Shared repoconf exceptions."""


class RepoconfException(Exception):
    """Base exception for repoconf failures."""


class GitCmdException(RepoconfException):
    """Exception raised when a Git command fails."""
