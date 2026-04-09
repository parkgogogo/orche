# Developing Agent Plugins

`orche` uses a plugin architecture for agent integrations. Each agent (e.g. `codex`, `claude`) is implemented as a plugin that tells `orche` how to launch, monitor, and communicate with that agent.

## Plugin Interface

An agent plugin must provide:

1. **Name** — The agent identifier used in CLI commands (`codex`, `claude`, etc.)
2. **Launch command builder** — How to construct the shell command that starts the agent
3. **Process matcher** — How to detect whether the agent process is still running
4. **Ready surface detector** — How to tell when the agent has finished startup and is ready for input
5. **Completion extractor** — How to extract a summary when the agent finishes a turn

## File Location

Agent plugins live in `src/agents/`. The `AgentRegistry` in `src/agents/registry.py` discovers and loads them automatically.

## Example: Minimal Agent Plugin

```python
from .common import BaseAgent

class MyAgent(BaseAgent):
    name = "myagent"
    runtime_label = "myagent"

    def build_launch_command(self, runtime, **kwargs):
        return ["myagent-cli", "--cwd", str(runtime.home)]

    def matches_process(self, proc):
        return proc.info.get("name") == "myagent-cli"

    def capture_has_ready_surface(self, pane_text):
        return "Ready>" in pane_text

    def extract_completion_summary(self, pane_text):
        return pane_text.strip().split("\n")[-1]
```

## Registration

Add your plugin class to `src/agents/__init__.py` so it is picked up by the registry:

```python
from .myagent import MyAgent
```

The registry will automatically discover it at runtime.
