"""Test configuration management."""

import json
from basic_memory.config import BasicMemoryConfig, ConfigManager


class TestBasicMemoryConfig:
    """Test BasicMemoryConfig behavior with BASIC_MEMORY_HOME environment variable."""

    def test_default_behavior_without_basic_memory_home(self, config_home, monkeypatch):
        """Test that config uses default path when BASIC_MEMORY_HOME is not set."""
        # Ensure BASIC_MEMORY_HOME is not set
        monkeypatch.delenv("BASIC_MEMORY_HOME", raising=False)

        config = BasicMemoryConfig()

        # Should use the default path (home/basic-memory)
        expected_path = str(config_home / "basic-memory")
        assert config.projects["main"] == expected_path

    def test_respects_basic_memory_home_environment_variable(self, config_home, monkeypatch):
        """Test that config respects BASIC_MEMORY_HOME environment variable."""
        custom_path = str(config_home / "app" / "data")
        monkeypatch.setenv("BASIC_MEMORY_HOME", custom_path)

        config = BasicMemoryConfig()

        # Should use the custom path from environment variable
        assert config.projects["main"] == custom_path

    def test_model_post_init_respects_basic_memory_home(self, config_home, monkeypatch):
        """Test that model_post_init creates main project with BASIC_MEMORY_HOME when missing."""
        custom_path = str(config_home / "custom" / "memory" / "path")
        monkeypatch.setenv("BASIC_MEMORY_HOME", custom_path)

        # Create config without main project
        other_path = str(config_home / "some" / "path")
        config = BasicMemoryConfig(projects={"other": other_path})

        # model_post_init should have added main project with BASIC_MEMORY_HOME
        assert "main" in config.projects
        assert config.projects["main"] == custom_path

    def test_model_post_init_fallback_without_basic_memory_home(self, config_home, monkeypatch):
        """Test that model_post_init falls back to default when BASIC_MEMORY_HOME is not set."""
        # Ensure BASIC_MEMORY_HOME is not set
        monkeypatch.delenv("BASIC_MEMORY_HOME", raising=False)

        # Create config without main project
        other_path = str(config_home / "some" / "path")
        config = BasicMemoryConfig(projects={"other": other_path})

        # model_post_init should have added main project with default path
        expected_path = str(config_home / "basic-memory")
        assert "main" in config.projects
        assert config.projects["main"] == expected_path

    def test_basic_memory_home_with_relative_path(self, config_home, monkeypatch):
        """Test that BASIC_MEMORY_HOME works with relative paths."""
        relative_path = "relative/memory/path"
        monkeypatch.setenv("BASIC_MEMORY_HOME", relative_path)

        config = BasicMemoryConfig()

        # Should use the exact value from environment variable
        assert config.projects["main"] == relative_path

    def test_basic_memory_home_overrides_existing_main_project(self, config_home, monkeypatch):
        """Test that BASIC_MEMORY_HOME is not used when a map is passed in the constructor."""
        custom_path = str(config_home / "override" / "memory" / "path")
        monkeypatch.setenv("BASIC_MEMORY_HOME", custom_path)

        # Try to create config with a different main project path
        original_path = str(config_home / "original" / "path")
        config = BasicMemoryConfig(projects={"main": original_path})

        # The default_factory should override with BASIC_MEMORY_HOME value
        # Note: This tests the current behavior where default_factory takes precedence
        assert config.projects["main"] == original_path


class TestConfigManager:
    """Test ConfigManager behavior with BASIC_MEMORY_HOME environment variable."""

    def test_load_config_respects_basic_memory_home_with_existing_file(self, config_home, monkeypatch):
        """Test that ConfigManager.load_config respects BASIC_MEMORY_HOME even when config file exists."""
        # Set up a custom path via environment variable
        custom_path = str(config_home / "custom" / "env" / "path")
        monkeypatch.setenv("BASIC_MEMORY_HOME", custom_path)

        # Create a config manager with a temporary config directory
        config_dir = config_home / ".basic-memory"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        
        # Create a config file with a different main project path
        file_config = {
            "projects": {
                "main": str(config_home / "file" / "path")
            },
            "default_project": "main"
        }
        config_file.write_text(json.dumps(file_config))

        # Mock the ConfigManager to use our temporary config directory
        monkeypatch.setattr("basic_memory.config.ConfigManager.config_dir", config_dir)
        monkeypatch.setattr("basic_memory.config.ConfigManager.config_file", config_file)

        # Create ConfigManager and load config
        config_manager = ConfigManager()
        config_manager.config_dir = config_dir
        config_manager.config_file = config_file
        
        loaded_config = config_manager.load_config()

        # The environment variable should override the file-based configuration
        assert loaded_config.projects["main"] == custom_path

    def test_load_config_without_basic_memory_home_uses_file_config(self, config_home, monkeypatch):
        """Test that ConfigManager.load_config uses file config when BASIC_MEMORY_HOME is not set."""
        # Ensure BASIC_MEMORY_HOME is not set
        monkeypatch.delenv("BASIC_MEMORY_HOME", raising=False)

        # Create a config manager with a temporary config directory
        config_dir = config_home / ".basic-memory"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        
        # Create a config file with a specific main project path
        file_path = str(config_home / "file" / "path")
        file_config = {
            "projects": {
                "main": file_path
            },
            "default_project": "main"
        }
        config_file.write_text(json.dumps(file_config))

        # Create ConfigManager and load config
        config_manager = ConfigManager()
        config_manager.config_dir = config_dir
        config_manager.config_file = config_file
        
        loaded_config = config_manager.load_config()

        # Should use the file-based configuration
        assert loaded_config.projects["main"] == file_path
