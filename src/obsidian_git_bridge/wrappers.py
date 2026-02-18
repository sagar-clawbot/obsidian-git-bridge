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
        """Initialize Git repository."""
        return git_ops.init_git_repo(self.vault_path)

    def configure_gitignore(self) -> dict[str, Any]:
        """Configure Obsidian-specific .gitignore."""
        return git_ops.configure_gitignore(self.vault_path)

    def add_remote(self, name: str, url: str) -> dict[str, Any]:
        """Add Git remote (alias for setup_remote for CLI compatibility)."""
        # Determine auth method from URL
        auth_method = "ssh" if url.startswith("git@") else "https"
        return git_ops.setup_remote(self.vault_path, url, auth_method)

    def setup_remote(self, url: str, auth_method: str = "ssh") -> dict[str, Any]:
        """Setup remote repository."""
        return git_ops.setup_remote(self.vault_path, url, auth_method)

    def initial_commit(self) -> dict[str, Any]:
        """Create initial commit and push."""
        return git_ops.initial_commit(self.vault_path)

    def get_status(self) -> dict[str, Any]:
        """Get repository status."""
        status = git_ops.get_repo_status(self.vault_path)
        # Convert RepoStatus to dict for CLI
        return {
            "branch": status.branch,
            "remote": status.remote_url,
            "ahead": status.commits_ahead,
            "behind": status.commits_behind,
            "modified": status.modified_files or [],
            "untracked": status.untracked_files or [],
            "is_clean": status.is_clean(),
        }

    def pull(self) -> dict[str, Any]:
        """Pull changes from remote."""
        return git_ops.pull_changes(self.vault_path)

    def push(self, message: Optional[str] = None) -> dict[str, Any]:
        """Push changes to remote."""
        return git_ops.push_changes(self.vault_path, message)

    def sync(self, message: Optional[str] = None) -> dict[str, Any]:
        """Quick sync (pull + push)."""
        return git_ops.quick_sync(self.vault_path, message)


class ObsidianConfig:
    """Wrapper for Obsidian configuration."""

    # Common vault locations to check
    COMMON_VAULT_PATHS = [
        "~/Documents/Obsidian",
        "~/Obsidian",
        "~/obsidian",
        "~/Dropbox/Obsidian",
        "~/iCloud Drive/Obsidian",
        "~/.obsidian",
    ]

    def __init__(self, vault_path: Optional[Path] = None) -> None:
        self.vault_path = vault_path

    def detect_vault_path(self) -> Optional[Path]:
        """Auto-detect Obsidian vault path from common locations."""
        # First try the obsidian_config module
        path_str = oc.find_vault_path()
        if path_str:
            return Path(path_str).expanduser().resolve()
        
        # Check common locations
        for path_template in self.COMMON_VAULT_PATHS:
            path = Path(path_template).expanduser().resolve()
            if path.exists() and path.is_dir():
                # Check if it has .obsidian folder or markdown files
                if self._looks_like_vault(path):
                    return path
        
        return None

    def _looks_like_vault(self, path: Path) -> bool:
        """Check if directory looks like an Obsidian vault."""
        # Has .obsidian folder?
        if (path / ".obsidian").exists():
            return True
        
        # Has markdown files?
        md_files = list(path.glob("*.md"))
        if len(md_files) > 0:
            return True
        
        # Has subdirectories with markdown?
        for subdir in path.iterdir():
            if subdir.is_dir():
                md_files = list(subdir.glob("*.md"))
                if len(md_files) > 0:
                    return True
        
        return False

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

    def __init__(self, vault_path: Path, output_dir: Path) -> None:
        self.vault_path = vault_path
        self.vault_name = vault_path.name
        self.output_dir = output_dir

    def generate_cron_script(self, schedule: str = "*/15 * * * *") -> Path:
        """Generate cron script (alias for generate_setup_script for CLI compatibility)."""
        # Create the script content
        script_content = f'''#!/bin/bash
# Obsidian Vault Sync Script for VPS
# Auto-generated by obsidian-git-bridge

VAULT_PATH="{self.vault_path}"
LOG_FILE="/var/log/obsidian-{self.vault_name}-sync.log"

cd "$VAULT_PATH" || exit 1

# Pull changes from remote
git pull --rebase origin main >> "$LOG_FILE" 2>&1

# Check for local changes
if ! git diff-index --quiet HEAD --; then
    git add -A
    git commit -m "VPS Auto-sync: $(date)" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
fi
'''
        
        # Write script
        script_path = self.output_dir / f"{self.vault_name}-sync.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)  # Make executable
        
        return script_path

    def generate_cron_job(self) -> str:
        """Generate cron job entry."""
        return f"*/5 * * * * /bin/bash {self.output_dir}/{self.vault_name}-sync.sh"

    def generate_setup_instructions(self) -> Path:
        """Generate setup instructions file."""
        instructions = f'''# VPS Setup Instructions for {self.vault_name}

## 1. Clone the Repository on VPS

```bash
git clone <your-repo-url> {self.vault_path}
```

## 2. Install Sync Script

Copy the sync script to your VPS:
```bash
cp {self.output_dir}/{self.vault_name}-sync.sh ~/obsidian-sync.sh
```

## 3. Set Up Cron Job

Add to crontab:
```bash
crontab -e
```

Add this line:
```
{self.generate_cron_job()}
```

## 4. Test the Sync

Run manually once:
```bash
~/obsidian-sync.sh
```

Check logs:
```bash
tail -f /var/log/obsidian-{self.vault_name}-sync.log
```

---
*Generated by obsidian-git-bridge*
'''
        
        instructions_path = self.output_dir / "VPS_SETUP.md"
        instructions_path.write_text(instructions)
        return instructions_path

    def get_full_setup(self) -> dict[str, Any]:
        """Get complete VPS setup package."""
        return {
            "script": self.generate_cron_script(),
            "cron": self.generate_cron_job(),
            "instructions": self.generate_setup_instructions(),
        }
