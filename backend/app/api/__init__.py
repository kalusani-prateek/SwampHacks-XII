"""REST API blueprints, all served under /api (contract: docs/API.md)."""


def register_blueprints(app):
    from . import alerts, auth, briefings, chat, meta, notifications, reports, settings, sites, spa, stats, users

    for module in (auth, users, sites, alerts, reports, briefings, settings, stats, notifications, chat, meta):
        app.register_blueprint(module.bp, url_prefix="/api")
    app.register_blueprint(spa.bp)  # the built React app, for every non-API path
