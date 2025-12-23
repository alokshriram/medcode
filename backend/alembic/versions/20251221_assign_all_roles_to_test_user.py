"""Assign all roles to test user alokshriram@gmail.com

Revision ID: 20251221_test_roles
Revises: 20251221_queue_items
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251221_test_roles'
down_revision: Union[str, None] = '20251221_queue_items'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Assign all roles (coder, admin, supervisor) to the test user
    op.execute("""
        UPDATE users.users
        SET roles = ARRAY['coder', 'admin', 'supervisor']
        WHERE email = 'alokshriram@gmail.com'
    """)


def downgrade() -> None:
    # Reset to default empty roles
    op.execute("""
        UPDATE users.users
        SET roles = ARRAY[]::varchar[]
        WHERE email = 'alokshriram@gmail.com'
    """)
