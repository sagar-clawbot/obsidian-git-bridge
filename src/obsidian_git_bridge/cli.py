"""CLI entry point for Obsidian Git Bridge."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.traceback import install as install_traceback

from . import __version__
from .git_operations import GitOperations
from .obsidian_config import ObsidianConfig
from .vps_setup import VPSSetupGenerator
from .doctor import Doctor

install_traceback()
console = Console()


def get_vault_path(vault_path: str | None) -> Path:
    """Resolve vault path from argument or auto-detect."""
    if vault_path:
        path = Path(vault_path).expanduser().resolve()
        if not path.exists():
            console.print(f"[red]Error: Vault path does not exist: {path}[/red]")
            sys.exit(1)
        return path
    
    # Auto-detect
    config = ObsidianConfig()
    detected = config.detect_vault_path()
    if detected:
        console.print(f"[green]Auto-detected vault: {detected}[/green]")
        return detected
    
    console.print("[red]Error: Could not auto-detect Obsidian vault. Use --vault-path.[/red]")
    sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="obsidian-git-bridge")
@click.option("--vault-path", "-v", type=str, help="Path to Obsidian vault")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, vault_path: str | None, verbose: bool) -> None:
    """Automate Obsidian vault Git setup for cross-device sync."""
    ctx.ensure_object(dict)
    ctx.obj["vault_path"] = vault_path
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--gitignore", is_flag=True, default=True, help="Create Obsidian .gitignore")
@click.pass_context
def init(ctx: click.Context, gitignore: bool) -> None:
    """Initialize Git repository in vault."""
    vault = get_vault_path(ctx.obj["vault_path"])
    verbose = ctx.obj["verbose"]
    
    git_ops = GitOperations(vault, verbose=verbose)
    
    if git_ops.is_git_repo():
        console.print(f"[yellow]Vault already initialized: {vault}[/yellow]")
        return
    
    git_ops.init_repo()
    console.print(f"[green]Initialized Git repo in: {vault}[/green]")
    
    if gitignore:
        obsidian_config = ObsidianConfig()
        obsidian_config.create_gitignore(vault)
        console.print("[green]Created Obsidian .gitignore[/green]")


@cli.command(name="setup-remote")
@click.option("--remote-url", "-r", type=str, help="Remote repository URL")
@click.option("--name", default="origin", help="Remote name")
@click.option("--auth", type=click.Choice(["ssh", "https"]), help="Authentication method")
@click.pass_context
def setup_remote(
    ctx: click.Context, 
    remote_url: str | None, 
    name: str, 
    auth: str | None
) -> None:
    """Configure GitHub/GitLab remote."""
    vault = get_vault_path(ctx.obj["vault_path"])
    verbose = ctx.obj["verbose"]
    
    git_ops = GitOperations(vault, verbose=verbose)
    
    if not git_ops.is_git_repo():
        console.print("[red]Error: Not a Git repository. Run 'init' first.[/red]")
        sys.exit(1)
    
    # Interactive prompt for remote URL
    if not remote_url:
        remote_url = click.prompt("Remote repository URL")
    
    # Determine auth method
    if not auth:
        auth = "ssh" if remote_url.startswith("git@") else "https"
    
    git_ops.add_remote(name, remote_url)
    console.print(f"[green]Added remote '{name}': {remote_url}[/green]")
    
    if auth == "https":
        console.print("[yellow]Note: Configure credentials with: git config credential.helper store[/yellow]")
    else:
        console.print("[green]SSH authentication configured[/green]")


@cli.command(name="setup-vps")
@click.option("--output", "-o", type=Path, help="Output directory for scripts")
@click.option("--cron-schedule", default="*/15 * * * *", help="Cron schedule (default: every 15 min)")
@click.pass_context
def setup_vps(
    ctx: click.Context, 
    output: Path | None, 
    cron_schedule: str
) -> None:
    """Generate VPS setup instructions and scripts."""
    vault = get_vault_path(ctx.obj["vault_path"])
    
    if output is None:
        output = vault / ".obsidian-git-bridge"
    
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    
    vps = VPSSetupGenerator(vault, output)
    vps.generate_cron_script(cron_schedule)
    vps.generate_setup_instructions()
    
    console.print(f"[green]Generated VPS scripts in: {output}[/green]")
    console.print(f"[blue]Cron schedule: {cron_schedule}[/blue]")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check sync status of vault."""
    vault = get_vault_path(ctx.obj["vault_path"])
    verbose = ctx.obj["verbose"]
    
    git_ops = GitOperations(vault, verbose=verbose)
    
    if not git_ops.is_git_repo():
        console.print("[red]Error: Not a Git repository.[/red]")
        sys.exit(1)
    
    status_info = git_ops.get_status()
    
    console.print(f"\n[bold]Vault:[/bold] {vault}")
    console.print(f"[bold]Branch:[/bold] {status_info['branch']}")
    console.print(f"[bold]Remote:[/bold] {status_info['remote'] or 'Not configured'}")
    
    if status_info["ahead"]:
        console.print(f"[yellow]Ahead by {status_info['ahead']} commit(s)[/yellow]")
    if status_info["behind"]:
        console.print(f"[yellow]Behind by {status_info['behind']} commit(s)[/yellow]")
    
    if status_info["modified"]:
        console.print(f"\n[bold]Modified files ({len(status_info['modified'])}):[/bold]")
        for f in status_info["modified"][:10]:
            console.print(f"  • {f}")
        if len(status_info["modified"]) > 10:
            console.print(f"  ... and {len(status_info['modified']) - 10} more")
    else:
        console.print("\n[green]No uncommitted changes[/green]")
    
    if status_info["untracked"]:
        console.print(f"\n[bold]Untracked files ({len(status_info['untracked'])}):[/bold]")
        for f in status_info["untracked"][:5]:
            console.print(f"  • {f}")
        if len(status_info["untracked"]) > 5:
            console.print(f"  ... and {len(status_info['untracked']) - 5} more")


@cli.command()
@click.option("--fix", is_flag=True, help="Attempt to fix issues automatically")
@click.pass_context
def doctor(ctx: click.Context, fix: bool) -> None:
    """Diagnose common issues with vault Git setup."""
    vault = get_vault_path(ctx.obj["vault_path"])
    verbose = ctx.obj["verbose"]
    
    doc = Doctor(vault, verbose=verbose)
    issues = doc.run_checks(fix=fix)
    
    if not issues:
        console.print("[green]✓ All checks passed![/green]")
        return
    
    console.print(f"\n[yellow]Found {len(issues)} issue(s):[/yellow]")
    for issue in issues:
        status = "[green]✓ Fixed[/green]" if issue.get("fixed") else "[red]✗[/red]"
        console.print(f"{status} {issue['message']}")


@cli.command(name="sync-now")
@click.option("--message", "-m", default="Auto-sync from obsidian-git-bridge", help="Commit message")
@click.option("--push", is_flag=True, default=True, help="Push after commit")
@click.pass_context
def sync_now(ctx: click.Context, message: str, push: bool) -> None:
    """Manual sync trigger - commit and push changes."""
    vault = get_vault_path(ctx.obj["vault_path"])
    verbose = ctx.obj["verbose"]
    
    git_ops = GitOperations(vault, verbose=verbose)
    
    if not git_ops.is_git_repo():
        console.print("[red]Error: Not a Git repository.[/red]")
        sys.exit(1)
    
    # Pull first to avoid conflicts
    try:
        git_ops.pull()
        console.print("[green]Pulled latest changes[/green]")
    except Exception as e:
        if verbose:
            console.print(f"[yellow]Pull warning: {e}[/yellow]")
    
    # Stage and commit
    result = git_ops.commit_all(message)
    
    if result["committed"]:
        console.print(f"[green]Committed: {result['message']}[/green]")
    else:
        console.print("[blue]No changes to commit[/blue]")
    
    # Push if enabled
    if push:
        try:
            git_ops.push()
            console.print("[green]Pushed to remote[/green]")
        except Exception as e:
            console.print(f"[red]Push failed: {e}[/red]")
            sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
