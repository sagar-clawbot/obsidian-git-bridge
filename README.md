# Obsidian Git Bridge

Automate Obsidian vault Git setup for cross-device sync.

## Installation

```bash
pip install obsidian-git-bridge
```

## Quick Start

```bash
# Initialize Git in your Obsidian vault
obsidian-git-bridge init

# Setup remote repository
obsidian-git-bridge setup-remote

# Check sync status
obsidian-git-bridge status

# Manual sync
obsidian-git-bridge sync-now
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize Git repo in vault |
| `setup-remote` | Configure GitHub/GitLab remote |
| `setup-vps` | Generate VPS setup instructions/scripts |
| `status` | Check sync status |
| `doctor` | Diagnose issues |
| `sync-now` | Manual sync trigger |

## Options

- `--vault-path PATH` - Specify vault location (auto-detected if omitted)
- `--verbose` - Enable verbose logging
- `--help` - Show help message

## License

MIT
