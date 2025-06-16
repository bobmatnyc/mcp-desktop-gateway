"""
Tests for Config management components.
"""
import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from core.config import ConfigManager
from core.env_config import EnvironmentConfig


@pytest.mark.core
class TestConfigManager:
    """Test ConfigManager functionality."""
    
    @pytest.fixture
    def temp_config_file(self, temp_config_dir, sample_config):
        """Create a temporary config file."""
        config_path = temp_config_dir / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        return config_path
    
    @pytest.fixture
    def config_manager(self, temp_config_file):
        """Create ConfigManager with test config."""
        return ConfigManager(str(temp_config_file))
    
    def test_config_manager_initialization(self, config_manager):
        """Test ConfigManager initializes correctly."""
        assert config_manager is not None
        assert hasattr(config_manager, 'config_path')
        assert hasattr(config_manager, '_config')
    
    def test_load_config_yaml(self, temp_config_file):
        """Test loading YAML configuration."""
        manager = ConfigManager(str(temp_config_file))
        
        config = manager._config
        assert config['server']['name'] == 'mcp-gateway-test'
        assert config['server']['version'] == '1.0.0'
        assert len(config['connectors']) == 2
    
    def test_load_config_json(self, temp_config_dir, sample_config):
        """Test loading JSON configuration."""
        import json
        config_path = temp_config_dir / "test_config.json"
        with open(config_path, 'w') as f:
            json.dump(sample_config, f)
        
        manager = ConfigManager(str(config_path))
        config = manager._config
        assert config['server']['name'] == 'mcp-gateway-test'
    
    def test_load_config_file_not_found(self, temp_config_dir):
        """Test handling of missing config file."""
        nonexistent_path = temp_config_dir / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            ConfigManager(str(nonexistent_path))
    
    def test_load_config_invalid_yaml(self, temp_config_dir):
        """Test handling of invalid YAML."""
        invalid_config_path = temp_config_dir / "invalid.yaml"
        with open(invalid_config_path, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        with pytest.raises(yaml.YAMLError):
            ConfigManager(str(invalid_config_path))
    
    def test_get_server_config(self, config_manager):
        """Test getting server configuration."""
        server_config = config_manager.get_server_config()
        
        assert server_config.name == 'mcp-gateway-test'
        assert server_config.version == '1.0.0'
        assert server_config.log_level == 'INFO'
    
    def test_get_connector_configs(self, config_manager):
        """Test getting connector configurations."""
        connector_configs = config_manager.get_connector_configs()
        
        assert len(connector_configs) == 2
        
        enabled_connector = next(c for c in connector_configs if c.name == 'test_connector')
        assert enabled_connector.enabled is True
        assert enabled_connector.config == {'test_param': 'test_value'}
        
        disabled_connector = next(c for c in connector_configs if c.name == 'disabled_connector')
        assert disabled_connector.enabled is False
    
    def test_get_enabled_connectors(self, config_manager):
        """Test getting only enabled connectors."""
        enabled_connectors = config_manager.get_enabled_connectors()
        
        assert len(enabled_connectors) == 1
        assert enabled_connectors[0].name == 'test_connector'
        assert enabled_connectors[0].enabled is True
    
    def test_get_connector_config(self, config_manager):
        """Test getting specific connector configuration."""
        connector_config = config_manager.get_connector_config('test_connector')
        
        assert connector_config is not None
        assert connector_config.name == 'test_connector'
        assert connector_config.config == {'test_param': 'test_value'}
    
    def test_get_connector_config_not_found(self, config_manager):
        """Test getting non-existent connector configuration."""
        connector_config = config_manager.get_connector_config('nonexistent')
        assert connector_config is None
    
    def test_reload_config(self, config_manager, temp_config_dir, sample_config):
        """Test reloading configuration."""
        # Modify the config
        sample_config['server']['name'] = 'modified-gateway'
        
        # Write modified config
        with open(config_manager.config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Reload
        config_manager.reload()
        
        # Verify changes
        server_config = config_manager.get_server_config()
        assert server_config.name == 'modified-gateway'
    
    def test_default_config_path(self):
        """Test default config path resolution."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data='server:\n  name: test')):
                manager = ConfigManager()
                assert 'config.yaml' in manager.config_path
    
    def test_dev_config_override(self, temp_config_dir):
        """Test development config override."""
        # Create main config
        main_config = {
            'server': {'name': 'main', 'version': '1.0.0'},
            'connectors': [{'name': 'main_connector', 'enabled': True}]
        }
        main_path = temp_config_dir / "config.yaml"
        with open(main_path, 'w') as f:
            yaml.dump(main_config, f)
        
        # Create dev config
        dev_config = {
            'server': {'name': 'dev-override'},
            'connectors': [{'name': 'dev_connector', 'enabled': True}]
        }
        dev_path = temp_config_dir / "config.dev.yaml"
        with open(dev_path, 'w') as f:
            yaml.dump(dev_config, f)
        
        # Load with dev override
        manager = ConfigManager(str(main_path))
        
        # Should use dev values where available
        server_config = manager.get_server_config()
        assert server_config.name == 'dev-override'
        assert server_config.version == '1.0.0'  # Falls back to main config
    
    @patch.dict(os.environ, {'MCP_GATEWAY_SERVER_NAME': 'env-override'})
    def test_environment_variable_substitution(self, temp_config_dir):
        """Test environment variable substitution in config."""
        config_with_env = {
            'server': {
                'name': '${MCP_GATEWAY_SERVER_NAME}',
                'version': '1.0.0'
            },
            'connectors': []
        }
        
        config_path = temp_config_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_with_env, f)
        
        manager = ConfigManager(str(config_path))
        server_config = manager.get_server_config()
        
        assert server_config.name == 'env-override'
    
    def test_validate_config_valid(self, config_manager):
        """Test configuration validation with valid config."""
        is_valid, errors = config_manager.validate_config()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_config_missing_server(self, temp_config_dir):
        """Test configuration validation with missing server section."""
        invalid_config = {'connectors': []}
        config_path = temp_config_dir / "invalid.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        manager = ConfigManager(str(config_path))
        is_valid, errors = manager.validate_config()
        
        assert is_valid is False
        assert any('server' in error.lower() for error in errors)
    
    def test_validate_config_invalid_connector(self, temp_config_dir):
        """Test configuration validation with invalid connector."""
        invalid_config = {
            'server': {'name': 'test', 'version': '1.0.0'},
            'connectors': [
                {'name': 'valid_connector', 'enabled': True},
                {'enabled': True}  # Missing name
            ]
        }
        config_path = temp_config_dir / "invalid.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        manager = ConfigManager(str(config_path))
        is_valid, errors = manager.validate_config()
        
        assert is_valid is False
        assert any('name' in error.lower() for error in errors)


@pytest.mark.core
class TestEnvironmentConfig:
    """Test EnvConfig functionality."""
    
    def test_env_config_initialization(self):
        """Test EnvConfig initializes correctly."""
        env_config = EnvironmentConfig()
        assert env_config is not None
    
    @patch.dict(os.environ, {
        'MCP_GATEWAY_SERVER_NAME': 'test-server',
        'MCP_GATEWAY_SERVER_VERSION': '2.0.0',
        'MCP_GATEWAY_LOG_LEVEL': 'DEBUG'
    })
    def test_get_server_config_from_env(self):
        """Test getting server config from environment variables."""
        env_config = EnvironmentConfig()
        server_config = env_config.get_server_config()
        
        assert server_config['name'] == 'test-server'
        assert server_config['version'] == '2.0.0'
        assert server_config['log_level'] == 'DEBUG'
    
    def test_get_server_config_defaults(self):
        """Test getting server config with defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            env_config = EnvironmentConfig()
            server_config = env_config.get_server_config()
            
            assert server_config['name'] == 'mcp-gateway'
            assert server_config['version'] == '1.0.0'
            assert server_config['log_level'] == 'INFO'
    
    @patch.dict(os.environ, {
        'MCP_GATEWAY_CONNECTOR_TEST_ENABLED': 'true',
        'MCP_GATEWAY_CONNECTOR_TEST_PARAM': 'value'
    })
    def test_get_connector_config_from_env(self):
        """Test getting connector config from environment variables."""
        env_config = EnvironmentConfig()
        connector_config = env_config.get_connector_config('test')
        
        assert connector_config['enabled'] is True
        assert connector_config['config']['param'] == 'value'
    
    def test_get_connector_config_not_configured(self):
        """Test getting connector config when not configured in env."""
        with patch.dict(os.environ, {}, clear=True):
            env_config = EnvironmentConfig()
            connector_config = env_config.get_connector_config('test')
            
            assert connector_config is None
    
    @patch.dict(os.environ, {'MCP_GATEWAY_DEBUG': 'true'})
    def test_is_debug_mode_true(self):
        """Test debug mode detection when enabled."""
        env_config = EnvironmentConfig()
        assert env_config.is_debug_mode() is True
    
    @patch.dict(os.environ, {'MCP_GATEWAY_DEBUG': 'false'})
    def test_is_debug_mode_false(self):
        """Test debug mode detection when disabled."""
        env_config = EnvironmentConfig()
        assert env_config.is_debug_mode() is False
    
    def test_is_debug_mode_default(self):
        """Test debug mode detection with default value."""
        with patch.dict(os.environ, {}, clear=True):
            env_config = EnvironmentConfig()
            assert env_config.is_debug_mode() is False
    
    @patch.dict(os.environ, {'MCP_GATEWAY_CONFIG_PATH': '/custom/config/path.yaml'})
    def test_get_config_path_custom(self):
        """Test getting custom config path from environment."""
        env_config = EnvironmentConfig()
        config_path = env_config.get_config_path()
        assert config_path == '/custom/config/path.yaml'
    
    def test_get_config_path_default(self):
        """Test getting default config path."""
        with patch.dict(os.environ, {}, clear=True):
            env_config = EnvironmentConfig()
            config_path = env_config.get_config_path()
            assert 'config.yaml' in config_path
    
    def test_substitute_env_vars(self):
        """Test environment variable substitution."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            env_config = EnvironmentConfig()
            result = env_config.substitute_env_vars('${TEST_VAR}')
            assert result == 'test_value'
    
    def test_substitute_env_vars_not_found(self):
        """Test environment variable substitution with missing var."""
        env_config = EnvironmentConfig()
        result = env_config.substitute_env_vars('${MISSING_VAR}')
        assert result == '${MISSING_VAR}'  # Should remain unchanged
    
    def test_substitute_env_vars_in_dict(self):
        """Test environment variable substitution in dictionary."""
        with patch.dict(os.environ, {'DB_HOST': 'localhost', 'DB_PORT': '5432'}):
            env_config = EnvironmentConfig()
            config_dict = {
                'database': {
                    'host': '${DB_HOST}',
                    'port': '${DB_PORT}',
                    'name': 'mydb'
                }
            }
            
            result = env_config.substitute_env_vars_in_dict(config_dict)
            
            assert result['database']['host'] == 'localhost'
            assert result['database']['port'] == '5432'
            assert result['database']['name'] == 'mydb'  # Unchanged
    
    def test_parse_boolean_values(self):
        """Test parsing boolean values from environment."""
        env_config = EnvironmentConfig()
        
        assert env_config._parse_bool('true') is True
        assert env_config._parse_bool('True') is True
        assert env_config._parse_bool('TRUE') is True
        assert env_config._parse_bool('1') is True
        assert env_config._parse_bool('yes') is True
        
        assert env_config._parse_bool('false') is False
        assert env_config._parse_bool('False') is False
        assert env_config._parse_bool('FALSE') is False
        assert env_config._parse_bool('0') is False
        assert env_config._parse_bool('no') is False
        assert env_config._parse_bool('random') is False
    
    def test_get_all_env_vars(self):
        """Test getting all MCP Gateway environment variables."""
        with patch.dict(os.environ, {
            'MCP_GATEWAY_TEST1': 'value1',
            'MCP_GATEWAY_TEST2': 'value2',
            'OTHER_VAR': 'other_value'
        }):
            env_config = EnvironmentConfig()
            env_vars = env_config.get_all_gateway_env_vars()
            
            assert 'MCP_GATEWAY_TEST1' in env_vars
            assert 'MCP_GATEWAY_TEST2' in env_vars
            assert 'OTHER_VAR' not in env_vars
            assert env_vars['MCP_GATEWAY_TEST1'] == 'value1'