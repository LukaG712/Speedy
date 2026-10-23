"""Basic tests for the Speedy CLI."""


def test_import_speedy():
    """Test that the speedy package can be imported."""
    import speedy

    assert hasattr(speedy, "__version__")


def test_cli_main_exists():
    """Test that the CLI main group exists."""
    from speedy.cli import main

    assert main is not None


def test_cli_has_commands():
    """Test that the CLI has expected commands."""
    from speedy.cli import main

    command_names = [cmd.name for cmd in main.commands.values()]
    expected_commands = ["status", "install", "start", "stop", "logs", "doctor"]
    for cmd in expected_commands:
        assert cmd in command_names, f"Missing command: {cmd}"
