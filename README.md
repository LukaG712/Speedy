# Speedy

> *"Step into the dark! Five new spooky mansions!"*
> ~ **The Dark Moon Song**, on the adventure ahead

**Speedy** is the command-line interface for the Evershade ecosystem. It provides an `evershade` command for managing services, agents, tasks, and pipelines from the terminal.

**Luigi's Mansion origin:** *Speedy Spirit* ~ fast ghosts from Luigi's Mansion that zoom around at high speed, perfect for a CLI that executes commands quickly.

## Features

- **Service management** ~ Start, stop, and check service status
- **Agent commands** ~ Create, list, and manage AI agents
- **Task execution** ~ Submit and monitor tasks
- **Configuration** ~ Manage API keys and settings

## Installation

```bash
pip install -e .
# Or globally
pip install .
```

## Usage

```bash
# Check service status
evershade status

# List agents
evershade agents list

# Submit a task
evershade task submit --service slinker --prompt "Fix the bug"

# Configure API key
evershade config set api-key your-key-here
```

## License

MIT
