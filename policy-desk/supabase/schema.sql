-- Run in the SQL editor of a dedicated Supabase project.
begin;
create extension if not exists vector with schema extensions;
set local search_path = public, extensions;

create table if not exists public.policy_chunks (
    id text primary key,
    content text not null,
    metadata jsonb not null,
    embedding extensions.vector not null,
    terms tsvector generated always as (
        setweight(to_tsvector('english', metadata->>'section'), 'A') ||
        setweight(to_tsvector('english', content), 'B')
    ) stored
);
alter table public.policy_chunks enable row level security;
revoke all on public.policy_chunks from public, anon, authenticated;
grant select, insert, delete on public.policy_chunks to service_role;
create index if not exists policy_chunks_terms_idx on public.policy_chunks using gin (terms);

-- The corpus is small enough for exact vector search. Fuse the dense and
-- full-text rankings using reciprocal rank fusion before selecting candidates.
create or replace function public.search_policy(
    query_text text,
    query_embedding extensions.vector,
    embedding_model text,
    result_limit integer default 12,
    search_mode text default 'hybrid'
)
returns table (id text, content text, metadata jsonb, score double precision)
language sql stable security invoker
set search_path = public, extensions
as $$
    with query as (
        select to_tsquery(
            'english',
            coalesce((
                select string_agg(quote_literal(lexeme), ' | ')
                from unnest(tsvector_to_array(to_tsvector('english', query_text))) as terms(lexeme)
            ), 'zzemptypolicyqueryzz')
        ) as terms
    ), dense as (
        select c.id, row_number() over (order by c.embedding <=> query_embedding, c.id) as rank
        from public.policy_chunks c
        where query_embedding is not null and search_mode <> 'lexical' and c.metadata->>'embedding_model' = search_policy.embedding_model
        order by c.embedding <=> query_embedding, c.id
        limit 24
    ), lexical as (
        select c.id, row_number() over (order by ts_rank_cd(c.terms, q.terms) desc, c.id) as rank
        from public.policy_chunks c cross join query q
        where search_mode <> 'dense' and c.terms @@ q.terms
          and c.metadata->>'embedding_model' = search_policy.embedding_model
        order by ts_rank_cd(c.terms, q.terms) desc, c.id
        limit 24
    )
    select c.id, c.content, c.metadata,
           coalesce(1.0 / (60 + d.rank), 0)::double precision +
           coalesce(1.0 / (60 + l.rank), 0)::double precision as score
    from dense d full outer join lexical l using (id)
    join public.policy_chunks c on c.id = coalesce(d.id, l.id)
    order by score desc, c.id
    limit least(greatest(result_limit, 1), 24);
$$;

-- A refresh replaces the whole snapshot in one transaction. Concurrent
-- refreshes serialize and failed inserts leave the previous snapshot intact.
create or replace function public.replace_policy_snapshot(chunks jsonb)
returns integer language plpgsql security invoker
set search_path = public, extensions
as $$
begin
    if jsonb_typeof(chunks) is distinct from 'array' or jsonb_array_length(chunks) = 0 then
        raise exception 'Policy snapshot must contain chunks';
    end if;
    lock table public.policy_chunks in share row exclusive mode;
    delete from public.policy_chunks where id is not null;
    insert into public.policy_chunks (id, content, metadata, embedding)
    select item.id, item.content, item.metadata, item.embedding::extensions.vector
    from jsonb_to_recordset(chunks) as item(id text, content text, metadata jsonb, embedding text);
    return jsonb_array_length(chunks);
end;
$$;

revoke execute on function public.search_policy(text, extensions.vector, text, integer, text) from public, anon, authenticated;
revoke execute on function public.replace_policy_snapshot(jsonb) from public, anon, authenticated;
grant execute on function public.search_policy(text, extensions.vector, text, integer, text) to service_role;
grant execute on function public.replace_policy_snapshot(jsonb) to service_role;
commit;
