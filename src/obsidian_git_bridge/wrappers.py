"""Wrapper classes for obsidian-git-bridge CLI compatibility."""

from pathlib import Path
from typing import Any, Optional

# Import function modules
from . import git_ops
from . import obsidian_config as oc
from . import vps_setup as vs


class GitOperations:
    """Wrapper for Git operations."""

    def __init__(self, vault_path: Path, verbose: bool = False) -> None:
        self.vault_path = vault_path
        self.verbose = verbose

    def is_git_repo(self) -> bool:
        """Check if vault is already a Git repository."""
        git_dir = self.vault_path / ".git"
        return git_dir.exists()

    def init_repo(self) -> dict[str, Any]:
        return git_ops.init_git_repo(self.vault_path)

    def configure_gitignore(self) -> dict[str, Any]:
        return git_ops.configure_gitignore(self.vault_path)

    def setup_remote(self, url: str, auth_method: str = "ssh") -> dict[str, Any]:
        return git_ops.setup_remote(self.vault_path, url, auth_method)

    def initial_commit(self) -> dict[str, Any]:
        return git_ops.initial_commit(self.vault_path)

    def get_status(self) -> Any:
        return git_ops.get_repo_status(self.vault_path)

    def pull(self) -> dict[str, Any]:
        return git_ops.pull_changes(self.vault_path)

    def push(self, message: Optional[str] = None) -> dict[str, Any]:
        return git_ops.push_changes(self.vault_path, message)

    def sync(self, message: Optional[str] = None) -> dict[str, Any]:
        return git_ops.quick_sync(self.vault_path, message)


class ObsidianConfig:
    """Wrapper for Obsidian configuration."""

    def __init__(self, vault_path: Optional[Path] = None) -> None:
        self.vault_path = vault_path

    def detect_vault_path(self) -> Optional[Path]:
        """Auto-detect Obsidian vault path."""
        path_str = oc.find_vault_path()
        return Path(path_str) if path_str else None

    def validate_vault(self, path: Path) -> bool:
        """Validate if path is a valid Obsidian vault."""
        return oc.validate_vault(str(path))

    # Alias for test compatibility
    is_valid_vault = validate_vault

    def get_vault_name(self, path: Path) -> str:
        """Get vault name from path."""
        return oc.get_vault_name(str(path))

    def configure_git_plugin(self, path: Optional[Path] = None, interval: int = 10) -> dict[str, Any]:
        """Configure Obsidian Git plugin."""
        vault_path = path or self.vault_path
        if vault_path is None:
            raise ValueError("Vault path required")
        return oc.configure_obsidian_git_plugin(str(vault_path), interval)

    def create_gitignore(self, path: Optional[Path] = None) -> Path:
        """Create Obsidian-specific .gitignore file."""
        from .git_ops import configure_gitignore
        
        vault_path = path or self.vault_path
        if vault_path is None:
            raise ValueError("Vault path required")
        
        result = configure_gitignore(str(vault_path))
        return Path(result["path"])


class VPSSetupGenerator:
    """Wrapper for VPS setup generation."""

    def __init__(self, vault_name: str, repo_url: str) -> None:
        self.vault_name = vault_name
        self.repo_url = repo_url

    def generate_setup_script(self) -> str:
        """Generate VPS setup script."""
        return vs.generate_vps_setup_script(self.vault_name, self.repo_url)

    def generate_cron_job(self) -> str:
        """Generate cron job entry."""
        return vs.generate_cron_job(self.vault_name)

    def generate_instructions(self) -> str:
        """Generate setup instructions."""
        return vs.generate_setup_instructions(self.vault_name, self.repo_url)

    def get_full_setup(self) -> dict[str, str]:
        """Get complete VPS setup package."""
        return {
            "script": self.generate_setup_script(),
            "cron": self.generate_cron_job(),
            "instructions": self.generate_instructions(),
        }
