-- ============================================================
-- FinSight AI
-- 05_create_views.sql
--
-- Objetivo:
-- Criar views analíticas em cima das tabelas carregadas no PostgreSQL.
--
-- Observação:
-- A tabela finsight.parcelas_emprestimos existe, mas ainda não será usada
-- porque sua carga será ajustada em uma etapa posterior.
-- ============================================================


-- ============================================================
-- LIMPEZA DAS VIEWS
-- ============================================================

DROP VIEW IF EXISTS finsight.vw_contexto_empresa_mensal;
DROP VIEW IF EXISTS finsight.vw_anomalias_empresa;
DROP VIEW IF EXISTS finsight.vw_indicadores_liquidez_empresa;
DROP VIEW IF EXISTS finsight.vw_contas_pagar_abertas;
DROP VIEW IF EXISTS finsight.vw_contas_receber_abertas;
DROP VIEW IF EXISTS finsight.vw_fluxo_caixa_mensal;
DROP VIEW IF EXISTS finsight.vw_fluxo_caixa_diario;


-- ============================================================
-- 1. FLUXO DE CAIXA DIÁRIO
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_fluxo_caixa_diario AS
SELECT
    t.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,
    DATE(t.data_transacao) AS data_movimento,

    SUM(
        CASE
            WHEN t.tipo_transacao = 'entrada' THEN t.valor
            ELSE 0
        END
    ) AS total_entradas,

    SUM(
        CASE
            WHEN t.tipo_transacao = 'saida' THEN t.valor
            ELSE 0
        END
    ) AS total_saidas,

    SUM(
        CASE
            WHEN t.tipo_transacao = 'entrada' THEN t.valor
            WHEN t.tipo_transacao = 'saida' THEN -t.valor
            ELSE 0
        END
    ) AS saldo_dia,

    COUNT(*) AS qtd_transacoes

FROM finsight.transacoes t

INNER JOIN finsight.empresas e
    ON t.id_empresa = e.id_empresa

GROUP BY
    t.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,
    DATE(t.data_transacao);


-- ============================================================
-- 2. FLUXO DE CAIXA MENSAL
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_fluxo_caixa_mensal AS
SELECT
    f.id_empresa,
    f.nome_empresa,
    f.setor,
    f.porte,
    DATE_TRUNC('month', f.data_movimento)::date AS mes_referencia,

    SUM(f.total_entradas) AS total_entradas,
    SUM(f.total_saidas) AS total_saidas,
    SUM(f.saldo_dia) AS saldo_mes,
    SUM(f.qtd_transacoes) AS qtd_transacoes,

    AVG(f.saldo_dia) AS saldo_medio_diario,

    SUM(SUM(f.saldo_dia)) OVER (
        PARTITION BY f.id_empresa
        ORDER BY DATE_TRUNC('month', f.data_movimento)::date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS saldo_acumulado

FROM finsight.vw_fluxo_caixa_diario f

GROUP BY
    f.id_empresa,
    f.nome_empresa,
    f.setor,
    f.porte,
    DATE_TRUNC('month', f.data_movimento)::date;


-- ============================================================
-- 3. CONTAS A RECEBER ABERTAS / VENCIDAS
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_contas_receber_abertas AS
SELECT
    cr.id_recebimento,
    cr.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,

    cr.id_cliente,
    c.nome_cliente,
    c.segmento AS segmento_cliente,
    c.risco_cliente,

    cr.data_emissao,
    cr.data_vencimento,
    cr.data_pagamento,
    cr.valor,
    cr.status,
    cr.dias_atraso,

    CASE
        WHEN cr.status = 'vencida' THEN 'Vencida'
        WHEN cr.status = 'aberta' AND cr.data_vencimento < CURRENT_DATE THEN 'Vencida'
        WHEN cr.status = 'aberta' THEN 'Aberta'
        ELSE 'Outro'
    END AS classificacao_recebivel,

    CASE
        WHEN cr.data_vencimento < CURRENT_DATE
             AND cr.data_pagamento IS NULL
        THEN CURRENT_DATE - cr.data_vencimento
        ELSE 0
    END AS dias_em_aberto_ou_atraso

FROM finsight.contas_receber cr

INNER JOIN finsight.empresas e
    ON cr.id_empresa = e.id_empresa

INNER JOIN finsight.clientes c
    ON cr.id_cliente = c.id_cliente

WHERE cr.status IN ('aberta', 'vencida');


-- ============================================================
-- 4. CONTAS A PAGAR ABERTAS / VENCIDAS
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_contas_pagar_abertas AS
SELECT
    cp.id_pagamento,
    cp.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,

    cp.id_fornecedor,
    f.nome_fornecedor,
    f.categoria AS categoria_fornecedor,

    cp.data_emissao,
    cp.data_vencimento,
    cp.data_pagamento,
    cp.valor,
    cp.categoria,
    cp.status,

    CASE
        WHEN cp.status = 'vencida' THEN 'Vencida'
        WHEN cp.status = 'aberta' AND cp.data_vencimento < CURRENT_DATE THEN 'Vencida'
        WHEN cp.status = 'aberta' THEN 'Aberta'
        ELSE 'Outro'
    END AS classificacao_pagamento,

    CASE
        WHEN cp.data_vencimento < CURRENT_DATE
             AND cp.data_pagamento IS NULL
        THEN CURRENT_DATE - cp.data_vencimento
        ELSE 0
    END AS dias_em_aberto_ou_atraso

FROM finsight.contas_pagar cp

INNER JOIN finsight.empresas e
    ON cp.id_empresa = e.id_empresa

LEFT JOIN finsight.fornecedores f
    ON cp.id_fornecedor = f.id_fornecedor

WHERE cp.status IN ('aberta', 'vencida');


-- ============================================================
-- 5. INDICADORES DE LIQUIDEZ POR EMPRESA
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_indicadores_liquidez_empresa AS
WITH saldos_bancarios AS (
    SELECT
        id_empresa,
        SUM(saldo_inicial) AS saldo_inicial_total,
        SUM(limite_credito) AS limite_credito_total
    FROM finsight.contas_bancarias
    GROUP BY id_empresa
),

fluxo_realizado AS (
    SELECT
        id_empresa,
        SUM(
            CASE
                WHEN tipo_transacao = 'entrada' THEN valor
                ELSE 0
            END
        ) AS total_entradas_realizadas,

        SUM(
            CASE
                WHEN tipo_transacao = 'saida' THEN valor
                ELSE 0
            END
        ) AS total_saidas_realizadas,

        SUM(
            CASE
                WHEN tipo_transacao = 'entrada' THEN valor
                WHEN tipo_transacao = 'saida' THEN -valor
                ELSE 0
            END
        ) AS saldo_fluxo_realizado

    FROM finsight.transacoes
    GROUP BY id_empresa
),

recebiveis AS (
    SELECT
        id_empresa,
        SUM(valor) AS total_receber_aberto,
        SUM(
            CASE
                WHEN status = 'vencida' THEN valor
                ELSE 0
            END
        ) AS total_receber_vencido,
        COUNT(*) AS qtd_recebiveis_abertos
    FROM finsight.contas_receber
    WHERE status IN ('aberta', 'vencida')
    GROUP BY id_empresa
),

pagamentos AS (
    SELECT
        id_empresa,
        SUM(valor) AS total_pagar_aberto,
        SUM(
            CASE
                WHEN status = 'vencida' THEN valor
                ELSE 0
            END
        ) AS total_pagar_vencido,
        COUNT(*) AS qtd_pagamentos_abertos
    FROM finsight.contas_pagar
    WHERE status IN ('aberta', 'vencida')
    GROUP BY id_empresa
),

emprestimos_ativos AS (
    SELECT
        id_empresa,
        SUM(saldo_devedor) AS saldo_devedor_total,
        SUM(valor_parcela) AS parcelas_mensais_estimadas,
        COUNT(*) AS qtd_emprestimos_ativos
    FROM finsight.emprestimos
    WHERE status = 'ativo'
    GROUP BY id_empresa
)

SELECT
    e.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,
    e.faturamento_medio,

    COALESCE(sb.saldo_inicial_total, 0) AS saldo_inicial_total,
    COALESCE(sb.limite_credito_total, 0) AS limite_credito_total,

    COALESCE(fr.total_entradas_realizadas, 0) AS total_entradas_realizadas,
    COALESCE(fr.total_saidas_realizadas, 0) AS total_saidas_realizadas,
    COALESCE(fr.saldo_fluxo_realizado, 0) AS saldo_fluxo_realizado,

    COALESCE(r.total_receber_aberto, 0) AS total_receber_aberto,
    COALESCE(r.total_receber_vencido, 0) AS total_receber_vencido,
    COALESCE(r.qtd_recebiveis_abertos, 0) AS qtd_recebiveis_abertos,

    COALESCE(p.total_pagar_aberto, 0) AS total_pagar_aberto,
    COALESCE(p.total_pagar_vencido, 0) AS total_pagar_vencido,
    COALESCE(p.qtd_pagamentos_abertos, 0) AS qtd_pagamentos_abertos,

    COALESCE(emp.saldo_devedor_total, 0) AS saldo_devedor_emprestimos,
    COALESCE(emp.parcelas_mensais_estimadas, 0) AS parcelas_mensais_estimadas,
    COALESCE(emp.qtd_emprestimos_ativos, 0) AS qtd_emprestimos_ativos,

    (
        COALESCE(sb.saldo_inicial_total, 0)
        + COALESCE(fr.saldo_fluxo_realizado, 0)
        + COALESCE(r.total_receber_aberto, 0)
        + COALESCE(sb.limite_credito_total, 0)
        - COALESCE(p.total_pagar_aberto, 0)
        - COALESCE(emp.parcelas_mensais_estimadas, 0)
    ) AS caixa_liquido_estimado,

    ROUND(
        (
            COALESCE(sb.saldo_inicial_total, 0)
            + COALESCE(r.total_receber_aberto, 0)
            + COALESCE(sb.limite_credito_total, 0)
        )
        / NULLIF(
            COALESCE(p.total_pagar_aberto, 0)
            + COALESCE(emp.parcelas_mensais_estimadas, 0),
            0
        ),
        4
    ) AS indice_cobertura_liquidez,

    CASE
        WHEN (
            COALESCE(sb.saldo_inicial_total, 0)
            + COALESCE(fr.saldo_fluxo_realizado, 0)
            + COALESCE(r.total_receber_aberto, 0)
            + COALESCE(sb.limite_credito_total, 0)
            - COALESCE(p.total_pagar_aberto, 0)
            - COALESCE(emp.parcelas_mensais_estimadas, 0)
        ) < 0
        THEN 'Crítico'

        WHEN ROUND(
            (
                COALESCE(sb.saldo_inicial_total, 0)
                + COALESCE(r.total_receber_aberto, 0)
                + COALESCE(sb.limite_credito_total, 0)
            )
            / NULLIF(
                COALESCE(p.total_pagar_aberto, 0)
                + COALESCE(emp.parcelas_mensais_estimadas, 0),
                0
            ),
            4
        ) < 1
        THEN 'Alto'

        WHEN ROUND(
            (
                COALESCE(sb.saldo_inicial_total, 0)
                + COALESCE(r.total_receber_aberto, 0)
                + COALESCE(sb.limite_credito_total, 0)
            )
            / NULLIF(
                COALESCE(p.total_pagar_aberto, 0)
                + COALESCE(emp.parcelas_mensais_estimadas, 0),
                0
            ),
            4
        ) < 1.5
        THEN 'Médio'

        ELSE 'Baixo'
    END AS classificacao_risco_liquidez

FROM finsight.empresas e

LEFT JOIN saldos_bancarios sb
    ON e.id_empresa = sb.id_empresa

LEFT JOIN fluxo_realizado fr
    ON e.id_empresa = fr.id_empresa

LEFT JOIN recebiveis r
    ON e.id_empresa = r.id_empresa

LEFT JOIN pagamentos p
    ON e.id_empresa = p.id_empresa

LEFT JOIN emprestimos_ativos emp
    ON e.id_empresa = emp.id_empresa;


-- ============================================================
-- 6. ANOMALIAS POR EMPRESA
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_anomalias_empresa AS
SELECT
    a.id_anomalia,
    a.id_empresa,
    e.nome_empresa,
    e.setor,
    e.porte,

    a.tipo_anomalia,
    a.origem,
    a.data_evento,
    DATE_TRUNC('month', a.data_evento)::date AS mes_referencia,

    a.valor_original,
    a.valor_anomalo,
    a.valor_anomalo - a.valor_original AS impacto_estimado,

    CASE
        WHEN a.valor_original = 0 THEN NULL
        ELSE ROUND((a.valor_anomalo / a.valor_original), 4)
    END AS fator_anomalia,

    a.descricao

FROM finsight.anomalias_financeiras a

INNER JOIN finsight.empresas e
    ON a.id_empresa = e.id_empresa;


-- ============================================================
-- 7. CONTEXTO MENSAL DA EMPRESA
-- ============================================================

CREATE OR REPLACE VIEW finsight.vw_contexto_empresa_mensal AS
SELECT
    fm.id_empresa,
    fm.nome_empresa,
    fm.setor,
    fm.porte,
    fm.mes_referencia,

    fm.total_entradas,
    fm.total_saidas,
    fm.saldo_mes,
    fm.saldo_medio_diario,
    fm.saldo_acumulado,

    cm.inflacao_mensal_pct,
    cm.selic_anual_pct,

    COUNT(ev.id_evento) AS qtd_eventos_no_mes,

    COALESCE(
        STRING_AGG(DISTINCT ev.tipo_evento, ', '),
        'Sem evento'
    ) AS eventos_no_mes

FROM finsight.vw_fluxo_caixa_mensal fm

LEFT JOIN finsight.cenario_macroeconomico cm
    ON fm.mes_referencia = cm.mes_referencia

LEFT JOIN finsight.eventos_empresariais ev
    ON fm.id_empresa = ev.id_empresa
   AND fm.mes_referencia BETWEEN DATE_TRUNC('month', ev.data_inicio)::date
                              AND DATE_TRUNC('month', ev.data_fim)::date

GROUP BY
    fm.id_empresa,
    fm.nome_empresa,
    fm.setor,
    fm.porte,
    fm.mes_referencia,
    fm.total_entradas,
    fm.total_saidas,
    fm.saldo_mes,
    fm.saldo_medio_diario,
    fm.saldo_acumulado,
    cm.inflacao_mensal_pct,
    cm.selic_anual_pct;


-- ============================================================
-- CONSULTAS DE TESTE
-- ============================================================

SELECT 'vw_fluxo_caixa_diario' AS view_name, COUNT(*) AS qtd_linhas
FROM finsight.vw_fluxo_caixa_diario

UNION ALL

SELECT 'vw_fluxo_caixa_mensal', COUNT(*)
FROM finsight.vw_fluxo_caixa_mensal

UNION ALL

SELECT 'vw_contas_receber_abertas', COUNT(*)
FROM finsight.vw_contas_receber_abertas

UNION ALL

SELECT 'vw_contas_pagar_abertas', COUNT(*)
FROM finsight.vw_contas_pagar_abertas

UNION ALL

SELECT 'vw_indicadores_liquidez_empresa', COUNT(*)
FROM finsight.vw_indicadores_liquidez_empresa

UNION ALL

SELECT 'vw_anomalias_empresa', COUNT(*)
FROM finsight.vw_anomalias_empresa

UNION ALL

SELECT 'vw_contexto_empresa_mensal', COUNT(*)
FROM finsight.vw_contexto_empresa_mensal;