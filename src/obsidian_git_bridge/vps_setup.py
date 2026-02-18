"""VPS setup and sync script generation module.

This module provides utilities for generating VPS-side setup scripts,
cron entries, and comprehensive setup instructions for obsidian-git-bridge.
"""

from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


# Default paths on VPS
DEFAULT_VPS_VAULT_DIR = "$HOME/obsidian-vaults"
DEFAULT_VPS_SCRIPT_DIR = "$HOME/.local/bin"


class VPSSetupError(Exception):
    """Raised when there's an issue generating VPS setup materials."""


def generate_vps_script(
    vault_name: str,
    repo_url: str,
    vault_dir: str = DEFAULT_VPS_VAULT_DIR,
) -> str:
    """Create sync script content for VPS deployment.

    This script handles:
    - Cloning the repository if it doesn't exist
    - Pulling latest changes
    - Auto-committing any local changes
    - Pushing to remote

    Args:
        vault_name: Name of the Obsidian vault (used for directory name).
        repo_url: Git repository URL.
        vault_dir: Base directory for vault storage on VPS.

    Returns:
        Complete bash script content as a string.

    Raises:
        VPSSetupError: If required parameters are missing or invalid.
    """
    if not vault_name:
        raise VPSSetupError("Vault name is required")
    if not repo_url:
        raise VPSSetupError("Repository URL is required")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    script = f'''#!/bin/bash
# =============================================================================
# Obsidian Git Bridge - VPS Sync Script
# Vault: {vault_name}
# Generated: {timestamp}
# =============================================================================

set -euo pipefail

# Configuration
VAULT_NAME="{vault_name}"
REPO_URL="{repo_url}"
VAULT_BASE_DIR="{vault_dir}"
VAULT_DIR="$VAULT_BASE_DIR/$VAULT_NAME"
LOG_FILE="$HOME/.obsidian-git-bridge/logs/${{VAULT_NAME}}-sync.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}}

# =============================================================================
# MAIN SYNC LOGIC
# =============================================================================

log "Starting sync for vault: $VAULT_NAME"

# Create vault directory if it doesn't exist
if [ ! -d "$VAULT_DIR" ]; then
    log "Vault directory not found. Cloning repository..."
    mkdir -p "$VAULT_BASE_DIR"
    if ! git clone "$REPO_URL" "$VAULT_DIR"; then
        log "ERROR: Failed to clone repository"
        exit 1
    fi
    log "Repository cloned successfully"
else
    # Vault exists, pull latest changes
    cd "$VAULT_DIR"
    
    # Check if it's a git repository
    if [ ! -d ".git" ]; then
        log "ERROR: Directory exists but is not a git repository"
        exit 1
    fi
    
    # Configure git (if not already configured)
    if [ -z "$(git config --get user.email 2>/dev/null || true)" ]; then
        git config user.email "vps-sync@obsidian-git-bridge.local"
        git config user.name "VPS Sync Bot"
    fi
    
    # Pull latest changes
    log "Pulling latest changes..."
    if ! git pull origin "$(git branch --show-current)" --no-rebase; then
        log "WARNING: Pull failed or has conflicts, attempting merge"
        # Try to resolve simple conflicts by favoring incoming changes
        if ! git diff --name-only --diff-filter=U | head -1 | grep -q .; then
            log "No conflicts detected, continuing..."
        else
            log "WARNING: Merge conflicts detected, manual resolution may be required"
        fi
    fi
    
    # Check for local changes
    if [ -n "$(git status --porcelain)" ]; then
        log "Local changes detected, committing..."
        git add -A
        git commit -m "vps-sync: auto-commit $(date '+%Y-%m-%d %H:%M:%S')" || true
        git push origin "$(git branch --show-current)" || log "WARNING: Push failed"
    else
        log "No local changes to commit"
    fi
fi

log "Sync completed successfully"
exit 0
'''
    return script


def generate_cron_entry(
    script_path: str,
    interval_minutes: int = 5,
) -> str:
    """Generate cron line for automated sync.

    Args:
        script_path: Path to the sync script on the VPS.
        interval_minutes: How often to run the sync (default: 5 minutes).

    Returns:
        Cron entry string ready to be added to crontab.

    Raises:
        VPSSetupError: If script_path is empty or interval is invalid.
    """
    if not script_path:
        raise VPSSetupError("Script path is required")
    if interval_minutes < 1 or interval_minutes > 60:
        raise VPSSetupError("Interval must be between 1 and 60 minutes")

    # Calculate cron expression
    # For intervals that divide evenly into 60, use step syntax
    if 60 % interval_minutes == 0:
        minute_expr = f"*/{interval_minutes}"
    else:
        # Generate comma-separated list
        minutes = list(range(0, 60, interval_minutes))
        minute_expr = ",".join(str(m) for m in minutes)

    # Redirect output to log file
    log_file = f"$HOME/.obsidian-git-bridge/logs/cron-$(basename '{script_path}' .sh).log"

    cron_line = f'{minute_expr} * * * * {script_path} >> {log_file} 2>&1'
    return cron_line


def generate_setup_instructions(
    vault_name: str,
    repo_url: str,
    vault_dir: str = DEFAULT_VPS_VAULT_DIR,
    sync_interval: int = 5,
    script_dir: str = DEFAULT_VPS_SCRIPT_DIR,
) -> str:
    """Generate full VPS setup guide with copy-paste ready commands.

    Args:
        vault_name: Name of the Obsidian vault.
        repo_url: Git repository URL.
        vault_dir: Base directory for vault storage on VPS.
        sync_interval: How often to sync (in minutes).
        script_dir: Directory to store sync scripts on VPS.

    Returns:
        Complete setup instructions as formatted text.

    Raises:
        VPSSetupError: If required parameters are missing.
    """
    if not vault_name:
        raise VPSSetupError("Vault name is required")
    if not repo_url:
        raise VPSSetupError("Repository URL is required")

    script_path = f"{script_dir}/obsidian-sync-{vault_name.lower().replace(' ', '-')}.sh"
    script_content = generate_vps_script(vault_name, repo_url, vault_dir)
    cron_entry = generate_cron_entry(script_path, sync_interval)

    instructions = f"""{'='*79}
OBSIDIAN GIT BRIDGE - VPS SETUP GUIDE
{'='*79}

Vault Name: {vault_name}
Repository: {repo_url}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{'='*79}
STEP 1: CREATE SYNC SCRIPT
{'='*79}

Create the sync script directory:

---
mkdir -p {script_dir}
mkdir -p $HOME/.obsidian-git-bridge/logs
---

Create the sync script:

---
cat > {script_path} << 'SCRIPT_EOF'
{script_content}
SCRIPT_EOF
---

Make the script executable:

---
chmod +x {script_path}
---

{'='*79}
STEP 2: TEST THE SYNC SCRIPT
{'='*79}

Run the script manually to verify it works:

---
{script_path}
---

Check the log output:

---
tail -f $HOME/.obsidian-git-bridge/logs/{vault_name}-sync.log
---

{'='*79}
STEP 3: SET UP AUTOMATED SYNC (CRON)
{'='*79}

Add the following line to your crontab:

---
crontab -e
---

Paste this line (syncs every {sync_interval} minutes):

---
# Obsidian Git Bridge - {vault_name}
{cron_entry}
---

To verify the cron entry was added:

---
crontab -l | grep obsidian
---

{'='*79}
STEP 4: VERIFY SETUP
{'='*79}

1. Check that the vault was cloned:
   ls -la {vault_dir}/{vault_name}/

2. Check git status:
   cd {vault_dir}/{vault_name} && git status

3. Monitor logs:
   tail -f $HOME/.obsidian-git-bridge/logs/{vault_name}-sync.log

4. Verify cron is running:
   ps aux | grep cron

{'='*79}
OPTIONAL: MANUAL SYNC COMMANDS
{'='*79}

Force sync now:
  {script_path}

Check git status:
  cd {vault_dir}/{vault_name} && git status

Pull latest:
  cd {vault_dir}/{vault_name} && git pull

Push local changes:
  cd {vault_dir}/{vault_name} && git add -A && git commit -m "manual sync" && git push

{'='*79}
TROUBLESHOOTING
{'='*79}

Issue: "Permission denied" when running script
  Fix: chmod +x {script_path}

Issue: "git: command not found"
  Fix: sudo apt-get install git  (or equivalent for your distro)

Issue: "Could not resolve host"
  Fix: Check network connectivity and repository URL

Issue: Sync conflicts
  Fix: Manually resolve in {vault_dir}/{vault_name}/
        cd {vault_dir}/{vault_name} && git status

{'='*79}
FILES CREATED
{'='*79}

Sync Script:   {script_path}
Vault Location: {vault_dir}/{vault_name}/
Log Files:     $HOME/.obsidian-git-bridge/logs/
Cron Entry:    {cron_entry}

{'='*79}
SETUP COMPLETE
{'='*79}
"""
    return instructions


def write_vps_script_to_file(
    vault_name: str,
    repo_url: str,
    output_path: str,
    vault_dir: str = DEFAULT_VPS_VAULT_DIR,
) -> Path:
    """Generate and write VPS sync script to a file.

    Args:
        vault_name: Name of the Obsidian vault.
        repo_url: Git repository URL.
        output_path: Path where the script should be written.
        vault_dir: Base directory for vault storage on VPS.

    Returns:
        Path object pointing to the created script file.

    Raises:
        VPSSetupError: If the script cannot be written.
    """
    script_content = generate_vps_script(vault_name, repo_url, vault_dir)

    output = Path(output_path).expanduser()

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(script_content)
        # Make executable
        output.chmod(0o755)
    except OSError as e:
        raise VPSSetupError(f"Failed to write script to {output}: {e}") from e

    return output


def generate_docker_compose(
    vaults: Sequence[dict],
    sync_interval: int = 300,
) -> str:
    """Generate docker-compose.yml for containerized VPS sync.

    Args:
        vaults: List of vault configurations, each with 'name' and 'repo_url'.
        sync_interval: Sync interval in seconds (default: 300 = 5 minutes).

    Returns:
        Docker Compose YAML content.
    """
    vault_configs = []
    for vault in vaults:
        name = vault.get("name", "vault")
        repo = vault.get("repo_url", "")
        vault_configs.append(f"      - VAULT_{name.upper()}={repo}")

    env_vars = "\n".join(vault_configs)

    compose = f'''version: "3.8"

services:
  obsidian-git-bridge:
    image: alpine/git:latest
    container_name: obsidian-sync
    environment:
      - SYNC_INTERVAL={sync_interval}
{env_vars}
    volumes:
      - ./vaults:/vaults
      - ./scripts:/scripts:ro
    command: |
      sh -c "
        apk add --no-cache bash curl &&
        while true; do
          for vault in /vaults/*/; do
            if [ -d \"$$vault/.git\" ]; then
              cd \"$$vault\" && git pull && git push
            fi
          done
          sleep {sync_interval}
        done
      "
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  vaults:
    driver: local
'''
    return compose
