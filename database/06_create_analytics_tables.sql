-- ============================================================
-- FinSight AI
-- 06_create_analytics_tables.sql
--
-- Objetivo:
-- Criar as tabelas analíticas finais do projeto.
--
-- Observação:
-- Neste momento vamos apenas criar as estruturas.
-- A geração dos dados analíticos será feita posteriormente em Python.
-- ============================================================


-- ============================================================
-- LIMPEZA DAS TABELAS ANALÍTICAS
-- ============================================================

DROP TABLE IF EXISTS finsight.insights_llm;
DROP TABLE IF EXISTS finsight.alertas_financeiros;
DROP TABLE IF EXISTS finsight.scores_liquidez;
DROP TABLE IF EXISTS finsight.previsoes_fluxo_caixa;


-- ============================================================
-- 1. PREVISÕES DE FLUXO DE CAIXA
-- ============================================================

CREATE TABLE finsight.previsoes_fluxo_caixa (

    id_previsao SERIAL PRIMARY KEY,

    id_empresa INTEGER NOT NULL,

    data_geracao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    data_previsao DATE NOT NULL,

    horizonte_dias INTEGER NOT NULL,

    entrada_prevista NUMERIC(18,2),

    saida_prevista NUMERIC(18,2),

    saldo_previsto NUMERIC(18,2),

    intervalo_inferior NUMERIC(18,2),

    intervalo_superior NUMERIC(18,2),

    probabilidade_caixa_negativo NUMERIC(8,4),

    modelo_utilizado VARCHAR(100),

    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_previsoes_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT chk_previsoes_horizonte
        CHECK (horizonte_dias > 0),

    CONSTRAINT chk_previsoes_probabilidade
        CHECK (
            probabilidade_caixa_negativo IS NULL
            OR (
                probabilidade_caixa_negativo >= 0
                AND probabilidade_caixa_negativo <= 1
            )
        )
);


-- ============================================================
-- 2. SCORES DE LIQUIDEZ
-- ============================================================

CREATE TABLE finsight.scores_liquidez (

    id_score SERIAL PRIMARY KEY,

    id_empresa INTEGER NOT NULL,

    data_referencia DATE NOT NULL,

    score_liquidez NUMERIC(8,4) NOT NULL,

    classificacao_risco VARCHAR(20) NOT NULL,

    probabilidade_caixa_negativo NUMERIC(8,4),

    inadimplencia_percentual NUMERIC(8,4),

    comprometimento_receita NUMERIC(8,4),

    cobertura_divida NUMERIC(8,4),

    concentracao_clientes NUMERIC(8,4),

    volatilidade_caixa NUMERIC(8,4),

    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_scores_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT chk_score_liquidez
        CHECK (score_liquidez >= 0 AND score_liquidez <= 100),

    CONSTRAINT chk_classificacao_risco
        CHECK (classificacao_risco IN ('Baixo', 'Médio', 'Alto', 'Crítico')),

    CONSTRAINT chk_scores_probabilidade
        CHECK (
            probabilidade_caixa_negativo IS NULL
            OR (
                probabilidade_caixa_negativo >= 0
                AND probabilidade_caixa_negativo <= 1
            )
        )
);


-- ============================================================
-- 3. ALERTAS FINANCEIROS
-- ============================================================

CREATE TABLE finsight.alertas_financeiros (

    id_alerta SERIAL PRIMARY KEY,

    id_empresa INTEGER NOT NULL,

    data_alerta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    tipo_alerta VARCHAR(100) NOT NULL,

    nivel_risco VARCHAR(20) NOT NULL,

    descricao TEXT NOT NULL,

    acao_recomendada TEXT,

    status_alerta VARCHAR(30) NOT NULL DEFAULT 'Aberto',

    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_alertas_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT chk_alertas_nivel_risco
        CHECK (nivel_risco IN ('Baixo', 'Médio', 'Alto', 'Crítico')),

    CONSTRAINT chk_alertas_status
        CHECK (status_alerta IN ('Aberto', 'Em análise', 'Resolvido', 'Ignorado'))
);


-- ============================================================
-- 4. INSIGHTS LLM
-- ============================================================

CREATE TABLE finsight.insights_llm (

    id_insight SERIAL PRIMARY KEY,

    id_empresa INTEGER NOT NULL,

    data_geracao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    resumo_executivo TEXT,

    recomendacoes TEXT,

    principais_riscos TEXT,

    acoes_prioritarias TEXT,

    modelo_utilizado VARCHAR(100),

    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_insights_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_previsoes_empresa
ON finsight.previsoes_fluxo_caixa (id_empresa);

CREATE INDEX idx_previsoes_data
ON finsight.previsoes_fluxo_caixa (data_previsao);

CREATE INDEX idx_previsoes_horizonte
ON finsight.previsoes_fluxo_caixa (horizonte_dias);


CREATE INDEX idx_scores_empresa
ON finsight.scores_liquidez (id_empresa);

CREATE INDEX idx_scores_data
ON finsight.scores_liquidez (data_referencia);

CREATE INDEX idx_scores_classificacao
ON finsight.scores_liquidez (classificacao_risco);


CREATE INDEX idx_alertas_empresa
ON finsight.alertas_financeiros (id_empresa);

CREATE INDEX idx_alertas_data
ON finsight.alertas_financeiros (data_alerta);

CREATE INDEX idx_alertas_nivel
ON finsight.alertas_financeiros (nivel_risco);

CREATE INDEX idx_alertas_status
ON finsight.alertas_financeiros (status_alerta);


CREATE INDEX idx_insights_empresa
ON finsight.insights_llm (id_empresa);

CREATE INDEX idx_insights_data
ON finsight.insights_llm (data_geracao);


-- ============================================================
-- VALIDAÇÃO
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'finsight'
  AND table_name IN (
      'previsoes_fluxo_caixa',
      'scores_liquidez',
      'alertas_financeiros',
      'insights_llm'
  )
ORDER BY table_name;