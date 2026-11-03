from alembic import command
from alembic.config import Config


def upgrade_head() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
