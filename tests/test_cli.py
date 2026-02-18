"""Tests for CLI module."""

import pytest
from click.testing import CliRunner

from obsidian_git_bridge.cli import cli


@pytest.fixture
def runner():
    """Provide Click CLI runner."""
    return CliRunner()


def test_cli_version(runner):
    """Test version flag."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "obsidian-git-bridge" in result.output


def test_cli_help(runner):
    """Test main help output."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "setup-remote" in result.output
    assert "status" in result.output
    assert "doctor" in result.output
    assert "sync-now" in result.output


def test_init_help(runner):
    """Test init command help."""
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "Initialize" in result.output
