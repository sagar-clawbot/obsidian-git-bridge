"""Tests for Obsidian config module."""

import pytest
from pathlib import Path

from obsidian_git_bridge.wrappers import ObsidianConfig


class TestObsidianConfig:
    """Test ObsidianConfig class."""
    
    def test_detect_vault_path_returns_none_when_no_vault(self, tmp_path, monkeypatch):
        """Test vault detection returns None when no vault found."""
        # Mock home directory to temp path
        monkeypatch.setenv("HOME", str(tmp_path))
        
        config = ObsidianConfig()
        result = config.detect_vault_path()
        assert result is None
    
    def test_detect_vault_path_finds_vault(self, tmp_path, monkeypatch):
        """Test vault detection finds vault with .obsidian folder."""
        # Create vault structure
        vault_path = tmp_path / "Documents" / "Obsidian"
        vault_path.mkdir(parents=True)
        (vault_path / ".obsidian").mkdir()
        
        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        
        config = ObsidianConfig()
        # Override common paths to use temp
        config.COMMON_VAULT_PATHS = ["~/Documents/Obsidian"]
        result = config.detect_vault_path()
        
        assert result is not None
        assert result.name == "Obsidian"
    
    def test_validate_vault_true(self, tmp_path):
        """Test valid vault detection."""
        vault = tmp_path / "test-vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        
        config = ObsidianConfig()
        assert config.validate_vault(vault) is True
        assert config.is_valid_vault(vault) is True  # Test alias
    
    def test_validate_vault_false(self, tmp_path):
        """Test invalid vault detection."""
        not_vault = tmp_path / "not-a-vault"
        not_vault.mkdir()
        
        config = ObsidianConfig()
        # Should raise exception for invalid vault
        with pytest.raises(Exception):
            config.validate_vault(not_vault)
    
    def test_get_vault_name(self, tmp_path):
        """Test getting vault name."""
        vault = tmp_path / "My Vault"
        vault.mkdir()
        
        config = ObsidianConfig()
        name = config.get_vault_name(vault)
        assert name == "My Vault"
