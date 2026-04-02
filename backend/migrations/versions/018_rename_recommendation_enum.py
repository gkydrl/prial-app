"""rename recommendation_enum values: AL->IYI_FIYAT, BEKLE->FIYAT_DUSEBILIR, GUCLU_BEKLE->FIYAT_YUKSELISTE

Revision ID: 018
Revises: 017
Create Date: 2026-04-02
"""
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'AL' TO 'IYI_FIYAT';")
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'BEKLE' TO 'FIYAT_DUSEBILIR';")
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'GUCLU_BEKLE' TO 'FIYAT_YUKSELISTE';")


def downgrade() -> None:
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'IYI_FIYAT' TO 'AL';")
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'FIYAT_DUSEBILIR' TO 'BEKLE';")
    op.execute("ALTER TYPE recommendation_enum RENAME VALUE 'FIYAT_YUKSELISTE' TO 'GUCLU_BEKLE';")
