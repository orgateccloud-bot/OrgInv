-- ═══════════════════════════════════════════════════════════════════
-- OrgAudi · Espólio — Schema inicial
-- ORGATEC CONTABILIDADE E AUDITORIA
--
-- Como aplicar:
--   1. Crie um projeto em https://supabase.com/dashboard
--   2. Vá em SQL Editor → New Query
--   3. Cole este arquivo e execute
--   4. Copie URL + anon key para frontend/.env.local
-- ═══════════════════════════════════════════════════════════════════

-- Extensões necessárias
create extension if not exists "uuid-ossp";

-- ── Tabela: espolio ─────────────────────────────────────────────
create table if not exists public.espolio (
  id            uuid primary key default uuid_generate_v4(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  nome          text not null,
  cpf_falecido  text,
  data_obito    date,
  data_partilha date,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists espolio_user_idx on public.espolio(user_id);

-- ── Tabela: herdeiro ────────────────────────────────────────────
create table if not exists public.herdeiro (
  id           uuid primary key default uuid_generate_v4(),
  espolio_id   uuid not null references public.espolio(id) on delete cascade,
  nome         text not null,
  cpf          text,
  fracao_monte numeric(10, 6),
  eh_meeiro    boolean not null default false,
  ordem        int not null default 0
);

create index if not exists herdeiro_espolio_idx on public.herdeiro(espolio_id);

-- ── Tabela: bem ─────────────────────────────────────────────────
create table if not exists public.bem (
  id                    uuid primary key default uuid_generate_v4(),
  espolio_id            uuid not null references public.espolio(id) on delete cascade,
  identificacao         text not null,
  matricula             text,
  municipio             text,
  regime                text,
  opcao                 text,
  eh_imovel             boolean not null default true,
  custo_aquisicao_dirpf numeric(15, 2),
  data_aquisicao        date,
  valor_partilha        numeric(15, 2),
  valor_venda           numeric(15, 2),
  data_operacao         date,
  ordem                 int not null default 0
);

create index if not exists bem_espolio_idx on public.bem(espolio_id);

-- ── Tabela: extracao_ia (auditoria de extrações Claude) ────────
create table if not exists public.extracao_ia (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  espolio_id      uuid references public.espolio(id) on delete set null,
  documentos      text[] not null default '{}',
  resultado_json  jsonb not null,
  tokens_input    int,
  tokens_output   int,
  audit_hash      text,
  created_at      timestamptz not null default now()
);

create index if not exists extracao_user_idx on public.extracao_ia(user_id);

-- ── Trigger: updated_at automático no espolio ──────────────────
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists espolio_touch on public.espolio;
create trigger espolio_touch
  before update on public.espolio
  for each row execute function public.touch_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- Row Level Security — cada usuário só vê o próprio espólio
-- ═══════════════════════════════════════════════════════════════════
alter table public.espolio      enable row level security;
alter table public.herdeiro     enable row level security;
alter table public.bem          enable row level security;
alter table public.extracao_ia  enable row level security;

-- Espolio: dono total
drop policy if exists espolio_owner_all on public.espolio;
create policy espolio_owner_all on public.espolio
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Herdeiro: através do espólio dono
drop policy if exists herdeiro_owner_all on public.herdeiro;
create policy herdeiro_owner_all on public.herdeiro
  for all using (
    espolio_id in (select id from public.espolio where user_id = auth.uid())
  ) with check (
    espolio_id in (select id from public.espolio where user_id = auth.uid())
  );

-- Bem: através do espólio dono
drop policy if exists bem_owner_all on public.bem;
create policy bem_owner_all on public.bem
  for all using (
    espolio_id in (select id from public.espolio where user_id = auth.uid())
  ) with check (
    espolio_id in (select id from public.espolio where user_id = auth.uid())
  );

-- Extração IA: dono total
drop policy if exists extracao_owner_all on public.extracao_ia;
create policy extracao_owner_all on public.extracao_ia
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
