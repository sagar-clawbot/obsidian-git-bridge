"""GitOperations class wrapper for obsidian-git-bridge CLI."""

from pathlib import Path
from typing import Any, Optional

from .git_ops import (
    init_git_repo,
    configure_gitignore,
    setup_remote,
    initial_commit,
    get_repo_status,
    pull_changes,
    push_changes,
    quick_sync,
    get_git_info,
)


class GitOperations:
    """Wrapper class for Git operations to match CLI expectations."""

    def __init__(self, vault_path: Path, verbose: bool = False) -> None:
        """Initialize GitOperations.
        
        Args:
            vault_path: Path to the Obsidian vault
            verbose: Enable verbose logging
        """
        self.vault_path = vault_path
        self.verbose = verbose

    def init_repo(self) -> dict[str, Any]:
        """Initialize Git repository."""
        return init_git_repo(self.vault_path)

    def configure_gitignore(self) -> dict[str, Any]:
        """Configure Obsidian-specific .gitignore."""
        return configure_gitignore(self.vault_path)

    def setup_remote(self, url: str, auth_method: str = "ssh") -> dict[str, Any]:
        """Setup remote repository."""
        return setup_remote(self.vault_path, url, auth_method)

    def initial_commit(self) -> dict[str, Any]:
        """Create initial commit and push."""
        return initial_commit(self.vault_path)

    def get_status(self) -> Any:
        """Get repository status."""
        return get_repo_status(self.vault_path)

    def pull(self) -> dict[str, Any]:
        """Pull changes from remote."""
        return pull_changes(self.vault_path)

    def push(self, message: Optional[str] = None) -> dict[str, Any]:
        """Push changes to remote."""
        return push_changes(self.vault_path, message)

    def sync(self, message: Optional[str] = None) -> dict[str, Any]:
        """Quick sync (pull + push)."""
        return quick_sync(self.vault_path, message)

    def get_info(self) -> dict[str, Any]:
        """Get Git repository info."""
        return get_git_info(self.vault_path)
