"""
Obsidian Git Bridge - Core Git operations for Obsidian vaults.
"""

from .git_ops import (
    # Core functions
    init_git_repo,
    configure_gitignore,
    setup_remote,
    initial_commit,
    get_repo_status,
    pull_changes,
    push_changes,
    
    # Exceptions
    GitError,
    GitNotInstalledError,
    NotAGitRepoError,
    RemoteAlreadyExistsError,
    MergeConflictError,
    AuthenticationError,
    PushRejectedError,
    
    # Data classes
    RepoStatus,
    
    # Utilities
    quick_sync,
    get_git_info,
)

__version__ = "0.1.0"

__all__ = [
    # Core functions
    "init_git_repo",
    "configure_gitignore",
    "setup_remote",
    "initial_commit",
    "get_repo_status",
    "pull_changes",
    "push_changes",
    
    # Exceptions
    "GitError",
    "GitNotInstalledError",
    "NotAGitRepoError",
    "RemoteAlreadyExistsError",
    "MergeConflictError",
    "AuthenticationError",
    "PushRejectedError",
    
    # Data classes
    "RepoStatus",
    
    # Utilities
    "quick_sync",
    "get_git_info",
]