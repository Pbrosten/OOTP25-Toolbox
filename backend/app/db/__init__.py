from .connection import get_db, close_db
from .cli import init_db_command, update_db_command


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(update_db_command)
