"""Scout CLI ~ Command-line interface for the Evershade ecosystem."""

import os
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

# Default service URLs
SERVICES = {
    "greenie": os.getenv("GREENIE_URL", "http://localhost:8080"),
    "slinker": os.getenv("SLINKER_URL", "http://localhost:8000"),
    "trapper": os.getenv("TRAPPER_URL", "http://localhost:3000"),
    "gobber": os.getenv("GOBBER_URL", "http://localhost:8085"),
    "creeper": os.getenv("CREEPER_URL", "http://localhost:8086"),
    "hider": os.getenv("HIDER_URL", "http://localhost:8087"),
    "polterpup": os.getenv("POLTERPUP_URL", "http://localhost:8088"),
    "chauncey": os.getenv("CHAUNCEY_URL", "http://localhost:8089"),
}


def get_api_key(service: str) -> str:
    """Get API key for a service from environment or config."""
    key_map = {
        "greenie": "HUB_API_KEY",
        "slinker": "SLINKER_API_KEY",
        "trapper": "TRAPPER_API_KEY",
        "gobber": "GOBBER_API_KEY",
        "creeper": "CREEPER_API_KEY",
        "hider": "HIDER_API_KEY",
        "polterpup": "POLTERPUP_API_KEY",
        "chauncey": "CHAUNCEY_API_KEY",
    }
    env_key = key_map.get(service, f"{service.upper()}_API_KEY")
    return os.getenv(env_key, f"{service}-dev-key-change-me")


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Evershade CLI ~ Manage your AI agent ecosystem."""
    pass


@main.command()
def status():
    """Check the status of all Evershade services."""
    console.print("\n[bold]Evershade Services[/bold]\n")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Service", style="green")
    table.add_column("URL")
    table.add_column("Status")

    for name, url in SERVICES.items():
        try:
            response = httpx.get(f"{url}/health", timeout=3)
            status = "[bold green]✓ Online[/bold green]" if response.status_code == 200 else "[bold yellow]⚠ Error[/bold yellow]"
        except Exception:
            status = "[bold red]✗ Offline[/bold red]"
        table.add_row(name.capitalize(), url, status)

    console.print(table)


@main.group()
def agents():
    """Manage AI agents."""
    pass


@agents.command()
def list_agents():
    """List all agents."""
    url = SERVICES["greenie"]
    api_key = get_api_key("greenie")
    try:
        response = httpx.get(f"{url}/api/agents", params={"x_key": api_key}, timeout=5)
        if response.status_code == 200:
            agents_data = response.json()
            if agents_data:
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Name", style="green")
                table.add_column("ID")
                table.add_column("Status")
                for agent in agents_data:
                    table.add_row(
                        agent.get("name", "Unknown"),
                        str(agent.get("id", ""))[:8],
                        agent.get("status", "unknown"),
                    )
                console.print(table)
            else:
                console.print("[yellow]No agents found.[/yellow]")
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Could not connect to Greenie: {e}[/red]")


@main.group()
def task():
    """Manage tasks."""
    pass


@task.command()
@click.option("--service", default="slinker", help="Target service")
@click.option("--prompt", required=True, help="Task prompt")
def submit(service: str, prompt: str):
    """Submit a new task."""
    url = SERVICES.get(service)
    if not url:
        console.print(f"[red]Unknown service: {service}[/red]")
        return
    api_key = get_api_key(service)
    try:
        response = httpx.post(
            f"{url}/api/tasks",
            json={"prompt": prompt},
            params={"x_key": api_key},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Task submitted![/green] ID: {data.get('id', 'unknown')[:8]}")
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Could not connect to {service}: {e}[/red]")


@main.group()
def config():
    """Manage configuration."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
def set_value(key: str, value: str):
    """Set a configuration value."""
    config_dir = Path.home() / ".evershade"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.env"
    # Read existing config
    lines = []
    if config_file.exists():
        lines = config_file.read_text().splitlines()
    # Update or add
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    config_file.write_text("\n".join(new_lines) + "\n")
    console.print(f"[green]Set {key}={value}[/green]")


@config.command()
def show():
    """Show current configuration."""
    config_file = Path.home() / ".evershade" / "config.env"
    if config_file.exists():
        console.print(f"[bold]Config file:[/bold] {config_file}\n")
        for line in config_file.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                k, _, v = line.partition("=")
                console.print(f"  {k} = [green]{v}[/green]")
    else:
        console.print("[yellow]No configuration file found.[/yellow]")


if __name__ == "__main__":
    main()
