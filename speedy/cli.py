"""Speedy CLI ~ Command-line interface for the Evershade ecosystem."""

import os
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

# Default service URLs — use env vars; defaults work in Docker internal network
SERVICES = {
    "greenie": os.getenv("GREENIE_URL", os.getenv("EVERSHADE_GREENIE_URL", "http://localhost:8080")),
    "slinker": os.getenv("SLINKER_URL", os.getenv("EVERSHADE_SLINKER_URL", "http://localhost:8000")),
    "trapper": os.getenv("TRAPPER_URL", os.getenv("EVERSHADE_TRAPPER_URL", "http://localhost:3000")),
    "gobber": os.getenv("GOBBER_URL", os.getenv("EVERSHADE_GOBBER_URL", "http://localhost:8085")),
    "sneaker": os.getenv("SNEAKER_URL", os.getenv("EVERSHADE_SNEAKER_URL", "http://localhost:8086")),
    "hider": os.getenv("HIDER_URL", os.getenv("EVERSHADE_HIDER_URL", "http://localhost:8087")),
    "poltergeist": os.getenv("POLTERGEIST_URL", os.getenv("EVERSHADE_POLTERGEIST_URL", "http://localhost:8088")),
    "shrewd": os.getenv("SHREWD_URL", os.getenv("EVERSHADE_SHREWD_URL", "http://localhost:8089")),
}

# Docker Compose profiles
PROFILES = ["minimal", "standard", "full", "ollama", "proxy", "dev"]


def get_api_key(service: str) -> str:
    """Get API key for a service from environment or config."""
    key_map = {
        "greenie": ("EVERSHADE_GREENIE_API_KEY", "HUB_API_KEY"),
        "slinker": ("EVERSHADE_SLINKER_API_KEY", "SLINKER_API_KEY"),
        "trapper": ("EVERSHADE_TRAPPER_API_KEY", "TRAPPER_API_KEY"),
        "gobber": ("EVERSHADE_GOBBER_API_KEY", "GOBBER_API_KEY"),
        "sneaker": ("EVERSHADE_SNEAKER_API_KEY", "SNEAKER_API_KEY"),
        "hider": ("EVERSHADE_HIDER_API_KEY", "HIDER_API_KEY"),
        "poltergeist": ("EVERSHADE_POLTERGEIST_API_KEY", "POLTERGEIST_API_KEY"),
        "shrewd": ("EVERSHADE_SHREWD_API_KEY", "SHREWD_API_KEY"),
    }
    keys = key_map.get(service)
    if keys:
        for env_key in keys:
            val = os.getenv(env_key)
            if val:
                return val
    return os.getenv(f"{service.upper()}_API_KEY", f"{service}-dev-key-change-me")


def _bearer_headers(service: str) -> dict[str, str]:
    """Get Bearer auth headers for a service."""
    api_key = get_api_key(service)
    return {"Authorization": f"Bearer {api_key}"}


def _find_compose_file() -> Path:
    """Find docker-compose.yml in current dir or parent dirs."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / "docker-compose.yml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("docker-compose.yml not found in current or parent directories")


def _docker_compose(*args: str, profile: str = "standard") -> int:
    """Run a docker compose command."""
    compose_file = _find_compose_file()
    cmd = ["docker", "compose", "-f", str(compose_file), "--profile", profile]
    cmd.extend(args)
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(result.stderr, style="red")
    return result.returncode


@click.group()
@click.version_option(version="1.1.0")
def main():
    """Evershade CLI ~ Manage your AI agent ecosystem."""
    pass


# ─── Status ─────────────────────────────────────────────────────

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


# ─── Install ────────────────────────────────────────────────────

@main.command()
@click.option("--profile", default="standard", type=click.Choice(PROFILES), help="Compose profile to install")
@click.option("--pull", is_flag=True, default=True, help="Pull latest images")
def install(profile: str, pull: bool):
    """Install Evershade services using Docker Compose."""
    console.print(f"\n[bold]Installing Evershade (profile: {profile})[/bold]\n")

    if pull:
        console.print("[bold]Pulling images...[/bold]")
        rc = _docker_compose("pull", profile=profile)
        if rc != 0:
            console.print("[red]Failed to pull images.[/red]")
            return

    console.print("[bold]Building services...[/bold]")
    rc = _docker_compose("up", "-d", "--build", profile=profile)
    if rc == 0:
        console.print("[green]✓ Installation complete![/green]")
    else:
        console.print("[red]Installation failed.[/red]")


# ─── Start ──────────────────────────────────────────────────────

@main.command()
@click.option("--profile", default="standard", type=click.Choice(PROFILES), help="Compose profile to start")
def start(profile: str):
    """Start Evershade services."""
    console.print(f"\n[bold]Starting Evershade (profile: {profile})[/bold]\n")
    rc = _docker_compose("up", "-d", profile=profile)
    if rc == 0:
        console.print("[green]✓ Services started![/green]")
    else:
        console.print("[red]Failed to start services.[/red]")


# ─── Stop ───────────────────────────────────────────────────────

@main.command()
@click.option("--profile", default="standard", type=click.Choice(PROFILES), help="Compose profile to stop")
@click.option("--remove-volumes", is_flag=True, help="Also remove volumes")
def stop(profile: str, remove_volumes: bool):
    """Stop Evershade services."""
    console.print(f"\n[bold]Stopping Evershade (profile: {profile})[/bold]\n")
    args = ["down"]
    if remove_volumes:
        args.append("-v")
    rc = _docker_compose(*args, profile=profile)
    if rc == 0:
        console.print("[green]✓ Services stopped![/green]")
    else:
        console.print("[red]Failed to stop services.[/red]")


# ─── Logs ───────────────────────────────────────────────────────

@main.command()
@click.option("--service", help="Show logs for a specific service")
@click.option("--profile", default="standard", type=click.Choice(PROFILES), help="Compose profile")
@click.option("--tail", default=100, help="Number of lines to show")
def logs(service: str, profile: str, tail: int):
    """View service logs."""
    args = ["logs", "--tail", str(tail), "-f"]
    if service:
        args.append(service)
    rc = _docker_compose(*args, profile=profile)
    return rc


# ─── Doctor ─────────────────────────────────────────────────────

@main.command()
def doctor():
    """Run diagnostics on the Evershade ecosystem."""
    console.print("\n[bold]Evershade Diagnostics[/bold]\n")
    issues = []

    # Check Docker
    console.print("[bold]Docker:[/bold]")
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {result.stdout.strip()}")
        else:
            issues.append("Docker not available")
            console.print("  [red]✗[/red] Docker not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("Docker not installed")
        console.print("  [red]✗[/red] Docker not installed")

    # Check Docker Compose
    console.print("[bold]Docker Compose:[/bold]")
    try:
        result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {result.stdout.strip()}")
        else:
            issues.append("Docker Compose not available")
            console.print("  [red]✗[/red] Docker Compose not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("Docker Compose not installed")
        console.print("  [red]✗[/red] Docker Compose not installed")

    # Check services
    console.print("\n[bold]Services:[/bold]")
    online = 0
    offline = 0
    for name, url in SERVICES.items():
        try:
            response = httpx.get(f"{url}/health", timeout=3)
            if response.status_code == 200:
                console.print(f"  [green]✓[/green] {name.capitalize()} is online")
                online += 1
            else:
                console.print(f"  [yellow]⚠[/yellow] {name.capitalize()} returned {response.status_code}")
                offline += 1
        except Exception:
            console.print(f"  [red]✗[/red] {name.capitalize()} is offline")
            offline += 1

    # Check config
    console.print("\n[bold]Configuration:[/bold]")
    config_file = Path.home() / ".evershade" / "config.env"
    if config_file.exists():
        console.print(f"  [green]✓[/green] Config file: {config_file}")
    else:
        console.print(f"  [yellow]⚠[/yellow] No config file at {config_file}")

    # Check env vars
    console.print("\n[bold]Environment:[/bold]")
    critical_vars = ["HUB_API_KEY", "ENCRYPTION_KEY"]
    for var in critical_vars:
        val = os.getenv(var)
        if val and val != f"{var.lower()}-change-me":
            console.print(f"  [green]✓[/green] {var} is set")
        else:
            console.print(f"  [yellow]⚠[/yellow] {var} is not set or using default")

    # Summary
    console.print(f"\n[bold]Summary:[/bold] {online} online, {offline} offline, {len(issues)} critical issues")
    if issues:
        console.print("\n[bold red]Issues:[/bold red]")
        for issue in issues:
            console.print(f"  - {issue}")


# ─── Backup ─────────────────────────────────────────────────────

@main.group()
def backup():
    """Backup and restore Evershade data."""
    pass


@backup.command()
@click.option("--output", default=None, help="Output file path (default: backups/evershade-<timestamp>.tar.gz)")
@click.option("--profile", default="standard", type=click.Choice(PROFILES), help="Compose profile")
def create(output: str, profile: str):
    """Create a backup of all Evershade data volumes."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if output is None:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        output = str(backup_dir / f"evershade-{timestamp}.tar.gz")

    console.print(f"\n[bold]Creating backup: {output}[/bold]\n")

    compose_file = _find_compose_file()
    project_dir = compose_file.parent

    # Collect volume data directories
    data_dirs = []
    for name in SERVICES.keys():
        data_dir = project_dir / name / "data"
        if data_dir.exists():
            data_dirs.append(data_dir)

    # Also check for SQLite DBs
    db_files = []
    for name in SERVICES.keys():
        db_file = project_dir / name / "data" / f"{name}.db"
        if db_file.exists():
            db_files.append(db_file)

    # Config files
    config_files = [
        project_dir / "docker-compose.yml",
        project_dir / ".env",
        Path.home() / ".evershade" / "config.env",
    ]

    with tarfile.open(output, "w:gz") as tar:
        for d in data_dirs:
            tar.add(str(d), arcname=d.name)
        for f in db_files:
            tar.add(str(f), arcname=f.name)
        for f in config_files:
            if f.exists():
                tar.add(str(f), arcname=f.name)

    console.print(f"[green]✓ Backup created: {output}[/green]")


@backup.command()
@click.argument("archive", type=click.Path(exists=True))
def restore(archive: str):
    """Restore from a backup archive."""
    console.print(f"\n[bold]Restoring from: {archive}[/bold]\n")

    if not click.confirm("This will overwrite existing data. Continue?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    compose_file = _find_compose_file()
    project_dir = compose_file.parent

    with tarfile.open(archive, "r:gz") as tar:
        # List contents first
        members = tar.getmembers()
        console.print("[bold]Archive contents:[/bold]")
        for member in members:
            console.print(f"  {member.name}")

        # Extract
        tar.extractall(path=str(project_dir))

    console.print("[green]✓ Restore complete![/green]")
    console.print("[yellow]Restart services to apply changes.[/yellow]")


# ─── Agents ─────────────────────────────────────────────────────

@main.group()
def agents():
    """Manage AI agents."""
    pass


@agents.command()
def list_agents():
    """List all agents."""
    url = SERVICES["greenie"]
    headers = _bearer_headers("greenie")
    try:
        response = httpx.get(f"{url}/api/agents", headers=headers, timeout=5)
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


# ─── Task ───────────────────────────────────────────────────────

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
    headers = _bearer_headers(service)
    try:
        response = httpx.post(
            f"{url}/api/tasks",
            json={"prompt": prompt},
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Task submitted![/green] ID: {data.get('id', 'unknown')[:8]}")
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Could not connect to {service}: {e}[/red]")


# ─── Config ─────────────────────────────────────────────────────

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
    lines = []
    if config_file.exists():
        lines = config_file.read_text().splitlines()
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
