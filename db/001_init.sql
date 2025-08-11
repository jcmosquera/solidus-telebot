create table if not exists clients (
  client_id text primary key,
  client_name text not null,
  vault_account_id text not null
);

create table if not exists user_links (
  telegram_user_id bigint primary key,
  client_id text not null references clients(client_id),
  created_at timestamptz not null default now()
);

create table if not exists link_codes (
  code_hash text primary key,
  client_id text not null references clients(client_id),
  expires_at timestamptz not null,
  used_at timestamptz
);

create table if not exists asset_map (
  asset_id text primary key,
  coingecko_id text not null
);

create table if not exists price_cache (
  coingecko_id text primary key,
  usd numeric not null,
  usd_24h numeric not null,
  fetched_at timestamptz not null
);

create table if not exists audit (
  id bigserial primary key,
  telegram_user_id bigint not null,
  client_id text,
  action text not null,
  ts timestamptz not null default now()
);
