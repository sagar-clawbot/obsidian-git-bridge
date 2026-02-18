"""Doctor module for diagnosing common issues."""

import logging
from pathlib import Path

from git import Repo, GitCommandError


class Doctor:
    """Diagnose and fix common Obsidian Git setup issues."""
    
    def __init__(self, vault_path: Path, verbose: bool = False) -> None:
        self.vault_path = vault_path
        self.verbose = verbose
        self.issues: list[dict] = []
        
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
    
    def run_checks(self, fix: bool = False) -> list[dict]:
        """Run all diagnostic checks."""
        self.issues = []
        
        self._check_git_initialized()
        self._check_gitignore_exists()
        self._check_remote_configured()
        self._check_user_config()
        self._check_ssh_key()
        self._check_large_files()
        
        if fix:
            self._attempt_fixes()
        
        return self.issues
    
    def _check_git_initialized(self) -> None:
        """Check if Git repository is initialized."""
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            self.issues.append({
                "severity": "error",
                "message": "Git repository not initialized",
                "fixable": True,
                "fix_action": "init",
            })
    
    def _check_gitignore_exists(self) -> None:
        """Check if .gitignore exists."""
        gitignore = self.vault_path / ".gitignore"
        if not gitignore.exists():
            self.issues.append({
                "severity": "warning",
                "message": ".gitignore not found (Obsidian workspace files may be tracked)",
                "fixable": True,
                "fix_action": "gitignore",
            })
    
    def _check_remote_configured(self) -> None:
        """Check if remote repository is configured."""
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            return
        
        try:
            repo = Repo(self.vault_path)
            remotes = list(repo.remotes)
            if not remotes:
                self.issues.append({
                    "severity": "warning",
                    "message": "No remote repository configured",
                    "fixable": False,
                    "fix_action": None,
                })
        except GitCommandError as e:
            self.issues.append({
                "severity": "error",
                "message": f"Git error: {e}",
                "fixable": False,
                "fix_action": None,
            })
    
    def _check_user_config(self) -> None:
        """Check if Git user is configured."""
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            return
        
        try:
            repo = Repo(self.vault_path)
            config = repo.config_reader()
            
            try:
                config.get_value("user", "name")
            except Exception:
                self.issues.append({
                    "severity": "warning",
                    "message": "Git user.name not configured",
                    "fixable": True,
                    "fix_action": "user_config",
                })
            
            try:
                config.get_value("user", "email")
            except Exception:
                self.issues.append({
                    "severity": "warning",
                    "message": "Git user.email not configured",
                    "fixable": True,
                    "fix_action": "user_config",
                })
        except GitCommandError:
            pass
    
    def _check_ssh_key(self) -> None:
        """Check if SSH key exists."""
        ssh_dir = Path.home() / ".ssh"
        ssh_keys = list(ssh_dir.glob("id_*"))
        
        if not ssh_keys:
            self.issues.append({
                "severity": "info",
                "message": "No SSH keys found (required for SSH authentication)",
                "fixable": False,
                "fix_action": None,
            })
    
    def _check_large_files(self) -> None:
        """Check for large files that shouldn't be in Git."""
        large_extensions = {".mp4", ".mov", ".avi", ".pdf", ".zip", ".dmg", ".iso"}
        large_files: list[Path] = []
        
        for ext in large_extensions:
            large_files.extend(self.vault_path.rglob(f"*{ext}"))
        
        if large_files:
            self.issues.append({
                "severity": "warning",
                "message": f"Found {len(large_files)} large file(s) that may not belong in Git",
                "fixable": False,
                "fix_action": None,
                "details": [str(f.relative_to(self.vault_path)) for f in large_files[:5]],
            })
    
    def _attempt_fixes(self) -> None:
        """Attempt to fix auto-fixable issues."""
        for issue in self.issues:
            if not issue.get("fixable"):
                continue
            
            action = issue.get("fix_action")
            
            if action == "init":
                from .git_ops import GitOperations
                git_ops = GitOperations(self.vault_path)
                git_ops.init_repo()
                issue["fixed"] = True
            
            elif action == "gitignore":
                from .obsidian_config import ObsidianConfig
                config = ObsidianConfig()
                config.create_gitignore(self.vault_path)
                issue["fixed"] = True
            
            elif action == "user_config":
                try:
                    repo = Repo(self.vault_path)
                    config = repo.config_writer()
                    config.set_value("user", "name", "Obsidian Git Bridge")
                    config.set_value("user", "email", "bridge@obsidian.local")
                    config.release()
                    issue["fixed"] = True
                except GitCommandError:
                    pass
