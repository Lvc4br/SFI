# Cartões de crédito e faturas

A migration 0018 adiciona cartões vinculados a contas do tipo `credit`, ciclos mensais, parcelas e pagamentos idempotentes.

## Regras
- Um cartão usa uma conta de crédito exclusiva, em BRL. A conta é o saldo devedor contábil.
- Dia de fechamento e vencimento são configuráveis de 1 a 31; meses curtos usam o último dia disponível.
- Compra após o fechamento entra no ciclo seguinte. Parcelas são distribuídas por ciclos consecutivos e os centavos residuais são alocados às primeiras parcelas, preservando o total.
- Cada parcela cria uma despesa na conta de crédito e aparece na fatura correspondente.
- Pagamento parcial ou total cria despesa na conta de origem e entrada compensatória na conta de crédito, na mesma transação de banco de dados.
- A liquidação movimenta saldo entre contas, mas não é contabilizada como nova receita ou despesa no fluxo de caixa; somente as parcelas da compra entram nas despesas.
- A data contábil de cada parcela é ancorada à meia-noite no fuso horário do usuário para manter a competência correta nos relatórios.
- Pagamentos excedentes, conta de crédito como origem, moedas não suportadas e chaves repetidas são rejeitados.
- Os dados são isolados por usuário. Não há integração bancária ou captura automática de compras.

## API
- `POST /api/v1/credit/cards`, `GET /api/v1/credit/cards`
- `POST /api/v1/credit/purchases`
- `GET /api/v1/credit/invoices?card_id=...`
- `POST /api/v1/credit/invoices/{id}/close`
- `POST /api/v1/credit/invoices/{id}/payments`

A criação de compra usa `idempotency_key`; o mesmo identificador gera um UUID determinístico por usuário e impede duplicação. Pagamentos têm chave única por usuário. Fechar fatura é uma operação manual nesta versão; a data de fechamento é calculada e armazenada, mas não há job automático.


## Interface
A tela **Cartões** está integrada à navegação do aplicativo. Ela permite cadastrar cartão e conta de crédito vinculada, registrar compra à vista ou parcelada, consultar faturas por cartão, fechar uma fatura manualmente e registrar pagamentos parciais ou totais a partir de uma conta não crédito em BRL.

A interface não armazena número completo, CVV ou dados de autenticação do cartão. Apenas o identificador interno da conta, nome e parâmetros de ciclo são usados pelo SFI.
