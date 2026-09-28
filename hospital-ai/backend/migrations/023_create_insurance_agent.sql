-- Insurance Agent tables.
-- Stores the policy snapshot supplied by hospital staff and immutable
-- Insurance Agent run outputs for audit/review.

create table if not exists insurance_policies (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  provider_name text not null default '',
  policy_number text not null default '',
  member_id text,
  plan_name text not null default '',
  status text not null default 'unknown',
  effective_from date,
  effective_to date,
  coverage_percent numeric(5,2) not null default 0 check (coverage_percent between 0 and 100),
  deductible_remaining numeric(12,2) not null default 0 check (deductible_remaining >= 0),
  out_of_pocket_remaining numeric(12,2) check (out_of_pocket_remaining >= 0),
  annual_limit_remaining numeric(12,2) check (annual_limit_remaining >= 0),
  copay numeric(12,2) not null default 0 check (copay >= 0),
  covered_services jsonb not null default '[]'::jsonb,
  excluded_services jsonb not null default '[]'::jsonb,
  preauthorization_services jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists insurance_policies_patient_policy_idx
  on insurance_policies(patient_id, policy_number);

create index if not exists insurance_policies_patient_idx
  on insurance_policies(patient_id, updated_at desc);

create table if not exists insurance_results (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  service_name text not null,
  service_date date not null,
  billed_amount numeric(12,2) not null default 0 check (billed_amount >= 0),
  policy_number text not null default '',
  policy_json jsonb not null default '{}'::jsonb,
  policy_verification_json jsonb not null default '{}'::jsonb,
  coverage_estimate_json jsonb not null default '{}'::jsonb,
  claim_draft_json jsonb not null default '{}'::jsonb,
  fraud_screening_json jsonb not null default '{}'::jsonb,
  preauthorization_json jsonb not null default '{}'::jsonb,
  request_json jsonb not null default '{}'::jsonb,
  summary text not null default '',
  engine text not null default 'ai_orchestrator',
  status text not null default 'Completed',
  warnings_json jsonb not null default '[]'::jsonb,
  processing_time_ms integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists insurance_results_patient_idx
  on insurance_results(patient_id, created_at desc);

create index if not exists insurance_results_service_date_idx
  on insurance_results(patient_id, service_name, service_date);
