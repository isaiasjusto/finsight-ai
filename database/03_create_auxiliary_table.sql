CREATE TABLE IF NOT EXISTS finsight.cenario_macroeconomico (
    id_cenario SERIAL PRIMARY KEY,
    mes_referencia DATE NOT NULL UNIQUE,
    inflacao_mensal_pct NUMERIC(8,4) NOT NULL,
    selic_anual_pct NUMERIC(8,4) NOT NULL,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finsight.eventos_empresariais (
    id_evento SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    tipo_evento VARCHAR(100) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    multiplicador_receita NUMERIC(10,4) NOT NULL,
    multiplicador_despesa NUMERIC(10,4) NOT NULL,
    descricao TEXT,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_eventos_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);

CREATE TABLE IF NOT EXISTS finsight.anomalias_financeiras (
    id_anomalia SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    tipo_anomalia VARCHAR(100) NOT NULL,
    data_evento DATE NOT NULL,
    valor_original NUMERIC(15,2) NOT NULL,
    valor_anomalo NUMERIC(15,2) NOT NULL,
    origem VARCHAR(20) NOT NULL,
    descricao TEXT,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_anomalias_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);

CREATE TABLE IF NOT EXISTS finsight.parcelas_emprestimos (
    id_parcela SERIAL PRIMARY KEY,
    id_emprestimo INTEGER NOT NULL,
    numero_parcela INTEGER NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    valor_parcela NUMERIC(15,2) NOT NULL,
    valor_juros NUMERIC(15,2),
    valor_amortizacao NUMERIC(15,2),
    saldo_devedor NUMERIC(15,2),
    status VARCHAR(20) DEFAULT 'aberta',
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_parcelas_emprestimo
        FOREIGN KEY (id_emprestimo)
        REFERENCES finsight.emprestimos(id_emprestimo)
);