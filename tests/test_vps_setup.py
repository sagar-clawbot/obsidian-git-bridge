"""Tests for VPS setup generator."""

import pytest
from pathlib import Path

from obsidian_git_bridge.wrappers import VPSSetupGenerator


class TestVPSSetupGenerator:
    """Test VPSSetupGenerator class."""
    
    def test_init(self, tmp_path):
        """Test initialization."""
        vault_path = tmp_path / "test-vault"
        vault_path.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        vps = VPSSetupGenerator(vault_path, output_dir)
        assert vps.vault_name == "test-vault"
        assert vps.vault_path == vault_path
        assert vps.output_dir == output_dir
    
    def test_generate_setup_script(self, tmp_path):
        """Test setup script generation."""
        vault_path = tmp_path / "test-vault"
        vault_path.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        vps = VPSSetupGenerator(vault_path, output_dir)
        script_path = vps.generate_cron_script()
        
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111  # Executable
        content = script_path.read_text()
        assert "#!/bin/bash" in content
        assert "test-vault" in content
    
    def test_generate_cron_job(self, tmp_path):
        """Test cron job generation."""
        vault_path = tmp_path / "test-vault"
        vault_path.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        vps = VPSSetupGenerator(vault_path, output_dir)
        cron = vps.generate_cron_job()
        
        assert "*/5 * * * *" in cron
        assert "test-vault" in cron
    
    def test_generate_instructions(self, tmp_path):
        """Test setup instructions generation."""
        vault_path = tmp_path / "test-vault"
        vault_path.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        vps = VPSSetupGenerator(vault_path, output_dir)
        instructions_path = vps.generate_setup_instructions()
        
        assert instructions_path.exists()
        content = instructions_path.read_text()
        assert "test-vault" in content
        assert "VPS Setup Instructions" in content
    
    def test_get_full_setup(self, tmp_path):
        """Test getting complete setup package."""
        vault_path = tmp_path / "test-vault"
        vault_path.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        vps = VPSSetupGenerator(vault_path, output_dir)
        setup = vps.get_full_setup()
        
        assert "script" in setup
        assert "cron" in setup
        assert "instructions" in setup
        assert setup["script"].exists()
        assert setup["instructions"].exists()
