"""
GlobalConfig — Безопасное хранение API ключей

Ключи хранятся в:
- Windows: C:\\Users\\<user>\\AppData\\Local\\GhostProtocol\\config.json
- Linux/Mac: ~/.ghost/config.json

НИКОГДА не попадает в Git!
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from .core import logger

# Поддерживаемые провайдеры
SUPPORTED_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": ["models/gemini-flash-latest", "models/gemini-2.0-flash-lite", "models/gemini-2.0-flash"],
        "default_model": "models/gemini-flash-latest",  # Лучшая совместимость с Free Tier
        "free_tier": True,
        "env_var": "GEMINI_API_KEY"
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
        "free_tier": False,
        "env_var": "OPENAI_API_KEY"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "models": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229"],
        "default_model": "claude-3-haiku-20240307",
        "free_tier": False,
        "env_var": "ANTHROPIC_API_KEY"
    },
    "ollama": {
        "name": "Ollama (Local)",
        "models": ["mistral", "llama3", "qwen2.5-coder"],
        "default_model": "mistral",
        "free_tier": True,
        "env_var": None  # No API key needed
    }
}

DEFAULT_GLOBAL_CONFIG = {
    "ai": {
        "provider": "gemini",
        "api_key": "",
        "model": "models/gemini-flash-latest",  # Лучшая совместимость с Free Tier
        "ollama_host": "http://localhost:11434"
    },
    "setup_complete": False
}


class GlobalConfig:
    """Глобальная конфигурация Ghost Protocol (хранится вне проектов)"""
    
    _instance: Optional['GlobalConfig'] = None
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_path = self.config_dir / "config.json"
        self._data = DEFAULT_GLOBAL_CONFIG.copy()
        self._load()
    
    def _get_config_dir(self) -> Path:
        """Возвращает путь к директории конфига (платформозависимо)"""
        if sys.platform == "win32":
            # Windows: C:\Users\<user>\AppData\Local\GhostProtocol
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            return Path(base) / "GhostProtocol"
        else:
            # Linux/Mac: ~/.ghost
            return Path.home() / ".ghost"
    
    def _load(self):
        """Загружает конфиг или создаёт дефолтный"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Мержим с дефолтами
                    self._data = {**DEFAULT_GLOBAL_CONFIG, **loaded}
                    if 'ai' in loaded:
                        self._data['ai'] = {**DEFAULT_GLOBAL_CONFIG['ai'], **loaded['ai']}
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load global config: {e}")
        
        # Проверяем переменные окружения (приоритет над файлом)
        self._load_from_env()
    
    def _load_from_env(self):
        """Загружает API ключи из переменных окружения"""
        provider = self._data['ai'].get('provider', 'gemini')
        if provider in SUPPORTED_PROVIDERS:
            env_var = SUPPORTED_PROVIDERS[provider].get('env_var')
            if env_var and os.environ.get(env_var):
                self._data['ai']['api_key'] = os.environ[env_var]
    
    def save(self):
        """Сохраняет конфиг"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)
        logger.info(f"Global config saved to {self.config_path}")
    
    def set_api_key(self, api_key: str, provider: str = "gemini"):
        """Устанавливает API ключ"""
        self._data['ai']['api_key'] = api_key
        self._data['ai']['provider'] = provider
        if provider in SUPPORTED_PROVIDERS:
            self._data['ai']['model'] = SUPPORTED_PROVIDERS[provider]['default_model']
        self._data['setup_complete'] = True
        self.save()
    
    def set_provider(self, provider: str, model: Optional[str] = None):
        """Устанавливает провайдера"""
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        
        self._data['ai']['provider'] = provider
        if model:
            self._data['ai']['model'] = model
        else:
            self._data['ai']['model'] = SUPPORTED_PROVIDERS[provider]['default_model']
        self.save()
    
    @property
    def api_key(self) -> str:
        return self._data['ai'].get('api_key', '')
    
    @property
    def provider(self) -> str:
        return self._data['ai'].get('provider', 'gemini')
    
    @property
    def model(self) -> str:
        return self._data['ai'].get('model', 'gemini-2.0-flash')
    
    @property
    def ollama_host(self) -> str:
        return self._data['ai'].get('ollama_host', 'http://localhost:11434')
    
    @property
    def setup_complete(self) -> bool:
        return self._data.get('setup_complete', False)
    
    @property
    def config_location(self) -> str:
        return str(self.config_path)
    
    @classmethod
    def get(cls) -> 'GlobalConfig':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Сбрасывает singleton (для тестов)"""
        cls._instance = None


def run_setup_wizard():
    """Интерактивный мастер настройки"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    
    console = Console()
    config = GlobalConfig.get()
    
    console.print(Panel.fit(
        "[bold cyan]Ghost Protocol Setup[/bold cyan]\n"
        "Configure your AI provider for code reviews",
        border_style="cyan"
    ))
    
    console.print("\n[bold]Choose your AI provider:[/bold]")
    console.print("  [1] Google Gemini (free tier available)")
    console.print("  [2] OpenAI GPT-4")
    console.print("  [3] Anthropic Claude")
    console.print("  [4] Local Ollama (no API key needed)")
    console.print("  [5] Skip AI features\n")
    
    choice = Prompt.ask("Enter choice", choices=["1", "2", "3", "4", "5"], default="1")
    
    providers = {
        "1": "gemini",
        "2": "openai", 
        "3": "anthropic",
        "4": "ollama",
        "5": None
    }
    
    provider = providers[choice]
    
    if provider is None:
        config._data['setup_complete'] = True
        config._data['ai']['api_key'] = ''
        config.save()
        console.print("\n[yellow]AI features disabled. You can enable them later with 'ghost --setup'[/yellow]")
        return
    
    if provider == "ollama":
        host = Prompt.ask("Ollama host", default="http://localhost:11434")
        config._data['ai']['ollama_host'] = host
        config._data['ai']['provider'] = "ollama"
        config._data['ai']['api_key'] = ''
        config._data['setup_complete'] = True
        config.save()
        console.print(f"\n[green][OK] Ollama configured at {host}[/green]")
        return
    
    # Для облачных провайдеров нужен API ключ
    provider_info = SUPPORTED_PROVIDERS[provider]
    console.print(f"\n[bold]{provider_info['name']}[/bold]")
    
    if provider == "gemini":
        console.print("[dim]Get your API key at: https://aistudio.google.com/apikey[/dim]")
    elif provider == "openai":
        console.print("[dim]Get your API key at: https://platform.openai.com/api-keys[/dim]")
    elif provider == "anthropic":
        console.print("[dim]Get your API key at: https://console.anthropic.com/[/dim]")
    
    api_key = Prompt.ask("\nEnter API key")
    
    if not api_key.strip():
        console.print("[red]API key cannot be empty![/red]")
        return
    
    config.set_api_key(api_key.strip(), provider)
    
    console.print(f"\n[green][OK] Configuration saved![/green]")
    console.print(f"[dim]Location: {config.config_location}[/dim]")
    console.print(f"[dim]Provider: {provider_info['name']}[/dim]")
    console.print(f"[dim]Model: {config.model}[/dim]")
    console.print("\n[bold]You can now run 'ghost' in any project![/bold]")

