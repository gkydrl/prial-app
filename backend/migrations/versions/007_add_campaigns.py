"""Add store_accounts, campaigns, campaign_products, code_pool, user_promo_assignments tables.

Revision ID: 007
"""
from alembic import op


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # store_accounts
    op.execute("""
        CREATE TABLE IF NOT EXISTS store_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            store store_name_enum NOT NULL,
            company_name VARCHAR(200),
            contact_email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    # campaigns
    op.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            store_account_id UUID NOT NULL REFERENCES store_accounts(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            discount_type discount_type_enum NOT NULL,
            discount_value NUMERIC(12,2) NOT NULL,
            target_price_min NUMERIC(12,2),
            target_price_max NUMERIC(12,2),
            is_unique_codes BOOLEAN NOT NULL DEFAULT true,
            fixed_code VARCHAR(50),
            starts_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_campaigns_store_account_id ON campaigns (store_account_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_campaigns_expires_at ON campaigns (expires_at);")

    # campaign_products (many-to-many)
    op.execute("""
        CREATE TABLE IF NOT EXISTS campaign_products (
            campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE CASCADE,
            PRIMARY KEY (campaign_id, product_id)
        );
    """)

    # code_pool
    op.execute("""
        CREATE TABLE IF NOT EXISTS code_pool (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            code VARCHAR(50) UNIQUE NOT NULL,
            assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
            assigned_at TIMESTAMPTZ,
            is_used BOOLEAN NOT NULL DEFAULT false
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_code_pool_campaign_id ON code_pool (campaign_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_code_pool_assigned_to ON code_pool (assigned_to);")

    # user_promo_assignments
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_promo_assignments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            code VARCHAR(50) NOT NULL,
            assigned_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_promo_user_product ON user_promo_assignments (user_id, product_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_promo_assignments")
    op.execute("DROP TABLE IF EXISTS code_pool")
    op.execute("DROP TABLE IF EXISTS campaign_products")
    op.execute("DROP TABLE IF EXISTS campaigns")
    op.execute("DROP TABLE IF EXISTS store_accounts")
