import click

from .service import init_database, update_database, UpdateAlreadyRunningError


@click.command("init-db")
def init_db_command():
    """Initialize the database schema."""
    result = init_database()
    click.echo(f"Initialized the database. {result}")


@click.command("update-db")
def update_db_command():
    """Run the database update process."""
    try:
        result = update_database()
    except UpdateAlreadyRunningError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)
    click.echo(f"Updated the database. {result}")
