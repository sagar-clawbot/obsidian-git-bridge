"""Tests for VPS setup generator."""

import pytest

from obsidian_git_bridge.wrappers import VPSSetupGenerator


class TestVPSSetupGenerator:
    """Test VPSSetupGenerator class."""
    
    def test_init(self):
        """Test initialization."""
        vps = VPSSetupGenerator("test-vault", "https://github.com/user/repo.git")
        assert vps.vault_name == "test-vault"
        assert vps.repo_url == "https://github.com/user/repo.git"
    
    def test_generate_setup_script(self):
        """Test setup script generation."""
        vps = VPSSetupGenerator("test-vault", "https://github.com/user/repo.git")
        script = vps.generate_setup_script()
        
        assert "#!/bin/bash" in script
        assert "test-vault" in script
        assert "github.com/user/repo.git" in script
    
    def test_generate_cron_job(self):
        """Test cron job generation."""
        vps = VPSSetupGenerator("test-vault", "https://github.com/user/repo.git")
        cron = vps.generate_cron_job()
        
        assert "*/5 * * * *" in cron
        assert "test-vault" in cron
    
    def test_generate_instructions(self):
        """Test setup instructions generation."""
        vps = VPSSetupGenerator("test-vault", "https://github.com/user/repo.git")
        instructions = vps.generate_instructions()
        
        assert "test-vault" in instructions
        assert "github.com/user/repo.git" in instructions
    
    def test_get_full_setup(self):
        """Test getting complete setup package."""
        vps = VPSSetupGenerator("test-vault", "https://github.com/user/repo.git")
        setup = vps.get_full_setup()
        
        assert "script" in setup
        assert "cron" in setup
        assert "instructions" in setup
        assert "test-vault" in setup["script"]
        assert "test-vault" in setup["cron"]
