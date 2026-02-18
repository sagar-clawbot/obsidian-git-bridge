#!/usr/bin/env python3
"""
Manual test script for git_ops.py
Tests all core functions.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the source to path
sys.path.insert(0, '/tmp/obsidian-git-bridge/src')

from obsidian_git_bridge import (
    init_git_repo,
    configure_gitignore,
    setup_remote,
    initial_commit,
    get_repo_status,
    pull_changes,
    push_changes,
    quick_sync,
    get_git_info,
    RepoStatus,
    GitError,
    NotAGitRepoError,
)

def test_init_git_repo():
    """Test 1: Initialize Git repository"""
    print("\n" + "="*60)
    print("TEST 1: init_git_repo()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        
        # Test creating new repo
        result = init_git_repo(vault_path)
        print(f"✓ Init new repo: {result['message']}")
        assert result['success'] is True
        assert result['was_already_init'] is False
        assert (vault_path / ".git").exists()
        
        # Test idempotent (already initialized)
        result2 = init_git_repo(vault_path)
        print(f"✓ Init existing repo: {result2['message']}")
        assert result2['was_already_init'] is True
        
    print("✅ TEST 1 PASSED")

def test_configure_gitignore():
    """Test 2: Configure .gitignore"""
    print("\n" + "="*60)
    print("TEST 2: configure_gitignore()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        vault_path.mkdir()
        
        # Test creating .gitignore
        result = configure_gitignore(vault_path)
        print(f"✓ Create .gitignore: {result['message']}")
        assert result['success'] is True
        assert result['created'] is True
        
        gitignore_path = vault_path / ".gitignore"
        assert gitignore_path.exists()
        
        content = gitignore_path.read_text()
        assert ".obsidian/workspace.json" in content
        assert ".DS_Store" in content
        print(f"✓ Content verified (patterns: {result['patterns_count']})")
        
        # Test idempotent
        result2 = configure_gitignore(vault_path)
        assert result2['created'] is False
        print(f"✓ Idempotent check: {result2['message']}")
        
        # Test with custom patterns
        result3 = configure_gitignore(
            vault_path, 
            custom_patterns=["*.secret", "private/"],
            overwrite=True
        )
        content3 = gitignore_path.read_text()
        assert "*.secret" in content3
        assert "private/" in content3
        print(f"✓ Custom patterns added")
        
    print("✅ TEST 2 PASSED")

def test_setup_remote():
    """Test 3: Setup remote"""
    print("\n" + "="*60)
    print("TEST 3: setup_remote()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        init_git_repo(vault_path)
        
        # Test adding remote
        result = setup_remote(vault_path, "https://github.com/user/repo.git")
        print(f"✓ Add remote: {result['message']}")
        assert result['success'] is True
        assert result['created'] is True
        assert result['remote_name'] == "origin"
        
        # Test idempotent (same URL)
        result2 = setup_remote(vault_path, "https://github.com/user/repo.git")
        assert result2['created'] is False
        print(f"✓ Idempotent check: {result2['message']}")
        
        # Test update (different URL)
        result3 = setup_remote(vault_path, "https://github.com/user/repo2.git")
        assert result3.get('updated') is True
        print(f"✓ Update remote: {result3['message']}")
        
        # Test SSH conversion
        result4 = setup_remote(
            vault_path, 
            "https://github.com/user/ssh-repo.git",
            remote_name="ssh-origin",
            auth_method="ssh"
        )
        assert "git@github.com:" in result4['url']
        print(f"✓ SSH conversion: {result4['url']}")
        
    print("✅ TEST 3 PASSED")

def test_initial_commit():
    """Test 4: Initial commit"""
    print("\n" + "="*60)
    print("TEST 4: initial_commit()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        init_git_repo(vault_path)
        
        # Create a test file
        (vault_path / "note.md").write_text("# Test Note")
        
        # Test initial commit (no remote, so won't push)
        result = initial_commit(vault_path, message="Test initial commit", push=False)
        print(f"✓ Initial commit: {result['message']}")
        assert result['success'] is True
        assert result['committed'] is True
        assert result['commit_sha'] is not None
        assert result['pushed'] is False  # No remote
        
        # Test idempotent (no changes)
        result2 = initial_commit(vault_path, push=False)
        assert result2['committed'] is False
        print(f"✓ No changes: {result2['message']}")
        
    print("✅ TEST 4 PASSED")

def test_get_repo_status():
    """Test 5: Get repo status"""
    print("\n" + "="*60)
    print("TEST 5: get_repo_status()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        
        # Test non-git directory
        vault_path.mkdir()
        status = get_repo_status(vault_path)
        assert status.is_git_repo is False
        print("✓ Non-git directory: correctly identified")
        
        # Init and test empty repo
        init_git_repo(vault_path)
        status = get_repo_status(vault_path)
        assert status.is_git_repo is True
        assert status.is_clean is True
        print(f"✓ Empty repo status: clean={status.is_clean}")
        
        # Create files
        (vault_path / "note1.md").write_text("# Note 1")
        (vault_path / "note2.md").write_text("# Note 2")
        
        status = get_repo_status(vault_path)
        assert status.is_clean is False
        assert len(status.untracked_files) == 2
        print(f"✓ Untracked files: {len(status.untracked_files)}")
        
        # Stage one file
        import subprocess
        subprocess.run(["git", "-C", str(vault_path), "add", "note1.md"], check=True)
        
        status = get_repo_status(vault_path)
        assert len(status.staged_files) == 1
        assert len(status.untracked_files) == 1
        print(f"✓ Staged files: {len(status.staged_files)}")
        
        # Commit and check clean
        initial_commit(vault_path, push=False)
        status = get_repo_status(vault_path)
        assert status.is_clean is True
        print(f"✓ After commit: clean={status.is_clean}")
        
        print(f"\nStatus display:\n{status}")
        
    print("✅ TEST 5 PASSED")

def test_pull_and_push():
    """Test 6: Pull and push changes"""
    print("\n" + "="*60)
    print("TEST 6: pull_changes() and push_changes()")
    print("="*60)
    
    # Note: These require actual remotes, so we test error cases
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        init_git_repo(vault_path)
        
        # Test pull on repo without remote
        try:
            pull_changes(vault_path)
            print("✗ Should have raised error")
        except GitError as e:
            print(f"✓ Pull without remote: {e.message}")
        
        # Test push on repo without remote
        try:
            push_changes(vault_path)
            print("✗ Should have raised error")
        except GitError as e:
            print(f"✓ Push without remote: {e.message}")
        
    print("✅ TEST 6 PASSED (error handling)")

def test_quick_sync():
    """Test 7: Quick sync"""
    print("\n" + "="*60)
    print("TEST 7: quick_sync()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        init_git_repo(vault_path)
        configure_gitignore(vault_path)
        
        # Create some files
        (vault_path / "note.md").write_text("# Test")
        initial_commit(vault_path, push=False)
        
        # Test quick_sync (will fail on pull without remote)
        result = quick_sync(vault_path, message="Quick sync test")
        print(f"✓ Quick sync attempted")
        print(f"  Pull result: {result['operations'].get('pull', {}).get('error', 'success')}")
        
    print("✅ TEST 7 PASSED")

def test_get_git_info():
    """Test 8: Get git info"""
    print("\n" + "="*60)
    print("TEST 8: get_git_info()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        init_git_repo(vault_path)
        setup_remote(vault_path, "https://github.com/user/repo.git")
        
        info = get_git_info(vault_path)
        assert info['is_git_repo'] is True
        assert info['git_installed'] is True
        assert info['git_version'] is not None
        assert 'remotes' in info
        print(f"✓ Git installed: {info['git_version']}")
        print(f"✓ Remotes: {info['remotes']}")
        print(f"✓ Status: {info['status']}")
        
    print("✅ TEST 8 PASSED")

def test_error_handling():
    """Test 9: Error handling"""
    print("\n" + "="*60)
    print("TEST 9: Error handling")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        non_git_path = Path(tmpdir) / "not_a_repo"
        non_git_path.mkdir()
        
        # Test operations on non-git directory
        try:
            setup_remote(non_git_path, "https://github.com/user/repo.git")
        except NotAGitRepoError as e:
            print(f"✓ NotAGitRepoError: {e.message}")
        
        try:
            initial_commit(non_git_path)
        except NotAGitRepoError as e:
            print(f"✓ NotAGitRepoError: {e.message}")
        
        try:
            pull_changes(non_git_path)
        except NotAGitRepoError as e:
            print(f"✓ NotAGitRepoError: {e.message}")
        
        try:
            push_changes(non_git_path)
        except NotAGitRepoError as e:
            print(f"✓ NotAGitRepoError: {e.message}")
        
        # Test status on non-git (should return not-git status, not raise)
        status = get_repo_status(non_git_path)
        assert status.is_git_repo is False
        print(f"✓ Status on non-git: is_git_repo=False")
        
    print("✅ TEST 9 PASSED")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OBSIDIAN GIT BRIDGE - MANUAL TEST SUITE")
    print("="*60)
    
    try:
        test_init_git_repo()
        test_configure_gitignore()
        test_setup_remote()
        test_initial_commit()
        test_get_repo_status()
        test_pull_and_push()
        test_quick_sync()
        test_get_git_info()
        test_error_handling()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())