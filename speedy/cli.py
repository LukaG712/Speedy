"""Speedy CLI ~ Command-line interface for the Evershade ecosystem."""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
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
@click.option("--include-secrets", is_flag=True, help="Include .env with secrets (default: redacted)")
def create(output: str, profile: str, include_secrets: bool):
    """Create a backup of all Evershade data volumes."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if output is None:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        output = str(backup_dir / f"evershade-{timestamp}.tar.gz")

    console.print(f"\n[bold]Creating backup: {output}[/bold]\n")

    # Check free disk space before starting backup
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        usage = shutil.disk_usage(str(output_path.parent))
        # Estimate required space: sum of all data directories + 50% overhead
        compose_file = _find_compose_file()
        project_dir = compose_file.parent
        estimated_size = 0
        for name in SERVICES.keys():
            data_dir = project_dir / name / "data"
            if data_dir.exists():
                for f in data_dir.rglob("*"):
                    if f.is_file():
                        estimated_size += f.stat().st_size
        estimated_size = int(estimated_size * 1.5)  # 50% overhead for compression temp space
        free_space = usage.free
        if estimated_size > free_space:
            console.print(f"[red]✗ Insufficient disk space for backup.[/red]")
            console.print(f"  Estimated needed: {estimated_size / (1024**3):.1f} GB")
            console.print(f"  Free space: {free_space / (1024**3):.1f} GB")
            raise SystemExit(1)
        console.print(f"  Disk space check passed ({free_space / (1024**3):.1f} GB free)")
    except (shutil.Error, OSError):
        # disk_usage not available on some systems; continue without check
        pass

    compose_file = _find_compose_file()
    project_dir = compose_file.parent

    # Use temporary directory for consistent SQLite snapshots
    tmp_dir = tempfile.mkdtemp(prefix="evershade-backup-")
    manifest = {
        "version": "1.0",
        "timestamp": timestamp,
        "profile": profile,
        "services": {},
        "checksums": {},
    }

    try:
        # Collect and snapshot SQLite databases
        db_files = []
        for name in SERVICES.keys():
            db_file = project_dir / name / "data" / f"{name}.db"
            if db_file.exists():
                # Use sqlite3 .backup for consistent snapshot
                snapshot_path = Path(tmp_dir) / f"{name}.db"
                try:
                    src_conn = sqlite3.connect(str(db_file))
                    dst_conn = sqlite3.connect(str(snapshot_path))
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                    src_conn.close()
                    db_files.append((db_file, snapshot_path))
                    console.print(f"  [green]✓[/green] Snapshot: {name}.db")
                except Exception as e:
                    console.print(f"  [yellow]⚠[/yellow] Failed to snapshot {name}.db: {e}")
                    # Fall back to direct copy
                    shutil.copy2(str(db_file), str(snapshot_path))
                    db_files.append((db_file, snapshot_path))

        # Collect data directories (excluding already-snapped DBs)
        data_dirs = []
        for name in SERVICES.keys():
            data_dir = project_dir / name / "data"
            if data_dir.exists():
                data_dirs.append(data_dir)

        # Config files
        config_files = [
            project_dir / "docker-compose.yml",
            project_dir / ".env",
            Path.home() / ".evershade" / "config.env",
        ]

        # Create tarball with consistent snapshots
        with tarfile.open(output, "w:gz") as tar:
            # Add SQLite snapshots instead of live files
            for orig, snapshot in db_files:
                tar.add(str(snapshot), arcname=f"{orig.parent.name}/{orig.name}")
                # Calculate checksum
                sha = hashlib.sha256()
                with open(snapshot, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha.update(chunk)
                manifest["checksums"][f"{orig.parent.name}/{orig.name}"] = sha.hexdigest()
                manifest["services"][orig.parent.name] = {"database": True}

            # Add data directories
            for d in data_dirs:
                tar.add(str(d), arcname=d.name)

            # Add config files (redact secrets if requested)
            for f in config_files:
                if f.exists():
                    if f.name == ".env" and not include_secrets:
                        # Create redacted version
                        redacted_path = Path(tmp_dir) / ".env"
                        redacted_lines = []
                        with open(f, "r") as env_file:
                            for line in env_file:
                                line = line.strip()
                                if "=" in line and not line.startswith("#"):
                                    key = line.split("=", 1)[0]
                                    if any(s in key.lower() for s in ["key", "secret", "password", "token"]):
                                        redacted_lines.append(f"{key}=<redacted>")
                                    else:
                                        redacted_lines.append(line)
                                else:
                                    redacted_lines.append(line)
                        redacted_path.write_text("\n".join(redacted_lines))
                        tar.add(str(redacted_path), arcname=".env")
                        console.print("  [yellow]⚠[/yellow] Secrets redacted from .env (use --include-secrets to include)")
                    else:
                        tar.add(str(f), arcname=f.name)

        # Add manifest
        manifest_path = Path(tmp_dir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        with tarfile.open(output, "a:gz") as tar:
            tar.add(str(manifest_path), arcname="manifest.json")

        console.print(f"[green]✓ Backup created: {output}[/green]")
        console.print(f"  Services: {len(manifest['services'])}")
        console.print(f"  Checksums: {len(manifest['checksums'])}")

    finally:
        # Clean up temporary directory
        shutil.rmtree(tmp_dir, ignore_errors=True)


@backup.command()
@click.argument("archive", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Validate archive without extracting")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def restore(archive: str, dry_run: bool, force: bool):
    """Restore from a backup archive."""
    console.print(f"\n[bold]Restoring from: {archive}[/bold]\n")

    compose_file = _find_compose_file()
    project_dir = compose_file.parent.resolve()

    # Validate archive integrity
    console.print("[bold]Validating archive...[/bold]")
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()

            # Check for path traversal attacks
            for member in members:
                # Resolve the member's path relative to project_dir
                member_path = (project_dir / member.name).resolve()
                if not str(member_path).startswith(str(project_dir)):
                    console.print(f"[red]✗ Security violation: {member.name} escapes project directory[/red]")
                    return

            # Check for manifest
            manifest_names = [m.name for m in members if m.name == "manifest.json"]
            if manifest_names:
                # Read and display manifest
                manifest_file = tar.extractfile("manifest.json")
                if manifest_file:
                    manifest = json.loads(manifest_file.read().decode())
                    console.print(f"  [green]✓[/green] Manifest version: {manifest.get('version', 'unknown')}")
                    console.print(f"  [green]✓[/green] Backup timestamp: {manifest.get('timestamp', 'unknown')}")
                    console.print(f"  [green]✓[/green] Profile: {manifest.get('profile', 'unknown')}")

                    # Verify checksums
                    checksums = manifest.get("checksums", {})
                    if checksums:
                        console.print("[bold]Verifying checksums...[/bold]")
                        for filename, expected_sha in checksums.items():
                            member = tar.getmember(filename)
                            file_obj = tar.extractfile(member)
                            if file_obj:
                                sha = hashlib.sha256(file_obj.read()).hexdigest()
                                if sha == expected_sha:
                                    console.print(f"  [green]✓[/green] {filename}")
                                else:
                                    console.print(f"  [red]✗[/red] {filename} checksum mismatch!")
                                    return
                            else:
                                console.print(f"  [yellow]⚠[/yellow] {filename} not found in archive")

            # List contents
            console.print("\n[bold]Archive contents:[/bold]")
            for member in members:
                console.print(f"  {member.name}")

            if dry_run:
                console.print("\n[green]✓ Validation complete (dry run, no changes made)[/green]")
                return

    except tarfile.TarError as e:
        console.print(f"[red]✗ Invalid archive: {e}[/red]")
        return

    # Confirm before restoring
    if not force:
        if not click.confirm("\nThis will overwrite existing data. Continue?"):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Create recovery backup before overwriting
    console.print("[bold]Creating recovery backup...[/bold]")
    recovery_dir = project_dir / "backups" / "recovery"
    recovery_dir.mkdir(parents=True, exist_ok=True)
    recovery_timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    recovery_path = recovery_dir / f"pre-restore-{recovery_timestamp}"
    recovery_path.mkdir(exist_ok=True)

    # Backup existing data directories
    for name in SERVICES.keys():
        data_dir = project_dir / name / "data"
        if data_dir.exists():
            recovery_data_dir = recovery_path / name / "data"
            recovery_data_dir.mkdir(parents=True, exist_ok=True)
            for item in data_dir.iterdir():
                if item.is_file():
                    shutil.copy2(str(item), str(recovery_data_dir / item.name))
            console.print(f"  [green]✓[/green] Recovery backup: {name}/data")

    # Extract archive safely
    console.print("\n[bold]Extracting...[/bold]")
    with tarfile.open(archive, "r:gz") as tar:
        for member in members:
            # Double-check path traversal
            member_path = (project_dir / member.name).resolve()
            if not str(member_path).startswith(str(project_dir)):
                console.print(f"[red]✗ Skipping unsafe path: {member.name}[/red]")
                continue

            # Extract member
            target_path = project_dir / member.name
            if member.isdir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                file_obj = tar.extractfile(member)
                if file_obj:
                    with open(target_path, "wb") as f:
                        shutil.copyfileobj(file_obj, f)

    console.print(f"\n[green]✓ Restore complete![/green]")
    console.print(f"[yellow]Recovery backup saved to: {recovery_path}[/yellow]")
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


@config.command()
def validate():
    """Validate the current Evershade configuration."""
    console.print("\n[bold]Validating Evershade Configuration[/bold]\n")
    issues = []
    warnings = []

    # Check .env file exists
    compose_file = None
    try:
        compose_file = _find_compose_file()
        console.print("[green]✓[/green] docker-compose.yml found")
    except FileNotFoundError:
        issues.append("docker-compose.yml not found")
        console.print("[red]✗[/red] docker-compose.yml not found")

    # Check .env file
    env_file = Path(".env")
    if not compose_file:
        project_dir = Path.cwd()
    else:
        project_dir = compose_file.parent

    env_file = project_dir / ".env"
    if env_file.exists():
        console.print(f"[green]✓[/green] .env file found: {env_file}")
        env_vars = {}
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    else:
        warnings.append(".env file not found (may use environment variables instead)")
        console.print("[yellow]⚠[/yellow] .env file not found")
        env_vars = {}

    # Also check environment variables
    env_vars.update({k: v for k, v in os.environ.items() if k.startswith("EVERSHADE_") or k.endswith("_API_KEY")})

    # Check required variables
    required_vars = {
        "HUB_API_KEY": "Greenie API key",
        "ENCRYPTION_KEY": "Encryption key for secrets",
    }
    console.print("\n[bold]Required Variables:[/bold]")
    for var, description in required_vars.items():
        value = env_vars.get(var)
        if value and value != f"{var.lower()}-change-me" and "change-me" not in value.lower():
            console.print(f"  [green]✓[/green] {var} ({description})")
        else:
            issues.append(f"Missing or insecure: {var}")
            console.print(f"  [red]✗[/red] {var} ({description}) — missing or using default")

    # Check service API keys
    optional_vars = {
        "SLINKER_API_KEY": "Slinker API key",
        "TRAPPER_API_KEY": "Trapper API key",
        "GOBBER_API_KEY": "Gobber API key",
        "SNEAKER_API_KEY": "Sneaker API key",
        "HIDER_API_KEY": "Hider API key",
        "POLTERGEIST_API_KEY": "Poltergeist API key",
        "SHREWD_API_KEY": "Shrewd API key",
    }
    console.print("\n[bold]Service API Keys:[/bold]")
    for var, description in optional_vars.items():
        value = env_vars.get(var)
        if value and "change-me" not in value.lower():
            console.print(f"  [green]✓[/green] {var} ({description})")
        else:
            warnings.append(f"Missing or default: {var}")
            console.print(f"  [yellow]⚠[/yellow] {var} ({description}) — missing or using default")

    # Check Docker availability
    console.print("\n[bold]Docker:[/bold]")
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Docker available")
        else:
            issues.append("Docker not available")
            console.print("  [red]✗[/red] Docker not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("Docker not installed")
        console.print("  [red]✗[/red] Docker not installed")

    # Check Docker Compose
    try:
        result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Docker Compose available")
        else:
            issues.append("Docker Compose not available")
            console.print("  [red]✗[/red] Docker Compose not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("Docker Compose not installed")
        console.print("  [red]✗[/red] Docker Compose not installed")

    # Validate docker-compose.yml syntax
    if compose_file:
        console.print("\n[bold]Docker Compose Config:[/bold]")
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "config", "--quiet"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                console.print("  [green]✓[/green] docker-compose.yml is valid")
            else:
                issues.append("docker-compose.yml has errors")
                console.print("  [red]✗[/red] docker-compose.yml has errors")
                if result.stderr:
                    console.print(f"    {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            warnings.append("docker-compose config validation timed out")
            console.print("  [yellow]⚠[/yellow] Validation timed out")

    # Check service directories
    console.print("\n[bold]Service Directories:[/bold]")
    service_dirs = ["Greenie", "Slinker", "Trapper", "Gobber", "Sneaker", "Hider", "Poltergeist", "Shrewd", "Speedy", "Slammer"]
    for name in service_dirs:
        service_path = project_dir / name
        if service_path.exists() and service_path.is_dir():
            console.print(f"  [green]✓[/green] {name}")
        else:
            warnings.append(f"{name} directory not found")
            console.print(f"  [yellow]⚠[/yellow] {name} — not found (run 'evershade install' to bootstrap)")

    # Summary
    console.print(f"\n[bold]Summary:[/bold] {len(issues)} issues, {len(warnings)} warnings")
    if issues:
        console.print("\n[bold red]Issues (must fix):[/bold red]")
        for issue in issues:
            console.print(f"  - {issue}")
    if warnings:
        console.print("\n[bold yellow]Warnings (should fix):[/bold yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")
    if not issues and not warnings:
        console.print("\n[green]✓ Configuration is valid![/green]")
    elif not issues:
        console.print("\n[yellow]Configuration has warnings but is usable.[/yellow]")
    else:
        console.print("\n[red]Configuration has issues that must be resolved.[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
