"""Tests for Obsidian config module."""

import pytest
from pathlib import Path

from obsidian_git_bridge.wrappers import ObsidianConfig


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "test-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    return vault


class TestObsidianConfig:
    """Test ObsidianConfig class."""
    
    def test_is_valid_vault_true(self, temp_vault):
        """Test valid vault detection."""
        config = ObsidianConfig()
        assert config.is_valid_vault(temp_vault)
    
    def test_is_valid_vault_false(self, tmp_path):
        """Test invalid vault detection."""
        config = ObsidianConfig()
        assert not config.is_valid_vault(tmp_path / "not-a-vault")
    
    def test_create_gitignore(self, temp_vault):
        """Test .gitignore creation."""
        config = ObsidianConfig()
        path = config.create_gitignore(temp_vault)
        
        assert path.exists()
        content = path.read_text()
        assert ".obsidian/workspace.json" in content
        assert ".DS_Store" in content
    
    def test_configure_git_plugin(self, temp_vault):
        """Test Git plugin configuration."""
        config = ObsidianConfig()
        path = config.configure_git_plugin(temp_vault)
        
        assert path.exists()
        content = path.read_text()
        assert "commitMessage" in content
