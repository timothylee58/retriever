import os

import pytest
from sqlalchemy import create_engine, text

from app.config import Settings
from app.db import apply_schema

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://apple@localhost:5432/retriever_test",
)


@pytest.fixture(scope="session")
def engine():
    admin = create_engine("postgresql+psycopg://apple@localhost:5432/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'retriever_test'")).first()
        if not exists:
            conn.execute(text("CREATE DATABASE retriever_test"))
    eng = create_engine(TEST_URL)
    apply_schema(eng)
    return eng


@pytest.fixture()
def db(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                TRUNCATE events, jobs, webhook_inbox, discount_offers, forecasts, refunds,
                         approvals, rescues, match_suggestions, allocations, payments,
                         payment_attempts, payment_requests, invoices, customers, merchants
                RESTART IDENTITY CASCADE
                """
            )
        )
    return engine


@pytest.fixture()
def settings():
    return Settings(database_url=TEST_URL, dry_run=True, xai_api_key="", hitpay_webhook_salt="salt", stripe_webhook_secret="whsec_test")
