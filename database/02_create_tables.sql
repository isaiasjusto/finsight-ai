CREATE TABLE IF NOT EXISTS finsight.empresas (
    id_empresa SERIAL PRIMARY KEY,
    nome_empresa VARCHAR(150) NOT NULL,
    setor VARCHAR(100) NOT NULL,
    porte VARCHAR(30) NOT NULL,
    data_abertura DATE,
    faturamento_medio NUMERIC(15,2),
    quantidade_funcionarios INTEGER,
    status VARCHAR(20) DEFAULT 'ativa',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finsight.contas_bancarias (
    id_conta SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    banco VARCHAR(100) NOT NULL,
    tipo_conta VARCHAR(50) NOT NULL,
    saldo_inicial NUMERIC(15,2) NOT NULL DEFAULT 0,
    limite_credito NUMERIC(15,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa',
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_contas_bancarias_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);

CREATE TABLE IF NOT EXISTS finsight.clientes (
    id_cliente SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    nome_cliente VARCHAR(150) NOT NULL,
    segmento VARCHAR(100),
    limite_credito NUMERIC(15,2) NOT NULL DEFAULT 0,
    risco_cliente VARCHAR(20) NOT NULL DEFAULT 'baixo',
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT fk_clientes_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);

CREATE TABLE IF NOT EXISTS finsight.fornecedores (
    id_fornecedor SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    nome_fornecedor VARCHAR(150) NOT NULL,
    categoria VARCHAR(100),
    prazo_medio_pagamento INTEGER NOT NULL DEFAULT 30,
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT fk_fornecedores_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa)
);

CREATE TABLE IF NOT EXISTS finsight.transacoes (
    id_transacao BIGSERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    id_conta INTEGER NOT NULL,
    data_transacao TIMESTAMP NOT NULL,
    tipo_transacao VARCHAR(10) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    descricao VARCHAR(255),
    valor NUMERIC(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmada',
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_transacoes_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT fk_transacoes_conta
        FOREIGN KEY (id_conta)
        REFERENCES finsight.contas_bancarias(id_conta),

    CONSTRAINT ck_transacoes_tipo
        CHECK (tipo_transacao IN ('entrada', 'saida')),

    CONSTRAINT ck_transacoes_valor
        CHECK (valor > 0)
);

CREATE TABLE IF NOT EXISTS finsight.contas_receber (
    id_recebimento SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    id_cliente INTEGER NOT NULL,
    data_emissao DATE NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    valor NUMERIC(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'aberta',
    dias_atraso INTEGER NOT NULL DEFAULT 0,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_contas_receber_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT fk_contas_receber_cliente
        FOREIGN KEY (id_cliente)
        REFERENCES finsight.clientes(id_cliente),

    CONSTRAINT ck_contas_receber_valor
        CHECK (valor > 0),

    CONSTRAINT ck_contas_receber_datas
        CHECK (data_vencimento >= data_emissao),

    CONSTRAINT ck_contas_receber_atraso
        CHECK (dias_atraso >= 0)
);
CREATE TABLE IF NOT EXISTS finsight.contas_pagar (
    id_pagamento SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    id_fornecedor INTEGER NOT NULL,
    data_emissao DATE NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    valor NUMERIC(15,2) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'aberta',
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_contas_pagar_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT fk_contas_pagar_fornecedor
        FOREIGN KEY (id_fornecedor)
        REFERENCES finsight.fornecedores(id_fornecedor),

    CONSTRAINT ck_contas_pagar_valor
        CHECK (valor > 0),

    CONSTRAINT ck_contas_pagar_datas
        CHECK (data_vencimento >= data_emissao)
);
CREATE TABLE IF NOT EXISTS finsight.emprestimos (
    id_emprestimo SERIAL PRIMARY KEY,
    id_empresa INTEGER NOT NULL,
    instituicao VARCHAR(150) NOT NULL,
    valor_contratado NUMERIC(15,2) NOT NULL,
    taxa_juros NUMERIC(8,4) NOT NULL,
    quantidade_parcelas INTEGER NOT NULL,
    valor_parcela NUMERIC(15,2) NOT NULL,
    saldo_devedor NUMERIC(15,2) NOT NULL,
    data_contratacao DATE NOT NULL,
    data_proxima_parcela DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_emprestimos_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES finsight.empresas(id_empresa),

    CONSTRAINT ck_emprestimos_valor
        CHECK (valor_contratado > 0),

    CONSTRAINT ck_emprestimos_taxa
        CHECK (taxa_juros >= 0),

    CONSTRAINT ck_emprestimos_parcelas
        CHECK (quantidade_parcelas > 0),

    CONSTRAINT ck_emprestimos_valor_parcela
        CHECK (valor_parcela > 0),

    CONSTRAINT ck_emprestimos_saldo
        CHECK (saldo_devedor >= 0)
);
