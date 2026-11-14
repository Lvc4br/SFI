# Fase 2.5 — recorrências e projeção de fluxo de caixa

## Objetivo

Cadastrar compromissos e receitas recorrentes como regras de previsão, sem criar movimentações reais automaticamente.

## Endpoints

- `POST /api/v1/finance/recurrences`: cria uma regra semanal, mensal ou anual.
- `GET /api/v1/finance/recurrences?active_only=true`: consulta regras do usuário.
- `PATCH /api/v1/finance/recurrences/{id}`: pausa ou reativa a regra com `{"is_active": false|true}`.
- `GET /api/v1/finance/cash-flow/forecast?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`: retorna ocorrências previstas e totais por moeda.

## Regras de calendário

- A recorrência mantém o dia original como referência.
- Meses sem esse dia usam o último dia do mês (ex.: dia 31 -> 28/29 em fevereiro e volta a 31 no mês seguinte).
- Recorrências anuais de 29 de fevereiro usam 28 de fevereiro em anos não bissextos.
- A data final é inclusiva.
- O horizonte máximo de projeção é 367 dias e há limite de 5.000 ocorrências por regra.

## Integridade financeira

- Previsões não são lançamentos reais: não alteram saldo, orçamento ou histórico.
- Nenhuma execução automática ou movimentação bancária é realizada.
- Valores usam Decimal/Numeric.
- As regras e consultas são isoladas pelo usuário autenticado.
- A migration `0005_recurrences` é adicionada, mas não aplicada a nenhum banco neste PR.
