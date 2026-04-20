"""
Configuration loader for the Crypto Trading Bot.
Loads settings from YAML and supports environment variable overrides.
"""

import os
import yaml
from pathlib import Path


_CONFIG_CACHE = None


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML config file. Defaults to config/settings.yaml.
    
    Returns:
        Dictionary of configuration values.
    """
    global _CONFIG_CACHE

    if _CONFIG_CACHE is not None and config_path is None:
        return _CONFIG_CACHE

    if config_path is None:
        config_path = Path(__file__).parent / "settings.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Environment variable overrides
    env_overrides = {
        "CRYPTO_EXCHANGE": "exchange",
        "CRYPTO_PAIR": "trading_pair",
        "CRYPTO_TIMEFRAME": "timeframe",
        "CRYPTO_CAPITAL": "initial_capital",
        "CRYPTO_STRATEGY": "strategy",
        "CRYPTO_FEE_RATE": "fee_rate",
    }

    for env_var, config_key in env_overrides.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Auto-cast numeric values
            try:
                value = float(value)
            except ValueError:
                pass
            config[config_key] = value

    if config_path is None:
        _CONFIG_CACHE = config

    return config


def get_strategy_params(config: dict, strategy_name: str) -> dict:
    """
    Get parameters for a specific strategy from the config.
    
    Args:
        config: Full config dictionary.
        strategy_name: Name of the strategy.
    
    Returns:
        Dictionary of strategy-specific parameters.
    """
    return config.get("strategies", {}).get(strategy_name, {})
