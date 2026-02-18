"""
Git operations module for obsidian-git-bridge.

Provides core Git functionality for managing Obsidian vaults with Git version control.
Uses GitPython as the primary interface with subprocess fallback for edge cases.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Try to import GitPython
try:
    import git
    from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    logger.warning("GitPython not available, using subprocess fallback only")


class GitError(Exception):
    """Base exception for Git operations."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class GitNotInstalledError(GitError):
    """Raised when Git is not installed or not in PATH."""
    pass


class NotAGitRepoError(GitError):
    """Raised when operation requires a Git repository but none exists."""
    pass


class RemoteAlreadyExistsError(GitError):
    """Raised when trying to add a remote that already exists."""
    pass


class MergeConflictError(GitError):
    """Raised when a merge conflict occurs during pull/rebase."""
    pass


class AuthenticationError(GitError):
    """Raised when authentication fails for remote operations."""
    pass


class PushRejectedError(GitError):
    """Raised when push is rejected by remote."""
    pass


@dataclass
class RepoStatus:
    """Represents the status of a Git repository."""
    
    is_git_repo: bool
    branch: Optional[str] = None
    has_uncommitted_changes: bool = False
    untracked_files: list[str] = None
    modified_files: list[str] = None
    staged_files: list[str] = None
    commits_ahead: int = 0
    commits_behind: int = 0
    upstream_branch: Optional[str] = None
    can_fast_forward: bool = False
    has_conflicts: bool = False
    
    def __post_init__(self) -> None:
        if self.untracked_files is None:
            self.untracked_files = []
        if self.modified_files is None:
            self.modified_files = []
        if self.staged_files is None:
            self.staged_files = []
    
    @property
    def is_clean(self) -> bool:
        """Check if the working directory is clean."""
        return (
            not self.has_uncommitted_changes
            and not self.untracked_files
            and not self.modified_files
            and not self.staged_files
        )
    
    @property
    def needs_push(self) -> bool:
        """Check if local commits need to be pushed."""
        return self.commits_ahead > 0
    
    @property
    def needs_pull(self) -> bool:
        """Check if remote commits need to be pulled."""
        return self.commits_behind > 0
    
    def __str__(self) -> str:
        if not self.is_git_repo:
            return "Not a Git repository"
        
        lines = [f"On branch: {self.branch or 'unknown'}"]
        
        if self.upstream_branch:
            lines.append(f"Upstream: {self.upstream_branch}")
        
        if self.commits_ahead > 0 or self.commits_behind > 0:
            status = []
            if self.commits_ahead > 0:
                status.append(f"ahead {self.commits_ahead}")
            if self.commits_behind > 0:
                status.append(f"behind {self.commits_behind}")
            lines.append(f"Remote status: {', '.join(status)}")
        
        if self.has_conflicts:
            lines.append("⚠️  Has merge conflicts")
        
        if self.is_clean:
            lines.append("Working directory clean")
        else:
            if self.staged_files:
                lines.append(f"Changes staged: {len(self.staged_files)}")
            if self.modified_files:
                lines.append(f"Modified files: {len(self.modified_files)}")
            if self.untracked_files:
                lines.append(f"Untracked files: {len(self.untracked_files)}")
        
        return "\n".join(lines)


def _check_git_installed() -> None:
    """Check if Git is installed and available in PATH."""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=10
        )
    except FileNotFoundError:
        raise GitNotInstalledError(
            "Git is not installed or not in PATH",
            "Please install Git: https://git-scm.com/downloads"
        )
    except subprocess.TimeoutExpired:
        raise GitNotInstalledError(
            "Git command timed out",
            "Git may be hanging or misconfigured"
        )
    except subprocess.CalledProcessError as e:
        raise GitNotInstalledError(
            f"Git check failed: {e.stderr.decode() if e.stderr else 'unknown error'}"
        )


def _is_git_repo(vault_path: Union[str, Path]) -> bool:
    """Check if a directory is a Git repository."""
    path = Path(vault_path)
    git_dir = path / ".git"
    
    if git_dir.exists() and git_dir.is_dir():
        return True
    
    # Also check with git command for worktrees
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
            timeout=5
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_repo(vault_path: Union[str, Path], must_exist: bool = True) -> Any:
    """Get a GitPython Repo object for the given path."""
    if not GITPYTHON_AVAILABLE:
        raise GitError(
            "GitPython is not available",
            "Install with: pip install GitPython"
        )
    
    path = Path(vault_path)
    
    if must_exist and not _is_git_repo(path):
        raise NotAGitRepoError(
            f"'{path}' is not a Git repository",
            "Run init_git_repo() first to initialize"
        )
    
    try:
        return git.Repo(path)
    except InvalidGitRepositoryError:
        raise NotAGitRepoError(
            f"'{path}' is not a valid Git repository",
            "The .git directory may be corrupted"
        )
    except NoSuchPathError:
        raise GitError(
            f"Path does not exist: {path}",
            "Create the directory before initializing Git"
        )


def init_git_repo(vault_path: Union[str, Path]) -> dict[str, Any]:
    """
    Initialize a Git repository in the given vault path.
    
    Args:
        vault_path: Path to the Obsidian vault directory
        
    Returns:
        Dict with success status and message
        
    Raises:
        GitNotInstalledError: If Git is not installed
        GitError: If initialization fails
    """
    _check_git_installed()
    
    path = Path(vault_path)
    
    # Create directory if it doesn't exist
    if not path.exists():
        logger.info(f"Creating directory: {path}")
        path.mkdir(parents=True, exist_ok=True)
    
    # Check if already a git repo
    if _is_git_repo(path):
        logger.info(f"Git repository already exists at: {path}")
        return {
            "success": True,
            "message": "Git repository already initialized",
            "path": str(path),
            "was_already_init": True
        }
    
    try:
        if GITPYTHON_AVAILABLE:
            repo = git.Repo.init(path)
            logger.info(f"Initialized Git repository at: {path}")
        else:
            # Subprocess fallback
            result = subprocess.run(
                ["git", "init", str(path)],
                capture_output=True,
                check=True,
                text=True,
                timeout=30
            )
            logger.info(f"Initialized Git repository at: {path}")
            logger.debug(f"Git init output: {result.stdout}")
        
        return {
            "success": True,
            "message": "Git repository initialized successfully",
            "path": str(path),
            "was_already_init": False
        }
        
    except Exception as e:
        raise GitError(
            f"Failed to initialize Git repository: {e}",
            "Check directory permissions and disk space"
        )


# Obsidian-specific .gitignore content
DEFAULT_GITIGNORE = """# Obsidian Git Ignore

# Workspace settings (contains personal preferences)
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/workspaces.json

# Plugins (can be large, reinstall via community)
.obsidian/plugins/*/main.js
.obsidian/plugins/*.js
.obsidian/plugins/*.json

# Cache files
.obsidian/cache
.obsidian/graph.json

# Sync settings (if using Obsidian Sync)
.obsidian/sync.json

# OS files
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# Temporary files
*.tmp
*.temp
.tmp/
temp/

# Logs
*.log

# Node modules (if using plugins with npm)
node_modules/

# Build artifacts
dist/
build/

# Backup files
*.bak
*.backup

# Large media files (optional - uncomment if needed)
# *.mp4
# *.mov
# *.avi
# *.mp3
# *.wav

# Vault-specific exclusions
# Add your own patterns below
"""


def configure_gitignore(
    vault_path: Union[str, Path],
    custom_patterns: Optional[list[str]] = None,
    overwrite: bool = False
) -> dict[str, Any]:
    """
    Create Obsidian-specific .gitignore file.
    
    Args:
        vault_path: Path to the Obsidian vault directory
        custom_patterns: Additional patterns to add
        overwrite: Whether to overwrite existing .gitignore
        
    Returns:
        Dict with success status and details
        
    Raises:
        GitError: If writing fails
    """
    path = Path(vault_path)
    gitignore_path = path / ".gitignore"
    
    # Check if already exists and shouldn't overwrite
    if gitignore_path.exists() and not overwrite:
        logger.info(f".gitignore already exists at: {gitignore_path}")
        return {
            "success": True,
            "message": ".gitignore already exists (use overwrite=True to replace)",
            "path": str(gitignore_path),
            "created": False
        }
    
    # Build content
    content = DEFAULT_GITIGNORE
    
    if custom_patterns:
        content += "\n# Custom patterns\n"
        for pattern in custom_patterns:
            content += f"{pattern}\n"
    
    try:
        gitignore_path.write_text(content, encoding="utf-8")
        logger.info(f"Created .gitignore at: {gitignore_path}")
        
        return {
            "success": True,
            "message": ".gitignore created successfully",
            "path": str(gitignore_path),
            "created": True,
            "patterns_count": len(content.strip().split('\n'))
        }
        
    except Exception as e:
        raise GitError(
            f"Failed to create .gitignore: {e}",
            "Check directory permissions"
        )


def setup_remote(
    vault_path: Union[str, Path],
    remote_url: str,
    remote_name: str = "origin",
    auth_method: str = "ssh"
) -> dict[str, Any]:
    """
    Add a remote repository.
    
    Args:
        vault_path: Path to the Git repository
        remote_url: URL of the remote repository
        remote_name: Name for the remote (default: origin)
        auth_method: Authentication method ('ssh' or 'https')
        
    Returns:
        Dict with success status and details
        
    Raises:
        NotAGitRepoError: If not a Git repository
        RemoteAlreadyExistsError: If remote already exists
        GitError: If setup fails
    """
    _check_git_installed()
    
    if not _is_git_repo(vault_path):
        raise NotAGitRepoError(
            f"'{vault_path}' is not a Git repository",
            "Run init_git_repo() first"
        )
    
    # Normalize URL based on auth method
    url = remote_url.strip()
    
    if auth_method == "ssh":
        # Convert HTTPS to SSH if needed
        if url.startswith("https://github.com/"):
            path = url.replace("https://github.com/", "")
            url = f"git@github.com:{path}"
        elif url.startswith("https://gitlab.com/"):
            path = url.replace("https://gitlab.com/", "")
            url = f"git@gitlab.com:{path}"
    elif auth_method == "https":
        # Keep as HTTPS, but warn about credentials
        pass
    else:
        raise GitError(
            f"Unknown auth method: {auth_method}",
            "Use 'ssh' or 'https'"
        )
    
    try:
        if GITPYTHON_AVAILABLE:
            repo = _get_repo(vault_path)
            
            # Check if remote already exists
            try:
                existing = repo.remote(remote_name)
                existing_url = list(existing.urls)[0] if existing.urls else None
                
                if existing_url == url:
                    return {
                        "success": True,
                        "message": f"Remote '{remote_name}' already exists with same URL",
                        "remote_name": remote_name,
                        "url": url,
                        "created": False
                    }
                else:
                    # Update existing remote
                    existing.set_url(url)
                    logger.info(f"Updated remote '{remote_name}' to: {url}")
                    return {
                        "success": True,
                        "message": f"Remote '{remote_name}' updated",
                        "remote_name": remote_name,
                        "url": url,
                        "created": False,
                        "updated": True
                    }
            except ValueError:
                # Remote doesn't exist, create it
                repo.create_remote(remote_name, url)
                logger.info(f"Added remote '{remote_name}': {url}")
        else:
            # Subprocess fallback
            # Check if remote exists
            result = subprocess.run(
                ["git", "-C", str(vault_path), "remote", "get-url", remote_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                existing_url = result.stdout.strip()
                if existing_url == url:
                    return {
                        "success": True,
                        "message": f"Remote '{remote_name}' already exists with same URL",
                        "remote_name": remote_name,
                        "url": url,
                        "created": False
                    }
                else:
                    # Update
                    subprocess.run(
                        ["git", "-C", str(vault_path), "remote", "set-url", remote_name, url],
                        capture_output=True,
                        check=True,
                        timeout=10
                    )
                    return {
                        "success": True,
                        "message": f"Remote '{remote_name}' updated",
                        "remote_name": remote_name,
                        "url": url,
                        "created": False,
                        "updated": True
                    }
        
        return {
            "success": True,
            "message": f"Remote '{remote_name}' added successfully",
            "remote_name": remote_name,
            "url": url,
            "auth_method": auth_method,
            "created": True
        }
        
    except RemoteAlreadyExistsError:
        raise
    except Exception as e:
        raise GitError(
            f"Failed to setup remote: {e}",
            "Check the remote URL and your network connection"
        )


def initial_commit(
    vault_path: Union[str, Path],
    message: str = "Initial commit: Obsidian vault setup",
    push: bool = True
) -> dict[str, Any]:
    """
    Create initial commit and optionally push to main branch.
    
    Args:
        vault_path: Path to the Git repository
        message: Commit message
        push: Whether to push to remote after commit
        
    Returns:
        Dict with success status and details
        
    Raises:
        NotAGitRepoError: If not a Git repository
        GitError: If commit/push fails
    """
    _check_git_installed()
    
    if not _is_git_repo(vault_path):
        raise NotAGitRepoError(
            f"'{vault_path}' is not a Git repository",
            "Run init_git_repo() first"
        )
    
    path = Path(vault_path)
    
    try:
        if GITPYTHON_AVAILABLE:
            repo = _get_repo(vault_path)
            
            # Check if there are any commits already
            try:
                repo.head.commit
                has_commits = True
            except ValueError:
                has_commits = False
            
            if has_commits and not repo.is_dirty(untracked_files=True):
                return {
                    "success": True,
                    "message": "No changes to commit",
                    "path": str(path),
                    "committed": False
                }
            
            # Configure git user if not set (required for commit)
            config = repo.config_reader()
            try:
                config.get_value("user", "name")
            except Exception:
                repo.config_writer().set_value("user", "name", "Obsidian Git Bridge").release()
                logger.info("Set default git user.name")
            
            try:
                config.get_value("user", "email")
            except Exception:
                repo.config_writer().set_value("user", "email", "vault@obsidian.git").release()
                logger.info("Set default git user.email")
            
            # Stage all files
            repo.git.add(A=True)
            logger.debug("Staged all files")
            
            # Commit
            if repo.is_dirty(untracked_files=False) or repo.untracked_files:
                commit = repo.index.commit(message)
                logger.info(f"Created commit: {commit.hexsha[:8]} - {message}")
                committed = True
                commit_sha = commit.hexsha
            else:
                return {
                    "success": True,
                    "message": "No changes to commit",
                    "path": str(path),
                    "committed": False
                }
            
            # Push if requested and remote exists
            pushed = False
            if push:
                try:
                    origin = repo.remote("origin")
                    # Get current branch
                    branch = repo.active_branch.name
                    origin.push(refspec=f"{branch}:{branch}")
                    logger.info(f"Pushed to origin/{branch}")
                    pushed = True
                except ValueError:
                    logger.warning("No origin remote configured, skipping push")
                except GitCommandError as e:
                    if "rejected" in str(e).lower():
                        raise PushRejectedError(
                            "Push was rejected by remote",
                            "Pull changes first to resolve any conflicts"
                        )
                    raise AuthenticationError(
                        "Authentication failed during push",
                        "Check your SSH keys or credentials"
                    )
            
        else:
            # Subprocess fallback
            # Check if there are changes
            status_result = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            if not status_result.stdout.strip():
                return {
                    "success": True,
                    "message": "No changes to commit",
                    "path": str(path),
                    "committed": False
                }
            
            # Configure git user if needed
            for key, default in [("user.name", "Obsidian Git Bridge"), ("user.email", "vault@obsidian.git")]:
                result = subprocess.run(
                    ["git", "-C", str(path), "config", key],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if not result.stdout.strip():
                    subprocess.run(
                        ["git", "-C", str(path), "config", key, default],
                        capture_output=True,
                        check=True,
                        timeout=5
                    )
            
            # Stage and commit
            subprocess.run(
                ["git", "-C", str(path), "add", "-A"],
                capture_output=True,
                check=True,
                timeout=30
            )
            
            commit_result = subprocess.run(
                ["git", "-C", str(path), "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            committed = True
            commit_sha = None
            
            # Extract commit SHA
            sha_result = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if sha_result.returncode == 0:
                commit_sha = sha_result.stdout.strip()
            
            # Push if requested
            pushed = False
            if push:
                push_result = subprocess.run(
                    ["git", "-C", str(path), "push", "origin", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if push_result.returncode == 0:
                    pushed = True
                elif "rejected" in push_result.stderr.lower():
                    raise PushRejectedError(
                        "Push was rejected by remote",
                        "Pull changes first to resolve any conflicts"
                    )
                elif "authentication" in push_result.stderr.lower() or "permission" in push_result.stderr.lower():
                    raise AuthenticationError(
                        "Authentication failed during push",
                        "Check your SSH keys or credentials"
                    )
        
        return {
            "success": True,
            "message": "Initial commit created successfully",
            "path": str(path),
            "committed": committed,
            "commit_sha": commit_sha[:8] if commit_sha else None,
            "pushed": pushed,
            "commit_message": message
        }
        
    except PushRejectedError:
        raise
    except AuthenticationError:
        raise
    except Exception as e:
        raise GitError(
            f"Failed to create initial commit: {e}",
            "Check git configuration and repository status"
        )


def get_repo_status(vault_path: Union[str, Path]) -> RepoStatus:
    """
    Get the status of a Git repository.
    
    Args:
        vault_path: Path to the Git repository
        
    Returns:
        RepoStatus object with detailed status
        
    Raises:
        NotAGitRepoError: If not a Git repository
    """
    _check_git_installed()
    
    path = Path(vault_path)
    
    # Quick check first
    if not _is_git_repo(path):
        return RepoStatus(is_git_repo=False)
    
    try:
        if GITPYTHON_AVAILABLE:
            try:
                repo = _get_repo(vault_path)
            except NotAGitRepoError:
                return RepoStatus(is_git_repo=False)
            
            # Get branch info
            try:
                branch = repo.active_branch.name
            except TypeError:
                branch = None  # Detached HEAD
            
            # Get upstream info
            upstream_branch = None
            commits_ahead = 0
            commits_behind = 0
            can_fast_forward = False
            
            if branch:
                try:
                    upstream = repo.active_branch.tracking_branch()
                    if upstream:
                        upstream_branch = upstream.name
                        
                        # Fetch to get accurate counts
                        try:
                            repo.remotes.origin.fetch()
                        except Exception:
                            pass  # May fail without network
                        
                        # Get ahead/behind counts
                        local_commit = repo.active_branch.commit
                        remote_commit = upstream.commit
                        
                        commits_ahead = sum(1 for _ in repo.iter_commits(f"{upstream.name}..{branch}"))
                        commits_behind = sum(1 for _ in repo.iter_commits(f"{branch}..{upstream.name}"))
                        
                        # Check if fast-forward is possible
                        try:
                            repo.git.merge_base("--is-ancestor", branch, upstream.name)
                            can_fast_forward = True
                        except GitCommandError:
                            can_fast_forward = False
                            
                except Exception:
                    pass
            
            # Get working directory status
            untracked = repo.untracked_files
            
            modified = []
            staged = []
            has_conflicts = False
            
            # Check if repo has any commits (not empty)
            has_commits = False
            try:
                repo.head.commit
                has_commits = True
            except ValueError:
                pass  # No commits yet
            
            for item in repo.index.diff(None):  # Unstaged changes
                if item.change_type in ['M', 'T']:
                    modified.append(item.a_path)
            
            # Staged changes - compare against HEAD if exists, otherwise everything is staged
            if has_commits:
                for item in repo.index.diff("HEAD"):  # Staged changes
                    if item.change_type in ['A', 'M', 'D', 'R', 'T']:
                        staged.append(item.a_path)
            else:
                # No commits yet - everything in index is staged
                for entry in repo.index.entries.keys():
                    staged.append(entry[0])
            
            # Check for conflicts
            try:
                conflicts = repo.index.unmerged_blobs()
                has_conflicts = bool(conflicts)
            except Exception:
                pass
            
            has_changes = bool(untracked or modified or staged)
            
            return RepoStatus(
                is_git_repo=True,
                branch=branch,
                has_uncommitted_changes=has_changes,
                untracked_files=untracked,
                modified_files=modified,
                staged_files=staged,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind,
                upstream_branch=upstream_branch,
                can_fast_forward=can_fast_forward,
                has_conflicts=has_conflicts
            )
            
        else:
            # Subprocess fallback
            # Get branch
            branch_result = subprocess.run(
                ["git", "-C", str(path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
            
            # Get status in porcelain format
            status_result = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain", "-b"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            untracked = []
            modified = []
            staged = []
            upstream_branch = None
            commits_ahead = 0
            commits_behind = 0
            has_conflicts = False
            
            if status_result.returncode == 0:
                lines = status_result.stdout.strip().split('\n')
                for line in lines:
                    if not line:
                        continue
                    
                    # Parse branch info from first line
                    if line.startswith("##"):
                        parts = line[3:].split('...')
                        if len(parts) > 1:
                            upstream_branch = parts[1].split(' [')[0]
                            # Parse ahead/behind
                            if '[' in line:
                                status_part = line[line.find('[')+1:line.find(']')]
                                if 'ahead' in status_part:
                                    try:
                                        commits_ahead = int(status_part.split('ahead ')[1].split(',')[0])
                                    except (IndexError, ValueError):
                                        pass
                                if 'behind' in status_part:
                                    try:
                                        commits_behind = int(status_part.split('behind ')[1].split(',')[0])
                                    except (IndexError, ValueError):
                                        pass
                        continue
                    
                    # Parse file status
                    if len(line) >= 2:
                        index_status = line[0]
                        worktree_status = line[1]
                        filename = line[3:]
                        
                        if index_status == '?' and worktree_status == '?':
                            untracked.append(filename)
                        elif index_status in 'AMDRTC' and worktree_status == ' ':
                            staged.append(filename)
                        elif index_status in ' MD' or worktree_status in 'MD':
                            modified.append(filename)
                        elif index_status == 'U' or worktree_status == 'U' or index_status == worktree_status == 'D':
                            has_conflicts = True
            
            has_changes = bool(untracked or modified or staged)
            
            return RepoStatus(
                is_git_repo=True,
                branch=branch,
                has_uncommitted_changes=has_changes,
                untracked_files=untracked,
                modified_files=modified,
                staged_files=staged,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind,
                upstream_branch=upstream_branch,
                has_conflicts=has_conflicts
            )
            
    except NotAGitRepoError:
        return RepoStatus(is_git_repo=False)
    except Exception as e:
        logger.error(f"Error getting repo status: {e}")
        return RepoStatus(is_git_repo=False)


def pull_changes(
    vault_path: Union[str, Path],
    rebase: bool = True
) -> dict[str, Any]:
    """
    Pull changes from remote with optional rebase.
    
    Args:
        vault_path: Path to the Git repository
        rebase: Whether to use rebase (default) or merge
        
    Returns:
        Dict with success status and details
        
    Raises:
        NotAGitRepoError: If not a Git repository
        MergeConflictError: If pull results in conflicts
        AuthenticationError: If authentication fails
        GitError: If pull fails for other reasons
    """
    _check_git_installed()
    
    if not _is_git_repo(vault_path):
        raise NotAGitRepoError(
            f"'{vault_path}' is not a Git repository",
            "Run init_git_repo() first"
        )
    
    path = Path(vault_path)
    
    try:
        if GITPYTHON_AVAILABLE:
            repo = _get_repo(vault_path)
            
            # Check for uncommitted changes
            if repo.is_dirty(untracked_files=False):
                raise GitError(
                    "Cannot pull with uncommitted changes",
                    "Commit or stash your changes first"
                )
            
            # Get current branch
            try:
                branch = repo.active_branch.name
            except TypeError:
                raise GitError(
                    "Cannot pull in detached HEAD state",
                    "Checkout a branch first"
                )
            
            # Fetch first
            try:
                repo.remotes.origin.fetch()
            except GitCommandError as e:
                if "authentication" in str(e).lower():
                    raise AuthenticationError(
                        "Authentication failed during fetch",
                        "Check your SSH keys or credentials"
                    )
                raise
            
            # Check if we can fast-forward
            upstream = repo.active_branch.tracking_branch()
            if not upstream:
                raise GitError(
                    "No upstream branch configured",
                    "Set upstream with: git branch --set-upstream-to=origin/" + branch
                )
            
            # Pull with rebase or merge
            try:
                if rebase:
                    repo.git.pull("origin", branch, "--rebase")
                    logger.info(f"Pulled with rebase from origin/{branch}")
                else:
                    repo.git.pull("origin", branch)
                    logger.info(f"Pulled from origin/{branch}")
                    
            except GitCommandError as e:
                error_msg = str(e).lower()
                
                if "conflict" in error_msg:
                    # Abort the rebase if it failed
                    try:
                        repo.git.rebase("--abort")
                    except Exception:
                        pass
                    raise MergeConflictError(
                        "Pull resulted in merge conflicts",
                        "Resolve conflicts manually and continue"
                    )
                elif "authentication" in error_msg:
                    raise AuthenticationError(
                        "Authentication failed",
                        "Check your SSH keys or credentials"
                    )
                else:
                    raise GitError(f"Pull failed: {e}")
            
        else:
            # Subprocess fallback
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if status_result.stdout.strip():
                raise GitError(
                    "Cannot pull with uncommitted changes",
                    "Commit or stash your changes first"
                )
            
            # Get branch
            branch_result = subprocess.run(
                ["git", "-C", str(path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = branch_result.stdout.strip()
            
            # Fetch
            fetch_result = subprocess.run(
                ["git", "-C", str(path), "fetch", "origin"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if fetch_result.returncode != 0:
                if "authentication" in fetch_result.stderr.lower():
                    raise AuthenticationError(
                        "Authentication failed during fetch",
                        "Check your SSH keys or credentials"
                    )
                raise GitError(f"Fetch failed: {fetch_result.stderr}")
            
            # Pull
            pull_cmd = ["git", "-C", str(path), "pull", "origin", branch]
            if rebase:
                pull_cmd.append("--rebase")
            
            pull_result = subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if pull_result.returncode != 0:
                error = pull_result.stderr.lower()
                
                if "conflict" in error:
                    # Abort rebase
                    subprocess.run(
                        ["git", "-C", str(path), "rebase", "--abort"],
                        capture_output=True,
                        timeout=10
                    )
                    raise MergeConflictError(
                        "Pull resulted in merge conflicts",
                        "Resolve conflicts manually and continue"
                    )
                elif "authentication" in error:
                    raise AuthenticationError(
                        "Authentication failed",
                        "Check your SSH keys or credentials"
                    )
                else:
                    raise GitError(f"Pull failed: {pull_result.stderr}")
        
        return {
            "success": True,
            "message": "Pull completed successfully",
            "path": str(path),
            "rebase": rebase
        }
        
    except MergeConflictError:
        raise
    except AuthenticationError:
        raise
    except GitError:
        raise
    except Exception as e:
        raise GitError(
            f"Failed to pull changes: {e}",
            "Check your network connection and remote configuration"
        )


def push_changes(
    vault_path: Union[str, Path],
    message: Optional[str] = None,
    push_all_branches: bool = False
) -> dict[str, Any]:
    """
    Commit changes and push to remote.
    
    Args:
        vault_path: Path to the Git repository
        message: Commit message (auto-generated if None)
        push_all_branches: Whether to push all branches
        
    Returns:
        Dict with success status and details
        
    Raises:
        NotAGitRepoError: If not a Git repository
        PushRejectedError: If push is rejected
        AuthenticationError: If authentication fails
        GitError: If commit/push fails
    """
    _check_git_installed()
    
    if not _is_git_repo(vault_path):
        raise NotAGitRepoError(
            f"'{vault_path}' is not a Git repository",
            "Run init_git_repo() first"
        )
    
    path = Path(vault_path)
    
    # Auto-generate message if not provided
    if message is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Vault sync: {timestamp}"
    
    try:
        if GITPYTHON_AVAILABLE:
            repo = _get_repo(vault_path)
            
            # Check for changes
            if not repo.is_dirty(untracked_files=True):
                # Still try to push in case there are unpushed commits
                logger.info("No local changes to commit")
                committed = False
            else:
                # Stage all
                repo.git.add(A=True)
                
                # Commit
                commit = repo.index.commit(message)
                logger.info(f"Created commit: {commit.hexsha[:8]} - {message}")
                committed = True
            
            # Push
            try:
                origin = repo.remote("origin")
                
                if push_all_branches:
                    origin.push(all=True)
                    logger.info("Pushed all branches")
                else:
                    branch = repo.active_branch.name
                    origin.push(refspec=f"{branch}:{branch}")
                    logger.info(f"Pushed {branch} to origin")
                    
            except GitCommandError as e:
                error_msg = str(e).lower()
                
                if "rejected" in error_msg:
                    raise PushRejectedError(
                        "Push was rejected by remote",
                        "Pull changes first to resolve any conflicts"
                    )
                elif "authentication" in error_msg or "permission" in error_msg:
                    raise AuthenticationError(
                        "Authentication failed during push",
                        "Check your SSH keys or credentials"
                    )
                else:
                    raise GitError(f"Push failed: {e}")
                    
        else:
            # Subprocess fallback
            # Check for changes
            status_result = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            committed = False
            if status_result.stdout.strip():
                # Stage and commit
                subprocess.run(
                    ["git", "-C", str(path), "add", "-A"],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                
                subprocess.run(
                    ["git", "-C", str(path), "commit", "-m", message],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                committed = True
                logger.info(f"Created commit: {message}")
            
            # Push
            push_cmd = ["git", "-C", str(path), "push"]
            if push_all_branches:
                push_cmd.append("--all")
            else:
                push_cmd.extend(["origin", "HEAD"])
            
            push_result = subprocess.run(
                push_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if push_result.returncode != 0:
                error = push_result.stderr.lower()
                
                if "rejected" in error:
                    raise PushRejectedError(
                        "Push was rejected by remote",
                        "Pull changes first to resolve any conflicts"
                    )
                elif "authentication" in error or "permission" in error:
                    raise AuthenticationError(
                        "Authentication failed during push",
                        "Check your SSH keys or credentials"
                    )
                else:
                    raise GitError(f"Push failed: {push_result.stderr}")
        
        return {
            "success": True,
            "message": "Changes pushed successfully",
            "path": str(path),
            "committed": committed,
            "pushed": True,
            "commit_message": message if committed else None
        }
        
    except PushRejectedError:
        raise
    except AuthenticationError:
        raise
    except GitError:
        raise
    except Exception as e:
        raise GitError(
            f"Failed to push changes: {e}",
            "Check your network connection and remote configuration"
        )


# Convenience functions for CLI usage

def quick_sync(vault_path: Union[str, Path], message: Optional[str] = None) -> dict[str, Any]:
    """
    Quick sync: pull, commit, push in one operation.
    
    Args:
        vault_path: Path to the Git repository
        message: Commit message
        
    Returns:
        Dict with combined operation results
    """
    results = {
        "success": False,
        "operations": {},
        "path": str(vault_path)
    }
    
    # Pull first
    try:
        pull_result = pull_changes(vault_path)
        results["operations"]["pull"] = pull_result
    except GitError as e:
        results["operations"]["pull"] = {"error": str(e), "details": e.details}
        return results
    
    # Then push (commits if needed)
    try:
        push_result = push_changes(vault_path, message=message)
        results["operations"]["push"] = push_result
        results["success"] = True
    except GitError as e:
        results["operations"]["push"] = {"error": str(e), "details": e.details}
        return results
    
    return results


def get_git_info(vault_path: Union[str, Path]) -> dict[str, Any]:
    """
    Get comprehensive Git information about a vault.
    
    Args:
        vault_path: Path to the vault
        
    Returns:
        Dict with git information
    """
    info = {
        "path": str(vault_path),
        "is_git_repo": False,
        "git_installed": False,
        "git_version": None,
        "repo": None
    }
    
    # Check git installation
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["git_installed"] = True
            info["git_version"] = result.stdout.strip()
    except Exception:
        pass
    
    # Check if it's a repo
    status = get_repo_status(vault_path)
    info["is_git_repo"] = status.is_git_repo
    info["status"] = status
    
    if status.is_git_repo and info["git_installed"]:
        # Get remotes
        try:
            if GITPYTHON_AVAILABLE:
                repo = _get_repo(vault_path)
                info["remotes"] = [
                    {"name": r.name, "url": list(r.urls)[0] if r.urls else None}
                    for r in repo.remotes
                ]
            else:
                result = subprocess.run(
                    ["git", "-C", str(vault_path), "remote", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    remotes = {}
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split()
                            if len(parts) >= 2:
                                remotes[parts[0]] = parts[1]
                    info["remotes"] = [{"name": k, "url": v} for k, v in remotes.items()]
        except Exception as e:
            info["remotes_error"] = str(e)
    
    return info