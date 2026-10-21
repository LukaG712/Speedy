# Scout

> *"Step into the dark! Five new spooky mansions!"*
> ~ **The Dark Moon Song**, on the adventure ahead

**Scout** is the command-line interface for the Evershade ecosystem. It provides an `evershade` command for managing services, agents, tasks, and pipelines from the terminal.

**Luigi's Mansion origin:** *Scout* ~ a forward-looking explorer, fitting for a CLI that navigates the Evershade ecosystem.

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
