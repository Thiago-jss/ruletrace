CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS corpus_generations (
    id text PRIMARY KEY,
    embedding_model text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS active_corpus (
    singleton boolean PRIMARY KEY CHECK (singleton),
    generation_id text NOT NULL REFERENCES corpus_generations(id)
);

CREATE TABLE IF NOT EXISTS chunks (
    generation_id text NOT NULL REFERENCES corpus_generations(id) ON DELETE CASCADE,
    strategy text NOT NULL CHECK (strategy IN ('section', 'window')),
    chunk_id text NOT NULL,
    rule_id text NOT NULL,
    version text NOT NULL,
    source text NOT NULL,
    locator text NOT NULL,
    category text NOT NULL,
    starts_on date NOT NULL,
    ends_on date,
    content text NOT NULL,
    embedding vector(768) NOT NULL,
    lexical tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED,
    PRIMARY KEY (generation_id, strategy, chunk_id),
    CHECK (ends_on IS NULL OR ends_on > starts_on)
);

CREATE INDEX IF NOT EXISTS chunks_scope_idx ON chunks (generation_id, strategy, category, starts_on);
CREATE INDEX IF NOT EXISTS chunks_lexical_idx ON chunks USING gin (lexical);

CREATE TABLE IF NOT EXISTS registration_fixtures (
    id text PRIMARY KEY,
    category text NOT NULL,
    status text NOT NULL
);

INSERT INTO registration_fixtures (id, category, status) VALUES
    ('EVT-042', 'expositor', 'incompleta'),
    ('EVT-073', 'oficineiro', 'incompleta'),
    ('EVT-105', 'expositor', 'confirmada')
ON CONFLICT DO NOTHING;
