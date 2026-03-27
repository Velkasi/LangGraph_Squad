-- ─────────────────────────────────────────────────────────────────────────
-- L4 : Schéma PostgreSQL — mémoire identité & profil du team_agent
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS memory_facts (
    id              SERIAL PRIMARY KEY,
    content         TEXT        NOT NULL,
    category        VARCHAR(64) NOT NULL DEFAULT 'general',  -- preference, goal, identity, fact, decision
    confidence      FLOAT       NOT NULL DEFAULT 1.0,        -- 0.0 à 1.0
    usage_count     INTEGER     NOT NULL DEFAULT 0,
    last_used       TIMESTAMP   WITH TIME ZONE DEFAULT NOW(),
    created_at      TIMESTAMP   WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP   WITH TIME ZONE DEFAULT NOW(),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    contradicted_by INTEGER REFERENCES memory_facts(id) ON DELETE SET NULL
);

-- Index pour recherche rapide par catégorie et pertinence
CREATE INDEX IF NOT EXISTS idx_facts_category          ON memory_facts (category);
CREATE INDEX IF NOT EXISTS idx_facts_active_confidence ON memory_facts (is_active, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_facts_last_used         ON memory_facts (last_used DESC);

-- Table de validation : faits en attente de confirmation humaine
CREATE TABLE IF NOT EXISTS memory_pending (
    id          SERIAL PRIMARY KEY,
    content     TEXT        NOT NULL,
    category    VARCHAR(64) NOT NULL DEFAULT 'general',
    source      VARCHAR(64) NOT NULL DEFAULT 'agent',   -- agent, user
    confirmed   BOOLEAN,                                 -- NULL = en attente
    created_at  TIMESTAMP   WITH TIME ZONE DEFAULT NOW()
);

-- Vue des faits actifs les plus pertinents (utilisée par l4_search)
CREATE OR REPLACE VIEW top_facts AS
SELECT id, content, category, confidence, usage_count, last_used
FROM   memory_facts
WHERE  is_active = TRUE
ORDER  BY (confidence * 0.5 + LEAST(usage_count, 20) * 0.025) DESC
LIMIT  50;
