# Dívidas, empréstimos e financiamentos

A migration `0019_debts_and_payments` adiciona cadastro de obrigações e um livro-razão de pagamentos.

## Cadastro
- Credor, tipo, descrição, moeda, valor original e saldo principal em aberto.
- Taxa anual informativa, método declarado (`manual`, `price` ou `sac`), data de contratação, primeiro vencimento e quantidade de parcelas opcional.
- O saldo principal inicial assume o valor original quando não informado.
- `GET /api/v1/debts/{id}/schedule` gera projeção Price/SAC sem gravar pagamentos ou alterar o saldo. Usa taxa anual nominal dividida por 12, principal em aberto e quantidade de parcelas cadastrada; arredonda cada parcela para centavos e ajusta a última amortização para zerar o saldo.

## Pagamentos
- Cada pagamento informa separadamente amortização de principal e juros; a soma é a saída efetiva de caixa.
- A API cria a despesa na conta de origem e registra o pagamento na mesma transação de banco.
- A amortização reduz o saldo principal; juros não reduzem principal.
- A chave de idempotência é única por usuário. O pagamento e a despesa não podem ser duplicados.
- O pagamento precisa usar uma conta ativa, não crédito, e da mesma moeda da dívida.
- O saldo não pode ficar negativo. A dívida passa para `paid` ao zerar o principal.
- Dados são isolados por usuário e datas de pagamento precisam conter fuso horário.

## Limites conhecidos
- A projeção não é proposta de quitação nem cronograma contratual oficial. Não inclui CET, seguros, tarifas, impostos, multas, mora, indexadores ou refinanciamento.
- O SFI não consulta credores nem captura boletos. Compare a projeção com o contrato e o demonstrativo do credor; não altere pagamentos confirmados para ajustar divergências.
