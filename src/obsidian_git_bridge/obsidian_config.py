"""Obsidian vault detection and git plugin configuration module.

This module provides utilities for:
- Auto-detecting Obsidian vaults in common locations
- Validating vault structure
- Configuring the obsidian-git plugin for automated backups
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


# Common Obsidian vault locations to check
DEFAULT_VAULT_PATHS: Sequence[str] = [
    "~/Obsidian",
    "~/Documents/Obsidian",
    "~/.obsidian",
    "~/obsidian",
    "~/notes",
    "~/Notes",
]

# Obsidian git plugin configuration template
DEFAULT_OBSIDIAN_GIT_CONFIG = {
    "commitMessage": "vault backup: {{date}}",
    "autoBackupInterval": 10,
    "autoPush": True,
    "autoPull": True,
    "pullBeforePush": True,
    "disablePush": False,
    "disablePopups": False,
    "showStatusBar": True,
    "updateSubmodules": False,
    "syncMethod": "merge",
    "customMessageOnAutoBackup": False,
    "autoBackupAfterFileChange": False,
    "treeStructure": False,
    "refreshSourceControl": True,
    "basePath": "",
    "differentIntervalCommitAndPush": False,
    "changedFilesInStatusBar": False,
    "showedMobileNotice": True,
    "refreshSourceControlTimer": 7000,
    "showBranchStatusBar": True,
    "setLastSaveToLastCommit": False,
    "submoduleRecurseCheckout": False,
    "gitDir": "",
}


class VaultError(Exception):
    """Raised when there's an issue with the Obsidian vault."""


class PluginConfigError(Exception):
    """Raised when there's an issue configuring the obsidian-git plugin."""


def find_vault_path() -> str | None:
    """Auto-detect Obsidian vault in common locations.

    Checks the following locations in order:
    1. ~/Obsidian/
    2. ~/Documents/Obsidian/
    3. ~/.obsidian (hidden)
    4. ~/obsidian/
    5. ~/notes/ or ~/Notes/

    Returns:
        Path to the detected vault, or None if no vault found.
    """
    for path in DEFAULT_VAULT_PATHS:
        expanded_path = Path(path).expanduser()
        if expanded_path.exists() and expanded_path.is_dir():
            # Check if it looks like an Obsidian vault
            if _is_vault_directory(expanded_path):
                return str(expanded_path)
    return None


def _is_vault_directory(path: Path) -> bool:
    """Check if a directory appears to be an Obsidian vault.

    A valid vault typically has a .obsidian directory containing
    configuration files, or contains .md files.

    Args:
        path: Path to check.

    Returns:
        True if the directory appears to be an Obsidian vault.
    """
    # Check for .obsidian config directory
    obsidian_dir = path / ".obsidian"
    if obsidian_dir.exists() and obsidian_dir.is_dir():
        return True

    # Check for markdown files (vault likely contains notes)
    try:
        md_files = list(path.glob("*.md"))
        if len(md_files) > 0:
            return True
    except (PermissionError, OSError):
        pass

    return False


def validate_vault(vault_path: str) -> bool:
    """Check if directory is a valid Obsidian vault.

    A valid vault must:
    - Exist as a directory
    - Be readable/writable
    - Either have a .obsidian directory or contain .md files

    Args:
        vault_path: Path to the potential vault.

    Returns:
        True if the path is a valid Obsidian vault.

    Raises:
        VaultError: If the vault is invalid with detailed reason.
    """
    path = Path(vault_path).expanduser()

    # Check existence
    if not path.exists():
        raise VaultError(f"Vault path does not exist: {vault_path}")

    # Check if it's a directory
    if not path.is_dir():
        raise VaultError(f"Vault path is not a directory: {vault_path}")

    # Check readability
    if not os.access(path, os.R_OK):
        raise VaultError(f"Vault directory is not readable: {vault_path}")

    # Check writability
    if not os.access(path, os.W_OK):
        raise VaultError(f"Vault directory is not writable: {vault_path}")

    # Check if it looks like a vault
    if not _is_vault_directory(path):
        raise VaultError(
            f"Directory does not appear to be an Obsidian vault: {vault_path}\n"
            "Expected either a .obsidian directory or markdown (.md) files."
        )

    return True


def get_vault_name(vault_path: str) -> str:
    """Extract vault name from path.

    Args:
        vault_path: Path to the vault.

    Returns:
        The vault name (directory name).
    """
    path = Path(vault_path).expanduser()
    return path.name


def configure_obsidian_git_plugin(
    vault_path: str,
    interval: int = 10,
    commit_message: str = "vault backup: {{date}}",
) -> None:
    """Configure the obsidian-git plugin for automated backups.

    This modifies or creates the .obsidian/plugins/obsidian-git/data.json
    file to enable:
    - Auto-backup at specified interval (default 10 min)
    - Auto-push to remote
    - Custom commit message template

    Args:
        vault_path: Path to the Obsidian vault.
        interval: Backup interval in minutes (default: 10).
        commit_message: Commit message template (default: "vault backup: {{date}}").

    Raises:
        VaultError: If the vault is invalid.
        PluginConfigError: If the plugin configuration cannot be written.
    """
    # Validate vault first
    validate_vault(vault_path)

    path = Path(vault_path).expanduser()
    plugin_dir = path / ".obsidian" / "plugins" / "obsidian-git"
    config_file = plugin_dir / "data.json"

    # Create plugin directory structure if it doesn't exist
    try:
        plugin_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise PluginConfigError(
            f"Failed to create plugin directory: {plugin_dir}\nError: {e}"
        ) from e

    # Build configuration
    config = DEFAULT_OBSIDIAN_GIT_CONFIG.copy()
    config["autoBackupInterval"] = interval
    config["commitMessage"] = commit_message

    # Write configuration file
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise PluginConfigError(
            f"Failed to write plugin configuration: {config_file}\nError: {e}"
        ) from e

    # Create manifest.json if it doesn't exist (plugin metadata)
    manifest_file = plugin_dir / "manifest.json"
    if not manifest_file.exists():
        manifest = {
            "id": "obsidian-git",
            "name": "Obsidian Git",
            "version": "2.24.1",
            "minAppVersion": "0.12.0",
            "description": "Backup your vault with git.",
            "author": "Vinzent03",
            "authorUrl": "https://github.com/Vinzent03",
            "isDesktopOnly": False,
        }
        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except OSError as e:
            # Non-fatal: manifest is only needed for plugin recognition
            pass


def get_vault_info(vault_path: str | None = None) -> dict:
    """Get comprehensive information about a vault.

    Args:
        vault_path: Path to the vault. If None, attempts auto-detection.

    Returns:
        Dictionary with vault information.

    Raises:
        VaultError: If no vault is found or the vault is invalid.
    """
    if vault_path is None:
        vault_path = find_vault_path()
        if vault_path is None:
            raise VaultError(
                "No Obsidian vault found in common locations.\n"
                f"Checked: {', '.join(DEFAULT_VAULT_PATHS)}\n"
                "Please specify the vault path manually."
            )

    validate_vault(vault_path)

    path = Path(vault_path).expanduser()

    # Count markdown files
    md_count = len(list(path.glob("**/*.md")))

    # Check if git is initialized
    git_dir = path / ".git"
    has_git = git_dir.exists() and git_dir.is_dir()

    # Check if obsidian-git plugin is configured
    plugin_config = path / ".obsidian" / "plugins" / "obsidian-git" / "data.json"
    has_plugin_config = plugin_config.exists()

    return {
        "path": str(path),
        "name": get_vault_name(vault_path),
        "markdown_files": md_count,
        "has_git": has_git,
        "has_obsidian_git_config": has_plugin_config,
    }
