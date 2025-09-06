-- Enable required extensions
create extension if not exists postgis;
create extension if not exists pgcrypto; -- for gen_random_uuid()

-- Categories table (for default styles / grouping)
create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  color text,
  icon_url text,
  created_at timestamptz not null default now()
);

-- Places (pins)
create table if not exists public.places (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  geom geometry(Point, 4326) not null,
  category_id uuid references public.categories(id),
  properties jsonb not null default '{}',
  icon_url text,
  color text,
  scale numeric not null default 1.0,
  is_published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-update updated_at on modification
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists trg_places_updated_at on public.places;
create trigger trg_places_updated_at
before update on public.places
for each row execute function public.set_updated_at();

-- Media for places (images)
create table if not exists public.place_media (
  id uuid primary key default gen_random_uuid(),
  place_id uuid not null references public.places(id) on delete cascade,
  kind text not null check (kind in ('image')),
  url text not null,
  is_primary boolean not null default false,
  position int not null default 0,
  created_at timestamptz not null default now()
);

-- Indexes
create index if not exists places_geom_gix on public.places using gist (geom);
create index if not exists places_updated_idx on public.places (updated_at desc);
create index if not exists place_media_place_idx on public.place_media (place_id, is_primary desc, position asc, created_at asc);

-- RLS policies (public read of published data)
alter table public.places enable row level security;
alter table public.place_media enable row level security;
alter table public.categories enable row level security;

do $$ begin
  -- anon can read only published places
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='places' and policyname='places_public_select'
  ) then
    create policy places_public_select on public.places for select using (is_published = true);
  end if;

  -- anon can read categories (style metadata)
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='categories' and policyname='categories_public_select'
  ) then
    create policy categories_public_select on public.categories for select using (true);
  end if;

  -- anon can read media only for published places
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='place_media' and policyname='place_media_public_select'
  ) then
    create policy place_media_public_select on public.place_media for select using (
      exists (
        select 1 from public.places p where p.id = place_media.place_id and p.is_published = true
      )
    );
  end if;
end $$;

-- GeoJSON RPC: returns FeatureCollection for given bbox/filters
create or replace function public.places_geojson(
  lon_min double precision,
  lat_min double precision,
  lon_max double precision,
  lat_max double precision,
  in_category_ids uuid[] default null,
  in_since timestamptz default null
)
returns jsonb
language sql
stable
as $$
  with env as (
    select ST_MakeEnvelope(lon_min, lat_min, lon_max, lat_max, 4326) as bbox
  ), base as (
    select
      pl.id,
      pl.title,
      pl.description,
      pl.geom,
      pl.icon_url as place_icon,
      pl.color as place_color,
      pl.scale,
      pl.category_id,
      cat.name as category_name,
      cat.icon_url as category_icon,
      cat.color as category_color,
      (
        select m.url from public.place_media m
        where m.place_id = pl.id and m.kind = 'image'
        order by m.is_primary desc, m.position asc, m.created_at asc
        limit 1
      ) as primary_image_url
    from public.places pl
    join env on true
    left join public.categories cat on cat.id = pl.category_id
    where pl.is_published = true
      and ST_Intersects(pl.geom, env.bbox)
      and (in_category_ids is null or pl.category_id = any(in_category_ids))
      and (in_since is null or pl.updated_at >= in_since)
  ), features as (
    select jsonb_build_object(
      'type','Feature',
      'geometry', ST_AsGeoJSON(b.geom)::jsonb,
      'properties', jsonb_build_object(
        'id', b.id,
        'title', b.title,
        'description', coalesce(b.description, ''),
        'primary_image_url', b.primary_image_url,
        'icon_url', coalesce(b.place_icon, b.category_icon),
        'color', coalesce(b.place_color, b.category_color),
        'scale', b.scale,
        'category', b.category_name
      )
    ) as f
    from base b
  )
  select jsonb_build_object(
    'type','FeatureCollection',
    'features', coalesce(jsonb_agg(f), '[]'::jsonb)
  )
  from features;
$$;

-- Example seed (optional)
-- insert into public.categories(name, color, icon_url) values ('Default', '#ffffff', null);
-- insert into public.places(title, description, geom, category_id, is_published)
-- values ('Toranomon Hills', 'ランドマーク', ST_SetSRID(ST_MakePoint(139.7499, 35.6664),4326), (select id from public.categories limit 1), true);

