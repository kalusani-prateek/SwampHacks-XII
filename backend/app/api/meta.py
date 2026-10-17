"""Public server info the frontend reads at startup (mode, demo tools, which features are on)."""
from flask import Blueprint, current_app

from ..models import User
from ..services.assistant import provider
from ..services.hazards import SCORING

bp = Blueprint("meta", __name__)


@bp.get("/meta")
def meta():
    cfg = current_app.config
    demo_accounts = None
    if cfg["SEED_DEMO_USERS"] and User.query.filter(User.username.in_(["supervisor", "crew"])).count() == 2:
        # Development only: lets the sign-in page offer one-click demo accounts.
        demo_accounts = {"usernames": ["supervisor", "crew"], "password": cfg["DEMO_PASSWORD"]}
    return {
        "api": "planit-control",
        "demoTools": cfg["DEMO_TOOLS"],
        "demoAccounts": demo_accounts,
        "assistant": provider(cfg) is not None,
        "lightningSource": cfg["LIGHTNING_SOURCE"],
        "scoring": SCORING,
    }
