"""Command-line helpers:

    flask --app run refresh             pull every data source once and rescore all sites
    flask --app run briefings           generate and send tomorrow's briefings now
    flask --app run create-supervisor   add a supervisor account (prompts for details)
"""
import click

from .extensions import db
from .models import User


def register_cli(app):
    @app.cli.command("refresh")
    def refresh():
        """Pull weather, NWS alerts, rivers, fires and wildlife once, then rescore."""
        from .services import ingest
        ingest.refresh_all()
        click.echo("Refresh complete.")

    @app.cli.command("briefings")
    def send_briefings():
        """Generate and send tomorrow's briefings for every active site."""
        from .services import briefings
        click.echo(f"Sent {briefings.send_now()} briefings.")

    @app.cli.command("create-supervisor")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_supervisor(username, email, password):
        """Create a supervisor account (use this in production instead of demo accounts)."""
        from .api.validation import user_problem
        problem = user_problem(username=username, email=email.lower(), password=password)
        if problem:
            raise click.ClickException(problem)
        if User.query.filter((User.username == username) | (User.email == email.lower())).first():
            raise click.ClickException("That username or email already exists.")
        user = User(username=username, email=email.lower(), role="supervisor")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Supervisor '{username}' created.")
