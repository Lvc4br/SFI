# Dívidas, empréstimos e financiamentos

A migration `0019_debts_and_payments` adiciona cadastro de obrigações e um livro-razão de pagamentos.

## Cadastro
- Credor, tipo, descrição, moeda, valor original e saldo principal em aberto.
- Taxa anual informativa, método declarado (`manual`, `price` ou `sac`), data de contratação, primeiro vencimento e quantidade de parcelas opcional.
- O saldo principal inicial assume o valor original quando não informado.
- O módulo não presume cronograma contratual nem calcula encargos automaticamente. O método e a taxa são metadados até a implementação e validação de um cronograma completo.

## Pagamentos
- Cada pagamento informa separadamente amortização de principal e juros; a soma é a saída efetiva de caixa.
- A API cria a despesa na conta de origem e registra o pagamento na mesma transação de banco.
- A amortização reduz o saldo principal; juros não reduzem principal.
- A chave de idempotência é única por usuário. O pagamento e a despesa não podem ser duplicados.
- O pagamento precisa usar uma conta ativa, não crédito, e da mesma moeda da dívida.
- O saldo não pode ficar negativo. A dívida passa para `paid` ao zerar o principal.
- Dados são isolados por usuário e datas de pagamento precisam conter fuso horário.

## Limites conhecidos
- Não há conexão com credores, captura de boletos, cálculo de CET, multas, mora, refinanciamento ou geração automática de parcelas.
- Price/SAC são armazenados como método informado, não como cronograma calculado. Não use o saldo calculado pelo SFI como quitação oficial; confira o demonstrativo do credor.
