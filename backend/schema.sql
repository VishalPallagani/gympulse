create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  phone_number text unique not null,
  dashboard_token text unique not null default gen_random_uuid()::text,
  name text,
  last_weight_prompted_at date,
  created_at timestamp default now()
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  logged_at timestamp default now(),
  raw_message text,
  notes text
);

create table if not exists sets (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id),
  user_id uuid references users(id),
  exercise_name text not null,
  muscle_group text not null,
  weight_kg numeric,
  reps integer,
  sets_count integer,
  total_volume_kg numeric generated always as (weight_kg * reps * sets_count) stored,
  logged_at timestamp default now()
);

create table if not exists personal_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  exercise_name text not null,
  weight_kg numeric not null,
  achieved_at timestamp default now(),
  unique(user_id, exercise_name)
);

create table if not exists medals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  medal_key text not null,
  medal_name text not null,
  medal_emoji text,
  description text,
  awarded_at timestamp default now(),
  unique(user_id, medal_key)
);

create table if not exists subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  razorpay_subscription_id text,
  razorpay_customer_id text,
  status text default 'free',
  plan text default 'free',
  started_at timestamp,
  expires_at timestamp,
  created_at timestamp default now()
);

create table if not exists payment_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  phone_number text,
  event_type text not null,
  status text,
  amount_inr numeric,
  razorpay_payment_id text,
  razorpay_subscription_id text,
  razorpay_customer_id text,
  payload_json jsonb,
  occurred_at timestamp default now(),
  created_at timestamp default now()
);

create table if not exists body_weight_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  weight_kg numeric not null,
  logged_on date default current_date,
  source text default 'whatsapp',
  created_at timestamp default now(),
  unique(user_id, logged_on)
);

create index if not exists idx_sessions_user_id_logged_at on sessions(user_id, logged_at);
create index if not exists idx_sets_user_id_logged_at on sets(user_id, logged_at);
create index if not exists idx_sets_session_id on sets(session_id);
create index if not exists idx_medals_user_id on medals(user_id);
create index if not exists idx_subscriptions_user_id_created_at on subscriptions(user_id, created_at desc);
create index if not exists idx_subscriptions_subscription_id on subscriptions(razorpay_subscription_id);
create index if not exists idx_subscriptions_customer_id on subscriptions(razorpay_customer_id);
create index if not exists idx_payment_events_event_type on payment_events(event_type);
create index if not exists idx_payment_events_occurred_at on payment_events(occurred_at);
create index if not exists idx_body_weight_user_logged_on on body_weight_logs(user_id, logged_on desc);
