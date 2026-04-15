from __future__ import annotations

import importlib
import os
from functools import lru_cache

from .base import AgentPlugin

BUILTIN_PLUGIN_MODULES: tuple[str, ...] = (
    "agents.codex",
    "agents.claude",
)


class AgentRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, AgentPlugin] = {}

    def register(self, plugin: AgentPlugin) -> None:
        name = plugin.name.strip().lower()
        if not name:
            raise ValueError("Agent plugin name must not be empty")
        self._plugins[name] = plugin

    def load_module(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        plugins = getattr(module, "PLUGINS", None)
        if not plugins:
            raise ValueError(
                f"Agent plugin module {module_name} did not expose PLUGINS"
            )
        for plugin in plugins:
            self.register(plugin)

    def get(self, name: str) -> AgentPlugin:
        key = name.strip().lower()
        plugin = self._plugins.get(key)
        if plugin is None:
            supported = ", ".join(sorted(self._plugins))
            raise ValueError(
                f"Unsupported agent: {name}. Supported agents: {supported}"
            )
        return plugin

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins))


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    modules = list(BUILTIN_PLUGIN_MODULES)
    extra = os.environ.get("ORCHE_AGENT_PLUGIN_MODULES", "").strip()
    if extra:
        modules.extend(name.strip() for name in extra.split(",") if name.strip())
    for module_name in modules:
        registry.load_module(module_name)
    return registry


def get_agent_plugin(name: str) -> AgentPlugin:
    return get_agent_registry().get(name)


def supported_agents() -> tuple[str, ...]:
    return get_agent_registry().names()
