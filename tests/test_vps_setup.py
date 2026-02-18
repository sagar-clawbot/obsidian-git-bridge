"""Tests for VPS setup generator."""

import pytest
from pathlib import Path

from obsidian_git_bridge.vps_setup import VPSSetupGenerator


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault directory."""
    vault = tmp_path / "test-vault"
    vault.mkdir()
    return vault


@pytest.fixture
def output_dir(tmp_path):
    """Create output directory."""
    return tmp_path / "output"


class TestVPSSetupGenerator:
    """Test VPSSetupGenerator class."""
    
    def test_generate_cron_script(self, temp_vault, output_dir):
        """Test cron script generation."""
        vps = VPSSetupGenerator(temp_vault, output_dir)
        path = vps.generate_cron_script()
        
        assert path.exists()
        assert path.stat().st_mode & 0o111  # Executable
        content = path.read_text()
        assert "#!/bin/bash" in content
        assert str(temp_vault) in content
    
    def test_generate_setup_instructions(self, temp_vault, output_dir):
        """Test setup instructions generation."""
        vps = VPSSetupGenerator(temp_vault, output_dir)
        path = vps.generate_setup_instructions()
        
        assert path.exists()
        content = path.read_text()
        assert "VPS Setup Instructions" in content
        assert temp_vault.name in content
