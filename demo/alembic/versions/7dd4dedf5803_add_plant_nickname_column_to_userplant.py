"""add plant_nickname column to UserPlant

Revision ID: 7dd4dedf5803
Revises: 
Create Date: 2024-07-14 13:36:50.191957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dd4dedf5803'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE UserPlant ADD COLUMN plant_nickname TEXT")


def downgrade() -> None:
    pass
