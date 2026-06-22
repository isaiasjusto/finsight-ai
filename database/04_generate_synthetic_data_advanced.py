"""
FinSight AI - Gerador Avançado de Dados Sintéticos Financeiros

Recursos:
- Empresas de diferentes setores e perfis financeiros
- Sazonalidade mensal e efeito de feriados brasileiros
- Cenário macroeconômico sintético: inflação e Selic
- Crescimento, deterioração e crises por empresa
- Clientes com perfis de risco e comportamento de atraso
- Contas a receber e transações de entrada coerentes
- Contas a pagar e transações de saída coerentes
- Empréstimos e parcelas mensais registradas no fluxo de caixa
- Eventos extraordinários e anomalias financeiras
- Geração reprodutível
- Validação de integridade e qualidade
- Exportação para CSV
- Carga opcional no PostgreSQL
- Modo incremental opcional

Execução:
    python src/04_generate_synthetic_data_advanced.py

Carga no PostgreSQL:
    python src/04_generate_synthetic_data_advanced.py --load-db

Carga incremental:
    python src/04_generate_synthetic_data_advanced.py --load-db --incremental

Dependências:
    pip install pandas numpy faker sqlalchemy psycopg2-binary python-dotenv
"""

from __future__ import annotations

import argparse
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

fake = Faker("pt_BR")
Faker.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"

START_DATE = date(2023, 1, 1)
END_DATE = date(2026, 6, 17)

NUM_EMPRESAS = 20

SETOR_CONFIG: dict[str, dict[str, Any]] = {
    "Varejo": {
        "peso": 0.28,
        "faturamento_mensal": (180_000, 900_000),
        "funcionarios": (12, 180),
        "clientes": (90, 180),
        "fornecedores": (25, 60),
        "margem_liquida": (0.06, 0.14),
        "sensibilidade_inflacao": 0.75,
        "sensibilidade_selic": 0.45,
        "sazonalidade": {
            1: 0.78, 2: 0.82, 3: 0.90, 4: 0.94,
            5: 1.00, 6: 1.02, 7: 0.96, 8: 1.00,
            9: 1.05, 10: 1.12, 11: 1.38, 12: 1.55,
        },
    },
    "Serviços": {
        "peso": 0.24,
        "faturamento_mensal": (120_000, 650_000),
        "funcionarios": (8, 120),
        "clientes": (40, 110),
        "fornecedores": (12, 35),
        "margem_liquida": (0.10, 0.22),
        "sensibilidade_inflacao": 0.45,
        "sensibilidade_selic": 0.35,
        "sazonalidade": {
            1: 0.90, 2: 0.92, 3: 1.00, 4: 1.02,
            5: 1.00, 6: 1.04, 7: 0.96, 8: 1.01,
            9: 1.03, 10: 1.05, 11: 1.06, 12: 0.92,
        },
    },
    "Tecnologia": {
        "peso": 0.18,
        "faturamento_mensal": (220_000, 1_200_000),
        "funcionarios": (15, 220),
        "clientes": (25, 80),
        "fornecedores": (15, 45),
        "margem_liquida": (0.12, 0.28),
        "sensibilidade_inflacao": 0.30,
        "sensibilidade_selic": 0.70,
        "sazonalidade": {
            1: 0.92, 2: 0.95, 3: 1.00, 4: 1.03,
            5: 1.02, 6: 1.05, 7: 1.00, 8: 1.01,
            9: 1.05, 10: 1.08, 11: 1.10, 12: 1.00,
        },
    },
    "Alimentação": {
        "peso": 0.18,
        "faturamento_mensal": (140_000, 700_000),
        "funcionarios": (10, 140),
        "clientes": (80, 160),
        "fornecedores": (30, 70),
        "margem_liquida": (0.04, 0.11),
        "sensibilidade_inflacao": 0.90,
        "sensibilidade_selic": 0.25,
        "sazonalidade": {
            1: 0.95, 2: 0.98, 3: 1.00, 4: 1.05,
            5: 1.06, 6: 1.08, 7: 1.04, 8: 1.00,
            9: 0.98, 10: 1.03, 11: 1.08, 12: 1.25,
        },
    },
    "Indústria": {
        "peso": 0.12,
        "faturamento_mensal": (350_000, 1_800_000),
        "funcionarios": (35, 350),
        "clientes": (20, 70),
        "fornecedores": (35, 90),
        "margem_liquida": (0.07, 0.16),
        "sensibilidade_inflacao": 0.85,
        "sensibilidade_selic": 0.60,
        "sazonalidade": {
            1: 0.82, 2: 0.88, 3: 0.98, 4: 1.02,
            5: 1.05, 6: 1.03, 7: 0.96, 8: 1.02,
            9: 1.04, 10: 1.06, 11: 1.02, 12: 0.84,
        },
    },
}

PERFIS_FINANCEIROS: dict[str, dict[str, Any]] = {
    "saudavel": {
        "peso": 0.50,
        "crescimento_anual": (0.05, 0.18),
        "inadimplencia": (0.01, 0.06),
        "volatilidade": (0.06, 0.12),
        "endividamento": (0.05, 0.25),
        "prob_crise": 0.06,
    },
    "atencao": {
        "peso": 0.30,
        "crescimento_anual": (-0.03, 0.06),
        "inadimplencia": (0.07, 0.16),
        "volatilidade": (0.10, 0.20),
        "endividamento": (0.20, 0.50),
        "prob_crise": 0.18,
    },
    "critico": {
        "peso": 0.20,
        "crescimento_anual": (-0.18, -0.04),
        "inadimplencia": (0.15, 0.32),
        "volatilidade": (0.18, 0.32),
        "endividamento": (0.45, 0.85),
        "prob_crise": 0.40,
    },
}

BANCOS = [
    "Banco do Brasil", "Bradesco", "Itaú", "Santander",
    "Caixa Econômica Federal", "Nubank", "Inter", "C6 Bank",
]

CATEGORIAS_ENTRADA = {
    "Varejo": ["Venda de Produtos", "Marketplace", "Venda Corporativa"],
    "Serviços": ["Contrato Mensal", "Projeto Avulso", "Consultoria"],
    "Tecnologia": ["Assinatura SaaS", "Licenciamento", "Implantação"],
    "Alimentação": ["Venda Balcão", "Delivery", "Eventos"],
    "Indústria": ["Venda de Produção", "Contrato B2B", "Exportação"],
}

CATEGORIAS_FORNECEDORES = [
    "Mercadorias", "Matéria-prima", "Logística", "Tecnologia",
    "Energia", "Serviços", "Marketing", "Manutenção",
]

FERIADOS_FIXOS = {
    (1, 1): "Confraternização Universal",
    (4, 21): "Tiradentes",
    (5, 1): "Dia do Trabalho",
    (9, 7): "Independência do Brasil",
    (10, 12): "Nossa Senhora Aparecida",
    (11, 2): "Finados",
    (11, 15): "Proclamação da República",
    (11, 20): "Consciência Negra",
    (12, 25): "Natal",
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def weighted_choice(options: dict[str, dict[str, Any]]) -> str:
    labels = list(options.keys())
    weights = [float(options[label]["peso"]) for label in labels]
    return random.choices(labels, weights=weights, k=1)[0]


def month_range(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    result: list[date] = []

    while current <= end:
        result.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return result


def random_date_between(start: date, end: date) -> date:
    if end < start:
        return start

    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def business_day_like(base_date: date, preferred_day: int) -> date:
    day = min(max(preferred_day, 1), 28)
    result = date(base_date.year, base_date.month, day)

    while result.weekday() >= 5 or is_holiday(result):
        result += timedelta(days=1)

    return result


def is_holiday(day: date) -> bool:
    return (day.month, day.day) in FERIADOS_FIXOS


def holiday_name(day: date) -> str | None:
    return FERIADOS_FIXOS.get((day.month, day.day))


def holiday_factor(setor: str, day: date) -> float:
    if not is_holiday(day):
        return 1.0

    if setor in {"Varejo", "Alimentação"}:
        return random.uniform(1.08, 1.30)

    if setor in {"Serviços", "Indústria"}:
        return random.uniform(0.70, 0.92)

    return random.uniform(0.90, 1.05)


def company_name(setor: str, index: int) -> str:
    suffixes = {
        "Varejo": ["Comércio", "Store", "Varejista", "Magazine"],
        "Serviços": ["Serviços", "Consultoria", "Soluções", "Gestão"],
        "Tecnologia": ["Tech", "Sistemas", "Digital", "Software"],
        "Alimentação": ["Alimentos", "Gastronomia", "Foods", "Restaurantes"],
        "Indústria": ["Indústria", "Manufatura", "Produção", "Industrial"],
    }

    base = fake.last_name().replace(" ", "")
    return f"{base} {random.choice(suffixes[setor])} {index:02d}"


def classify_company_size(faturamento: float) -> str:
    if faturamento < 250_000:
        return "Pequena"
    if faturamento < 800_000:
        return "Média"
    return "Grande"


def anomaly_probability(profile: str) -> float:
    return {
        "saudavel": 0.002,
        "atencao": 0.005,
        "critico": 0.012,
    }[profile]


# ============================================================
# CENÁRIO MACROECONÔMICO SINTÉTICO
# ============================================================

def generate_macro_scenario() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    base_inflation = 0.45
    base_selic = 13.75

    for month_date in month_range(START_DATE, END_DATE):
        months_from_start = (
            (month_date.year - START_DATE.year) * 12
            + month_date.month
            - START_DATE.month
        )

        inflation_cycle = 0.18 * np.sin(months_from_start / 4.5)
        inflation_noise = np.random.normal(0, 0.06)
        inflation_monthly = max(
            -0.10,
            base_inflation + inflation_cycle + inflation_noise,
        )

        if month_date.year <= 2023:
            selic = base_selic - 0.10 * months_from_start
        elif month_date.year == 2024:
            selic = 11.75 - 0.12 * (month_date.month - 1)
        elif month_date.year == 2025:
            selic = 10.50 + 0.08 * (month_date.month - 1)
        else:
            selic = 11.40 - 0.05 * (month_date.month - 1)

        selic += np.random.normal(0, 0.12)
        selic = max(6.0, min(16.0, selic))

        rows.append({
            "mes_referencia": month_date,
            "inflacao_mensal_pct": round(float(inflation_monthly), 4),
            "selic_anual_pct": round(float(selic), 4),
        })

    return pd.DataFrame(rows)


# ============================================================
# EVENTOS EXTRAORDINÁRIOS
# ============================================================

def generate_company_events(
    empresas: pd.DataFrame,
    metadata: dict[int, dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    event_id = 1

    event_types = [
        "Crise de Receita",
        "Expansão Comercial",
        "Perda de Cliente Relevante",
        "Compra de Equipamento",
        "Campanha Promocional",
        "Interrupção Operacional",
    ]

    for empresa in empresas.itertuples(index=False):
        meta = metadata[empresa.id_empresa]

        number_of_events = random.choices(
            [0, 1, 2, 3],
            weights=[0.18, 0.42, 0.28, 0.12],
            k=1,
        )[0]

        if random.random() < meta["prob_crise"]:
            number_of_events = max(number_of_events, 1)

        for _ in range(number_of_events):
            event_type = random.choice(event_types)
            start = random_date_between(START_DATE, END_DATE - timedelta(days=30))
            duration = random.randint(15, 120)
            end = min(END_DATE, start + timedelta(days=duration))

            if event_type in {"Crise de Receita", "Perda de Cliente Relevante", "Interrupção Operacional"}:
                revenue_multiplier = random.uniform(0.55, 0.88)
                expense_multiplier = random.uniform(0.95, 1.25)
            elif event_type in {"Expansão Comercial", "Campanha Promocional"}:
                revenue_multiplier = random.uniform(1.10, 1.38)
                expense_multiplier = random.uniform(1.05, 1.30)
            else:
                revenue_multiplier = random.uniform(0.95, 1.05)
                expense_multiplier = random.uniform(1.15, 1.45)

            rows.append({
                "id_evento": event_id,
                "id_empresa": empresa.id_empresa,
                "tipo_evento": event_type,
                "data_inicio": start,
                "data_fim": end,
                "multiplicador_receita": round(revenue_multiplier, 4),
                "multiplicador_despesa": round(expense_multiplier, 4),
                "descricao": f"{event_type} simulada para fins analíticos.",
            })

            event_id += 1

    return pd.DataFrame(rows)


def event_multiplier(
    events: pd.DataFrame,
    company_id: int,
    day: date,
    field: str,
) -> float:
    if events.empty:
        return 1.0

    matches = events[
        (events["id_empresa"] == company_id)
        & (events["data_inicio"] <= day)
        & (events["data_fim"] >= day)
    ]

    if matches.empty:
        return 1.0

    value = float(matches[field].prod())
    return max(0.35, min(2.0, value))


# ============================================================
# GERAÇÃO DAS TABELAS OPERACIONAIS
# ============================================================

def generate_empresas() -> tuple[pd.DataFrame, dict[int, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    metadata: dict[int, dict[str, Any]] = {}

    for company_id in range(1, NUM_EMPRESAS + 1):
        setor = weighted_choice(SETOR_CONFIG)
        perfil = weighted_choice(PERFIS_FINANCEIROS)

        setor_cfg = SETOR_CONFIG[setor]
        perfil_cfg = PERFIS_FINANCEIROS[perfil]

        revenue = round(
            random.uniform(*setor_cfg["faturamento_mensal"]),
            2,
        )
        employees = random.randint(*setor_cfg["funcionarios"])
        opening_date = random_date_between(
            date(1998, 1, 1),
            date(2021, 12, 31),
        )

        growth = random.uniform(*perfil_cfg["crescimento_anual"])
        default_rate = random.uniform(*perfil_cfg["inadimplencia"])
        volatility = random.uniform(*perfil_cfg["volatilidade"])
        debt_ratio = random.uniform(*perfil_cfg["endividamento"])
        margin = random.uniform(*setor_cfg["margem_liquida"])

        rows.append({
            "id_empresa": company_id,
            "nome_empresa": company_name(setor, company_id),
            "setor": setor,
            "porte": classify_company_size(revenue),
            "data_abertura": opening_date,
            "faturamento_medio": revenue,
            "quantidade_funcionarios": employees,
            "status": "ativa",
            "data_criacao": datetime.now(),
        })

        metadata[company_id] = {
            "setor": setor,
            "perfil": perfil,
            "faturamento_medio": revenue,
            "crescimento_anual": growth,
            "inadimplencia": default_rate,
            "volatilidade": volatility,
            "endividamento": debt_ratio,
            "margem": margin,
            "prob_crise": perfil_cfg["prob_crise"],
        }

    return pd.DataFrame(rows), metadata


def generate_contas_bancarias(
    empresas: pd.DataFrame,
    metadata: dict[int, dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    account_id = 1

    for empresa in empresas.itertuples(index=False):
        quantity = random.choices(
            [1, 2, 3],
            weights=[0.45, 0.40, 0.15],
            k=1,
        )[0]

        meta = metadata[empresa.id_empresa]
        revenue = meta["faturamento_medio"]
        profile = meta["perfil"]

        balance_factor = {
            "saudavel": (0.35, 0.90),
            "atencao": (0.12, 0.45),
            "critico": (-0.10, 0.18),
        }[profile]

        total_balance = revenue * random.uniform(*balance_factor)
        total_limit = revenue * random.uniform(0.08, 0.30)

        proportions = np.random.dirichlet(np.ones(quantity))

        for account_index, proportion in enumerate(proportions):
            rows.append({
                "id_conta": account_id,
                "id_empresa": empresa.id_empresa,
                "banco": random.choice(BANCOS),
                "tipo_conta": (
                    "Conta Corrente"
                    if account_index == 0
                    else random.choice(["Conta Corrente", "Conta Investimento"])
                ),
                "saldo_inicial": round(total_balance * float(proportion), 2),
                "limite_credito": round(total_limit * float(proportion), 2),
                "status": "ativa",
                "data_criacao": datetime.now(),
            })
            account_id += 1

    return pd.DataFrame(rows)


def generate_clientes(
    empresas: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[int, list[int]]]:
    rows: list[dict[str, Any]] = []
    company_map: dict[int, list[int]] = {}
    client_id = 1

    for empresa in empresas.itertuples(index=False):
        quantity = random.randint(*SETOR_CONFIG[empresa.setor]["clientes"])
        company_map[empresa.id_empresa] = []

        for _ in range(quantity):
            risk = random.choices(
                ["baixo", "medio", "alto"],
                weights=[0.64, 0.26, 0.10],
                k=1,
            )[0]

            credit_limit = {
                "baixo": random.uniform(20_000, 150_000),
                "medio": random.uniform(10_000, 90_000),
                "alto": random.uniform(5_000, 50_000),
            }[risk]

            rows.append({
                "id_cliente": client_id,
                "id_empresa": empresa.id_empresa,
                "nome_cliente": fake.company(),
                "segmento": random.choice(
                    ["Varejo", "Serviços", "Indústria", "Tecnologia", "Atacado"]
                ),
                "limite_credito": round(credit_limit, 2),
                "risco_cliente": risk,
                "status": "ativo",
                "data_cadastro": random_date_between(
                    max(empresa.data_abertura, date(2020, 1, 1)),
                    END_DATE,
                ),
            })

            company_map[empresa.id_empresa].append(client_id)
            client_id += 1

    return pd.DataFrame(rows), company_map


def generate_fornecedores(
    empresas: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[int, list[int]]]:
    rows: list[dict[str, Any]] = []
    company_map: dict[int, list[int]] = {}
    supplier_id = 1

    for empresa in empresas.itertuples(index=False):
        quantity = random.randint(*SETOR_CONFIG[empresa.setor]["fornecedores"])
        company_map[empresa.id_empresa] = []

        for _ in range(quantity):
            rows.append({
                "id_fornecedor": supplier_id,
                "id_empresa": empresa.id_empresa,
                "nome_fornecedor": fake.company(),
                "categoria": random.choice(CATEGORIAS_FORNECEDORES),
                "prazo_medio_pagamento": random.choice([15, 21, 30, 45, 60]),
                "status": "ativo",
                "data_cadastro": random_date_between(
                    max(empresa.data_abertura, date(2020, 1, 1)),
                    END_DATE,
                ),
            })

            company_map[empresa.id_empresa].append(supplier_id)
            supplier_id += 1

    return pd.DataFrame(rows), company_map


# ============================================================
# RECEITA, RECEBÍVEIS E ENTRADAS
# ============================================================

def generate_monthly_revenue(
    base_monthly_revenue: float,
    setor: str,
    profile: str,
    growth_rate: float,
    volatility: float,
    month_date: date,
    macro_row: pd.Series,
    events: pd.DataFrame,
    company_id: int,
) -> float:
    months_since_start = (
        (month_date.year - START_DATE.year) * 12
        + month_date.month
        - START_DATE.month
    )

    growth_factor = (1 + growth_rate) ** (months_since_start / 12)
    seasonality = SETOR_CONFIG[setor]["sazonalidade"][month_date.month]
    noise = np.random.normal(1.0, volatility)

    inflation = float(macro_row["inflacao_mensal_pct"]) / 100
    selic = float(macro_row["selic_anual_pct"]) / 100

    inflation_effect = 1 - (
        inflation * SETOR_CONFIG[setor]["sensibilidade_inflacao"]
    )
    selic_effect = 1 - (
        max(selic - 0.08, 0)
        * SETOR_CONFIG[setor]["sensibilidade_selic"]
        * 0.20
    )

    deterioration = 1.0
    if profile == "critico" and month_date >= date(2025, 1, 1):
        deterioration = max(0.55, 1 - 0.012 * months_since_start)

    event_effect = event_multiplier(
        events,
        company_id,
        month_date,
        "multiplicador_receita",
    )

    value = (
        base_monthly_revenue
        * growth_factor
        * seasonality
        * noise
        * inflation_effect
        * selic_effect
        * deterioration
        * event_effect
    )

    return max(value, base_monthly_revenue * 0.18)


def generate_transactions_and_receivables(
    empresas: pd.DataFrame,
    contas: pd.DataFrame,
    clientes: pd.DataFrame,
    client_ids: dict[int, list[int]],
    metadata: dict[int, dict[str, Any]],
    macro: pd.DataFrame,
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transaction_rows: list[dict[str, Any]] = []
    receivable_rows: list[dict[str, Any]] = []
    anomaly_rows: list[dict[str, Any]] = []

    account_map = (
        contas.groupby("id_empresa")["id_conta"]
        .apply(list)
        .to_dict()
    )
    client_risk = clientes.set_index("id_cliente")["risco_cliente"].to_dict()
    macro_map = macro.set_index("mes_referencia")

    transaction_id = 1
    receivable_id = 1
    anomaly_id = 1

    for empresa in empresas.itertuples(index=False):
        meta = metadata[empresa.id_empresa]
        accounts = account_map[empresa.id_empresa]
        company_clients = client_ids[empresa.id_empresa]

        for month_date in month_range(START_DATE, END_DATE):
            macro_row = macro_map.loc[month_date]

            monthly_revenue = generate_monthly_revenue(
                base_monthly_revenue=meta["faturamento_medio"],
                setor=meta["setor"],
                profile=meta["perfil"],
                growth_rate=meta["crescimento_anual"],
                volatility=meta["volatilidade"],
                month_date=month_date,
                macro_row=macro_row,
                events=events,
                company_id=empresa.id_empresa,
            )

            invoice_count = max(
                8,
                int(monthly_revenue / random.uniform(4_000, 15_000)),
            )

            weights = np.random.dirichlet(np.ones(invoice_count))
            invoice_values = monthly_revenue * weights

            for invoice_value in invoice_values:
                client_id = random.choice(company_clients)
                risk = client_risk[client_id]

                issue_date = random_date_between(
                    month_date,
                    min(END_DATE, month_date + timedelta(days=27)),
                )
                due_date = issue_date + timedelta(
                    days=random.choice([7, 14, 21, 30, 45, 60])
                )

                delay_probability = {
                    "baixo": 0.06,
                    "medio": 0.18,
                    "alto": 0.38,
                }[risk]

                delay_probability += meta["inadimplencia"] * 0.35
                delayed = random.random() < min(delay_probability, 0.75)

                if due_date <= END_DATE:
                    delay_days = (
                        random.randint(5, 75)
                        if delayed
                        else random.randint(-3, 3)
                    )
                    payment_date = due_date + timedelta(days=delay_days)

                    if payment_date <= END_DATE:
                        status = "paga"
                        days_late = max(0, delay_days)

                        amount = float(invoice_value)
                        is_anomaly = random.random() < anomaly_probability(meta["perfil"])

                        if is_anomaly:
                            anomaly_type = random.choice(
                                ["Recebimento Atípico", "Possível Duplicidade", "Valor Excepcional"]
                            )
                            anomaly_factor = random.uniform(2.2, 5.5)
                            amount *= anomaly_factor

                            anomaly_rows.append({
                                "id_anomalia": anomaly_id,
                                "id_empresa": empresa.id_empresa,
                                "tipo_anomalia": anomaly_type,
                                "data_evento": payment_date,
                                "valor_original": round(float(invoice_value), 2),
                                "valor_anomalo": round(amount, 2),
                                "origem": "entrada",
                                "descricao": "Anomalia sintética criada para detecção analítica.",
                            })
                            anomaly_id += 1

                        transaction_rows.append({
                            "id_transacao": transaction_id,
                            "id_empresa": empresa.id_empresa,
                            "id_conta": random.choice(accounts),
                            "data_transacao": datetime.combine(
                                payment_date,
                                datetime.min.time(),
                            ) + timedelta(hours=random.randint(8, 18)),
                            "tipo_transacao": "entrada",
                            "categoria": random.choice(
                                CATEGORIAS_ENTRADA[meta["setor"]]
                            ),
                            "descricao": f"Recebimento do cliente {client_id}",
                            "valor": round(amount, 2),
                            "status": "confirmada",
                            "data_criacao": datetime.now(),
                        })
                        transaction_id += 1
                    else:
                        payment_date = None
                        status = "vencida" if due_date < END_DATE else "aberta"
                        days_late = max(0, (END_DATE - due_date).days)
                else:
                    payment_date = None
                    status = "aberta"
                    days_late = 0

                receivable_rows.append({
                    "id_recebimento": receivable_id,
                    "id_empresa": empresa.id_empresa,
                    "id_cliente": client_id,
                    "data_emissao": issue_date,
                    "data_vencimento": due_date,
                    "data_pagamento": payment_date,
                    "valor": round(float(invoice_value), 2),
                    "status": status,
                    "dias_atraso": days_late,
                    "data_criacao": datetime.now(),
                })
                receivable_id += 1

    return (
        pd.DataFrame(transaction_rows),
        pd.DataFrame(receivable_rows),
        pd.DataFrame(anomaly_rows),
    )


# ============================================================
# DESPESAS, CONTAS A PAGAR E SAÍDAS
# ============================================================

def generate_payables_and_expense_transactions(
    empresas: pd.DataFrame,
    contas: pd.DataFrame,
    fornecedores: pd.DataFrame,
    supplier_ids: dict[int, list[int]],
    metadata: dict[int, dict[str, Any]],
    macro: pd.DataFrame,
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    payable_rows: list[dict[str, Any]] = []
    transaction_rows: list[dict[str, Any]] = []
    anomaly_rows: list[dict[str, Any]] = []

    account_map = (
        contas.groupby("id_empresa")["id_conta"]
        .apply(list)
        .to_dict()
    )
    macro_map = macro.set_index("mes_referencia")

    payment_id = 1
    transaction_id = 10_000_000
    anomaly_id = 1_000_000

    for empresa in empresas.itertuples(index=False):
        meta = metadata[empresa.id_empresa]
        accounts = account_map[empresa.id_empresa]
        suppliers = supplier_ids[empresa.id_empresa]

        expense_ratio = max(0.45, min(0.98, 1 - meta["margem"]))

        for month_date in month_range(START_DATE, END_DATE):
            macro_row = macro_map.loc[month_date]

            monthly_revenue = generate_monthly_revenue(
                base_monthly_revenue=meta["faturamento_medio"],
                setor=meta["setor"],
                profile=meta["perfil"],
                growth_rate=meta["crescimento_anual"],
                volatility=meta["volatilidade"],
                month_date=month_date,
                macro_row=macro_row,
                events=events,
                company_id=empresa.id_empresa,
            )

            inflation = float(macro_row["inflacao_mensal_pct"]) / 100
            inflation_cost_factor = 1 + (
                inflation
                * SETOR_CONFIG[meta["setor"]]["sensibilidade_inflacao"]
                * 1.6
            )
            event_expense_factor = event_multiplier(
                events,
                empresa.id_empresa,
                month_date,
                "multiplicador_despesa",
            )

            total_expenses = (
                monthly_revenue
                * expense_ratio
                * inflation_cost_factor
                * event_expense_factor
            )

            recurring_expenses = [
                ("Folha de Pagamento", 0.32),
                ("Impostos", 0.16),
                ("Aluguel", 0.08),
                ("Tecnologia", 0.05),
                ("Marketing", 0.06),
                ("Energia", 0.04),
            ]

            remaining_ratio = max(
                0,
                1 - sum(ratio for _, ratio in recurring_expenses),
            )

            variable_categories = [
                "Compra de Mercadorias",
                "Logística",
                "Serviços Terceirizados",
                "Manutenção",
            ]

            expenses = [
                (category, total_expenses * ratio)
                for category, ratio in recurring_expenses
            ]

            variable_weights = np.random.dirichlet(
                np.ones(len(variable_categories))
            )

            for category, weight in zip(variable_categories, variable_weights):
                expenses.append(
                    (
                        category,
                        total_expenses * remaining_ratio * float(weight),
                    )
                )

            for category, raw_amount in expenses:
                supplier_id = random.choice(suppliers)
                issue_date = business_day_like(
                    month_date,
                    random.randint(1, 10),
                )
                due_date = issue_date + timedelta(
                    days=random.choice([7, 15, 21, 30, 45])
                )

                delay_probability = {
                    "saudavel": 0.03,
                    "atencao": 0.10,
                    "critico": 0.24,
                }[meta["perfil"]]

                delayed = random.random() < delay_probability
                delay_days = (
                    random.randint(3, 45)
                    if delayed
                    else random.randint(-2, 2)
                )
                payment_date = due_date + timedelta(days=delay_days)

                amount = float(raw_amount)
                is_anomaly = random.random() < anomaly_probability(meta["perfil"])

                if is_anomaly:
                    anomaly_type = random.choice(
                        ["Despesa Atípica", "Possível Duplicidade", "Pagamento Excepcional"]
                    )
                    factor = random.uniform(2.0, 4.5)
                    anomalous_amount = amount * factor

                    anomaly_rows.append({
                        "id_anomalia": anomaly_id,
                        "id_empresa": empresa.id_empresa,
                        "tipo_anomalia": anomaly_type,
                        "data_evento": issue_date,
                        "valor_original": round(amount, 2),
                        "valor_anomalo": round(anomalous_amount, 2),
                        "origem": "saida",
                        "descricao": "Anomalia sintética criada para detecção analítica.",
                    })

                    amount = anomalous_amount
                    anomaly_id += 1

                if payment_date <= END_DATE:
                    status = "paga"

                    transaction_rows.append({
                        "id_transacao": transaction_id,
                        "id_empresa": empresa.id_empresa,
                        "id_conta": random.choice(accounts),
                        "data_transacao": datetime.combine(
                            payment_date,
                            datetime.min.time(),
                        ) + timedelta(hours=random.randint(8, 18)),
                        "tipo_transacao": "saida",
                        "categoria": category,
                        "descricao": f"Pagamento ao fornecedor {supplier_id}",
                        "valor": round(amount, 2),
                        "status": "confirmada",
                        "data_criacao": datetime.now(),
                    })
                    transaction_id += 1
                else:
                    payment_date = None
                    status = "vencida" if due_date < END_DATE else "aberta"

                payable_rows.append({
                    "id_pagamento": payment_id,
                    "id_empresa": empresa.id_empresa,
                    "id_fornecedor": supplier_id,
                    "data_emissao": issue_date,
                    "data_vencimento": due_date,
                    "data_pagamento": payment_date,
                    "valor": round(amount, 2),
                    "categoria": category,
                    "status": status,
                    "data_criacao": datetime.now(),
                })
                payment_id += 1

    return (
        pd.DataFrame(payable_rows),
        pd.DataFrame(transaction_rows),
        pd.DataFrame(anomaly_rows),
    )


# ============================================================
# EMPRÉSTIMOS E PARCELAS
# ============================================================

def generate_loans_and_installments(
    empresas: pd.DataFrame,
    contas: pd.DataFrame,
    metadata: dict[int, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    loan_rows: list[dict[str, Any]] = []
    payable_rows: list[dict[str, Any]] = []
    transaction_rows: list[dict[str, Any]] = []

    account_map = (
        contas.groupby("id_empresa")["id_conta"]
        .apply(list)
        .to_dict()
    )

    loan_id = 1
    payment_id = 20_000_000
    transaction_id = 20_000_000

    for empresa in empresas.itertuples(index=False):
        meta = metadata[empresa.id_empresa]

        loan_count = {
            "saudavel": random.choices([0, 1, 2], [0.45, 0.45, 0.10])[0],
            "atencao": random.choices([1, 2, 3], [0.45, 0.40, 0.15])[0],
            "critico": random.choices([1, 2, 3, 4], [0.20, 0.38, 0.30, 0.12])[0],
        }[meta["perfil"]]

        for _ in range(loan_count):
            principal = meta["faturamento_medio"] * random.uniform(
                0.20,
                max(0.35, meta["endividamento"]),
            )
            monthly_rate = random.uniform(0.85, 2.90)
            installments = random.choice([12, 18, 24, 36, 48])
            contract_date = random_date_between(date(2022, 1, 1), END_DATE)

            rate_decimal = monthly_rate / 100
            if rate_decimal > 0:
                installment_value = (
                    principal
                    * rate_decimal
                    * (1 + rate_decimal) ** installments
                    / ((1 + rate_decimal) ** installments - 1)
                )
            else:
                installment_value = principal / installments

            total_paid = 0.0
            current_due = contract_date + timedelta(days=30)

            for installment_number in range(1, installments + 1):
                due_date = current_due + timedelta(days=30 * (installment_number - 1))

                if due_date > END_DATE + timedelta(days=90):
                    break

                payment_date: date | None
                status: str

                if due_date <= END_DATE:
                    delay_probability = {
                        "saudavel": 0.02,
                        "atencao": 0.08,
                        "critico": 0.20,
                    }[meta["perfil"]]

                    delayed = random.random() < delay_probability
                    delay_days = random.randint(2, 20) if delayed else random.randint(-2, 2)
                    candidate_payment = due_date + timedelta(days=delay_days)

                    if candidate_payment <= END_DATE:
                        payment_date = candidate_payment
                        status = "paga"
                        total_paid += installment_value

                        transaction_rows.append({
                            "id_transacao": transaction_id,
                            "id_empresa": empresa.id_empresa,
                            "id_conta": random.choice(account_map[empresa.id_empresa]),
                            "data_transacao": datetime.combine(
                                payment_date,
                                datetime.min.time(),
                            ) + timedelta(hours=10),
                            "tipo_transacao": "saida",
                            "categoria": "Parcela de Empréstimo",
                            "descricao": (
                                f"Parcela {installment_number}/{installments} "
                                f"do empréstimo {loan_id}"
                            ),
                            "valor": round(installment_value, 2),
                            "status": "confirmada",
                            "data_criacao": datetime.now(),
                        })
                        transaction_id += 1
                    else:
                        payment_date = None
                        status = "vencida"
                else:
                    payment_date = None
                    status = "aberta"

                payable_rows.append({
                    "id_pagamento": payment_id,
                    "id_empresa": empresa.id_empresa,
                    "id_fornecedor": None,
                    "data_emissao": contract_date,
                    "data_vencimento": due_date,
                    "data_pagamento": payment_date,
                    "valor": round(installment_value, 2),
                    "categoria": "Parcela de Empréstimo",
                    "status": status,
                    "data_criacao": datetime.now(),
                })
                payment_id += 1

            outstanding = max(0, principal - total_paid)
            next_payment = (
                END_DATE + timedelta(days=random.randint(1, 30))
                if outstanding > 0
                else None
            )

            loan_rows.append({
                "id_emprestimo": loan_id,
                "id_empresa": empresa.id_empresa,
                "instituicao": random.choice(BANCOS),
                "valor_contratado": round(principal, 2),
                "taxa_juros": round(monthly_rate, 4),
                "quantidade_parcelas": installments,
                "valor_parcela": round(installment_value, 2),
                "saldo_devedor": round(outstanding, 2),
                "data_contratacao": contract_date,
                "data_proxima_parcela": next_payment,
                "status": "ativo" if outstanding > 0 else "quitado",
                "data_criacao": datetime.now(),
            })

            loan_id += 1

    return (
        pd.DataFrame(loan_rows),
        pd.DataFrame(payable_rows),
        pd.DataFrame(transaction_rows),
    )


# ============================================================
# VALIDAÇÃO
# ============================================================

def validate_dataframes(dataframes: dict[str, pd.DataFrame]) -> None:
    required = [
        "empresas",
        "contas_bancarias",
        "clientes",
        "fornecedores",
        "transacoes",
        "contas_receber",
        "contas_pagar",
    ]

    for table_name in required:
        if dataframes[table_name].empty:
            raise ValueError(f"A tabela {table_name} foi gerada vazia.")

    positive_value_tables = {
        "transacoes": "valor",
        "contas_receber": "valor",
        "contas_pagar": "valor",
    }

    for table_name, value_column in positive_value_tables.items():
        if (dataframes[table_name][value_column] <= 0).any():
            raise ValueError(
                f"A tabela {table_name} possui valores menores ou iguais a zero."
            )

    empresas_ids = set(dataframes["empresas"]["id_empresa"])

    for table_name in [
        "contas_bancarias",
        "clientes",
        "fornecedores",
        "transacoes",
        "contas_receber",
        "contas_pagar",
        "emprestimos",
    ]:
        if table_name in dataframes and not dataframes[table_name].empty:
            invalid = set(dataframes[table_name]["id_empresa"]) - empresas_ids
            if invalid:
                raise ValueError(
                    f"A tabela {table_name} possui empresas inexistentes: {invalid}"
                )

    if (
        dataframes["contas_receber"]["data_vencimento"]
        < dataframes["contas_receber"]["data_emissao"]
    ).any():
        raise ValueError("Há contas a receber com vencimento anterior à emissão.")

    if (
        dataframes["contas_pagar"]["data_vencimento"]
        < dataframes["contas_pagar"]["data_emissao"]
    ).any():
        raise ValueError("Há contas a pagar com vencimento anterior à emissão.")

    duplicate_keys = {
        "empresas": "id_empresa",
        "contas_bancarias": "id_conta",
        "clientes": "id_cliente",
        "fornecedores": "id_fornecedor",
        "transacoes": "id_transacao",
        "contas_receber": "id_recebimento",
        "contas_pagar": "id_pagamento",
        "emprestimos": "id_emprestimo",
    }

    for table_name, key_column in duplicate_keys.items():
        if not dataframes[table_name].empty:
            if dataframes[table_name][key_column].duplicated().any():
                raise ValueError(
                    f"A tabela {table_name} possui IDs duplicados em {key_column}."
                )


# ============================================================
# CSV E BANCO
# ============================================================

def save_csvs(dataframes: dict[str, pd.DataFrame]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for table_name, dataframe in dataframes.items():
        output_file = OUTPUT_DIR / f"{table_name}.csv"
        dataframe.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig",
        )
        print(
            f"[CSV] {table_name:<22} "
            f"{len(dataframe):>10,} linhas -> {output_file}"
        )


def load_to_postgres(
    dataframes: dict[str, pd.DataFrame],
    incremental: bool,
) -> None:
    if create_engine is None or text is None:
        raise RuntimeError(
            "SQLAlchemy não está instalado. "
            "Execute: pip install sqlalchemy psycopg2-binary"
        )

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=True)

    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "finsight")
    db_user = os.getenv("DB_USER", "finsight_user")
    db_password = os.getenv("DB_PASSWORD", "finsight_password")
    
    print("DB_HOST:", db_host)
    print("DB_PORT:", db_port)
    print("DB_NAME:", db_name)
    print("DB_USER:", db_user)
    print("DB_PASSWORD:", db_password)

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name,
    )

    engine = create_engine(database_url, future=True)

    load_order = [
        "cenario_macroeconomico",
        "empresas",
        "contas_bancarias",
        "clientes",
        "fornecedores",
        "eventos_empresariais",
        "transacoes",
        "contas_receber",
        "contas_pagar",
        "emprestimos",
        "anomalias_financeiras",
    ]

    with engine.begin() as connection:
        if not incremental:
            connection.execute(
                text(
                    """
                    TRUNCATE TABLE
                        finsight.anomalias_financeiras,
                        finsight.transacoes,
                        finsight.contas_receber,
                        finsight.contas_pagar,
                        finsight.emprestimos,
                        finsight.eventos_empresariais,
                        finsight.contas_bancarias,
                        finsight.clientes,
                        finsight.fornecedores,
                        finsight.empresas,
                        finsight.cenario_macroeconomico
                    RESTART IDENTITY CASCADE;
                    """
                )
            )

        for table_name in load_order:
            dataframe = dataframes[table_name].copy()

            if incremental:
                primary_keys = {
                    "empresas": "id_empresa",
                    "contas_bancarias": "id_conta",
                    "clientes": "id_cliente",
                    "fornecedores": "id_fornecedor",
                    "transacoes": "id_transacao",
                    "contas_receber": "id_recebimento",
                    "contas_pagar": "id_pagamento",
                    "emprestimos": "id_emprestimo",
                }

                key_column = primary_keys[table_name]
                max_id_query = text(
                    f"SELECT COALESCE(MAX({key_column}), 0) "
                    f"FROM finsight.{table_name}"
                )
                max_existing_id = int(connection.execute(max_id_query).scalar_one())
                dataframe = dataframe[dataframe[key_column] > max_existing_id]

            if dataframe.empty:
                print(f"[DB] {table_name}: nenhuma linha nova.")
                continue

            dataframe.to_sql(
                table_name,
                con=connection,
                schema="finsight",
                if_exists="append",
                index=False,
                method="multi",
                chunksize=2_000,
            )

            print(
                f"[DB] {table_name:<22} "
                f"{len(dataframe):>10,} linhas carregadas."
            )

    print("\nCarga no PostgreSQL concluída com sucesso.")


# ============================================================
# RESUMO
# ============================================================

def print_summary(dataframes: dict[str, pd.DataFrame]) -> None:
    print("\nResumo da geração")
    print("=" * 56)

    for table_name, dataframe in dataframes.items():
        print(f"{table_name:<24} {len(dataframe):>12,} linhas")

    transactions = dataframes["transacoes"]
    total_in = transactions.loc[
        transactions["tipo_transacao"] == "entrada",
        "valor",
    ].sum()
    total_out = transactions.loc[
        transactions["tipo_transacao"] == "saida",
        "valor",
    ].sum()

    print("-" * 56)
    print(f"Total de entradas: R$ {total_in:,.2f}")
    print(f"Total de saídas:   R$ {total_out:,.2f}")
    print(f"Resultado líquido: R$ {(total_in - total_out):,.2f}")


# ============================================================
# ORQUESTRAÇÃO
# ============================================================

def build_dataset() -> dict[str, pd.DataFrame]:
    macro = generate_macro_scenario()
    empresas, metadata = generate_empresas()
    eventos = generate_company_events(empresas, metadata)
    contas = generate_contas_bancarias(empresas, metadata)
    clientes, client_ids = generate_clientes(empresas)
    fornecedores, supplier_ids = generate_fornecedores(empresas)

    (
        revenue_transactions,
        receivables,
        revenue_anomalies,
    ) = generate_transactions_and_receivables(
        empresas=empresas,
        contas=contas,
        clientes=clientes,
        client_ids=client_ids,
        metadata=metadata,
        macro=macro,
        events=eventos,
    )

    (
        payables,
        expense_transactions,
        expense_anomalies,
    ) = generate_payables_and_expense_transactions(
        empresas=empresas,
        contas=contas,
        fornecedores=fornecedores,
        supplier_ids=supplier_ids,
        metadata=metadata,
        macro=macro,
        events=eventos,
    )

    (
        loans,
        loan_payables,
        loan_transactions,
    ) = generate_loans_and_installments(
        empresas=empresas,
        contas=contas,
        metadata=metadata,
    )

    transactions = pd.concat(
        [
            revenue_transactions,
            expense_transactions,
            loan_transactions,
        ],
        ignore_index=True,
    ).sort_values(
        ["id_empresa", "data_transacao", "id_transacao"]
    ).reset_index(drop=True)

    transactions["id_transacao"] = range(1, len(transactions) + 1)

    # Parcelas de empréstimos não possuem fornecedor real.
    # Para manter compatibilidade com a FK atual de contas_pagar,
    # elas são mantidas em CSV separado e não anexadas à tabela operacional.
    payables = payables.reset_index(drop=True)

    anomalies = pd.concat(
        [revenue_anomalies, expense_anomalies],
        ignore_index=True,
    )

    dataframes = {
        "empresas": empresas,
        "contas_bancarias": contas,
        "clientes": clientes,
        "fornecedores": fornecedores,
        "transacoes": transactions,
        "contas_receber": receivables,
        "contas_pagar": payables,
        "emprestimos": loans,
        "cenario_macroeconomico": macro,
        "eventos_empresariais": eventos,
        "anomalias_financeiras": anomalies,
        "parcelas_emprestimos": loan_payables,
    }

    validate_dataframes(dataframes)
    return dataframes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera dados sintéticos avançados para o FinSight AI."
    )

    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Carrega as oito tabelas operacionais no PostgreSQL.",
    )

    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Carrega somente IDs maiores que os existentes no banco.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("Iniciando geração avançada de dados sintéticos...\n")

    dataframes = build_dataset()
    save_csvs(dataframes)
    print_summary(dataframes)

    if args.load_db:
        load_to_postgres(
            dataframes,
            incremental=args.incremental,
        )
    else:
        print(
            "\nCSVs gerados com sucesso.\n"
            "Para carregar no PostgreSQL:\n"
            "python src/04_generate_synthetic_data_advanced.py --load-db"
        )


if __name__ == "__main__":
    main()
