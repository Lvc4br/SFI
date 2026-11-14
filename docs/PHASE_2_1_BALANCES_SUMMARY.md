# Fase 2.1 — saldos calculados e resumo financeiro

## Entrega

- Saldo de cada conta calculado a partir do saldo inicial e do histórico imutável de movimentações.
- Resumo por período com receitas, despesas e fluxo líquido separados por moeda.
- Despesas por categoria e moeda.
- Isolamento por usuário em todas as consultas.
- Sem novas tabelas ou migrações: os valores são derivados das movimentações existentes.

## Semântica de saldo

- Contas corrente, poupança e dinheiro: saldo inicial + receitas - despesas.
- Contas de crédito: saldo inicial + despesas - receitas, exibido como `credit_used` (crédito utilizado), nunca somado ao saldo disponível em dinheiro.
- Ainda não existe cálculo de limite disponível, fatura, pagamento de cartão ou consolidação entre moedas.
- Totais do período são apresentados por moeda; não se somam BRL, USD ou outras moedas em um único número.

## API

- `GET /api/v1/finance/accounts/{account_id}/balance`
- `GET /api/v1/finance/summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

O resumo aceita até 367 dias, usa intervalo inclusivo de datas e considera datas de movimentação com fuso horário. Sem período explícito, usa o mês atual.

## Limites

Os saldos são derivados em tempo de consulta. Transferências, estornos, conciliação, orçamento e dashboard visual permanecem em etapas futuras.
