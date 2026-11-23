-- Retriever ledger. Money is amount_minor + currency. events is append-only.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE payment_method AS ENUM (
    'paynow','duitnow','fpx','tng','boost','grabpay','shopeepay','card','atome'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE invoice_status AS ENUM (
    'draft','issued','overdue','partially_paid','paid','written_off'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE request_status AS ENUM ('open','paid','expired','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE attempt_status AS ENUM ('pending','succeeded','failed','expired','abandoned');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE failure_class AS ENUM ('declined','expired','abandoned');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE match_status AS ENUM ('unmatched','suggested','matched','rejected','ignored');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE rescue_status AS ENUM ('opened','offered','recovered','churned','won_back','dismissed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE approval_kind AS ENUM ('match','discount','payee_release','refund');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE approval_status AS ENUM ('pending','approved','rejected','expired');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE refund_status AS ENUM ('requested','approved','submitted','succeeded','failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('queued','running','done','failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS merchants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid,
  name text NOT NULL,
  country char(2) NOT NULL,
  default_currency char(3) NOT NULL,
  timezone text NOT NULL,
  hitpay_mode text NOT NULL DEFAULT 'sandbox',
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  display_name text NOT NULL,
  email text,
  phone text,
  aliases text[] NOT NULL DEFAULT '{}',
  pause_chasing boolean NOT NULL DEFAULT false,
  last_success_method payment_method,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  customer_id uuid NOT NULL REFERENCES customers(id),
  ref text NOT NULL,
  amount_minor bigint NOT NULL,
  currency char(3) NOT NULL,
  amount_paid_minor bigint NOT NULL DEFAULT 0,
  issued_at timestamptz NOT NULL DEFAULT now(),
  due_at timestamptz NOT NULL,
  status invoice_status NOT NULL DEFAULT 'issued',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (merchant_id, ref)
);

CREATE TABLE IF NOT EXISTS payment_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  invoice_id uuid REFERENCES invoices(id),
  provider text NOT NULL,
  provider_request_id text NOT NULL,
  methods payment_method[] NOT NULL,
  url text,
  qr_payload text,
  purpose text NOT NULL,
  expires_at timestamptz,
  status request_status NOT NULL DEFAULT 'open',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_request_id)
);

CREATE TABLE IF NOT EXISTS payment_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  payment_request_id uuid REFERENCES payment_requests(id),
  provider_attempt_id text NOT NULL UNIQUE,
  method payment_method NOT NULL,
  amount_minor bigint NOT NULL,
  currency char(3) NOT NULL,
  status attempt_status NOT NULL,
  failure_code text,
  failure_class failure_class,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  provider text NOT NULL,
  provider_payment_id text NOT NULL UNIQUE,
  amount_minor bigint NOT NULL,
  currency char(3) NOT NULL,
  method payment_method NOT NULL,
  amount_refunded_minor bigint NOT NULL DEFAULT 0,
  payer_name text,
  payer_reference text,
  received_at timestamptz NOT NULL,
  match_status match_status NOT NULL DEFAULT 'unmatched',
  match_tier smallint,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS allocations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  payment_id uuid NOT NULL REFERENCES payments(id),
  invoice_id uuid NOT NULL REFERENCES invoices(id),
  amount_minor bigint NOT NULL CHECK (amount_minor > 0),
  approved_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS match_suggestions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  payment_id uuid NOT NULL REFERENCES payments(id),
  invoice_id uuid NOT NULL REFERENCES invoices(id),
  confidence numeric(3,2) NOT NULL,
  reason text NOT NULL,
  model text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rescues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  failed_attempt_id uuid NOT NULL UNIQUE REFERENCES payment_attempts(id),
  fallback_request_id uuid REFERENCES payment_requests(id),
  amount_minor bigint NOT NULL,
  currency char(3) NOT NULL,
  message_draft text,
  message_channel text NOT NULL DEFAULT 'dashboard',
  status rescue_status NOT NULL DEFAULT 'opened',
  churned_at timestamptz,
  recovered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  kind approval_kind NOT NULL,
  subject_id uuid NOT NULL,
  summary text NOT NULL,
  status approval_status NOT NULL DEFAULT 'pending',
  decided_by text,
  decided_at timestamptz,
  decision_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refunds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  payment_id uuid NOT NULL REFERENCES payments(id),
  approval_id uuid NOT NULL REFERENCES approvals(id),
  amount_minor bigint NOT NULL,
  reason text NOT NULL,
  provider_refund_id text UNIQUE,
  status refund_status NOT NULL DEFAULT 'requested',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS forecasts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  horizon_days int NOT NULL DEFAULT 14,
  series jsonb NOT NULL,
  min_balance_minor bigint NOT NULL,
  gap_minor bigint NOT NULL,
  inputs jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS discount_offers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  forecast_id uuid NOT NULL REFERENCES forecasts(id),
  invoice_id uuid NOT NULL REFERENCES invoices(id),
  discount_pct numeric(4,2) NOT NULL,
  discount_cost_minor bigint NOT NULL,
  gap_cost_minor bigint NOT NULL,
  payment_request_id uuid REFERENCES payment_requests(id),
  status text NOT NULL DEFAULT 'proposed',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhook_inbox (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  provider text NOT NULL,
  provider_event_id text NOT NULL,
  signature_valid boolean NOT NULL,
  raw_body bytea NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_event_id)
);

CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  kind text NOT NULL,
  payload jsonb NOT NULL,
  status job_status NOT NULL DEFAULT 'queued',
  attempts int NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id uuid NOT NULL REFERENCES merchants(id),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  actor text NOT NULL,
  type text NOT NULL,
  subject_type text NOT NULL,
  subject_id uuid NOT NULL,
  reason text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS payments_match_idx ON payments (merchant_id, match_status);
CREATE INDEX IF NOT EXISTS invoices_due_idx ON invoices (merchant_id, status, due_at);
CREATE INDEX IF NOT EXISTS rescues_status_idx ON rescues (merchant_id, status);
CREATE INDEX IF NOT EXISTS events_subject_idx ON events (merchant_id, subject_type, subject_id, occurred_at);
CREATE INDEX IF NOT EXISTS jobs_queued_idx ON jobs (status, run_after) WHERE status = 'queued';

CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'events is append-only';
END;
$$;

DROP TRIGGER IF EXISTS events_no_mutation ON events;
CREATE TRIGGER events_no_mutation
BEFORE UPDATE OR DELETE ON events
FOR EACH ROW EXECUTE FUNCTION events_append_only();

CREATE OR REPLACE VIEW v_recovery AS
SELECT
  count(*) FILTER (WHERE status <> 'dismissed') AS failures,
  count(*) FILTER (WHERE status IN ('recovered','won_back')) AS recovered,
  count(*) FILTER (WHERE status = 'churned') AS churned,
  count(*) FILTER (WHERE status = 'won_back') AS won_back,
  COALESCE(
    count(*) FILTER (WHERE status IN ('recovered','won_back'))::numeric
    / NULLIF(count(*) FILTER (WHERE status <> 'dismissed'), 0), 0
  ) AS recovery_rate,
  COALESCE(
    count(*) FILTER (WHERE status = 'churned')::numeric
    / NULLIF(count(*) FILTER (WHERE status <> 'dismissed'), 0), 0
  ) AS churn_rate
FROM rescues;

CREATE OR REPLACE VIEW v_at_risk AS
SELECT
  COALESCE((SELECT sum(amount_minor) FROM rescues WHERE status IN ('opened','offered')), 0)
  + COALESCE((SELECT sum(amount_minor) FROM payments WHERE match_status IN ('unmatched','suggested')), 0)
  + COALESCE((SELECT sum(amount_minor - amount_paid_minor) FROM invoices WHERE status IN ('issued','overdue','partially_paid')), 0)
  AS at_risk_minor;
