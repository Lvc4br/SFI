# Fase 2.3 — transferências e estornos auditáveis

## Transferências
- POST /api/v1/finance/transfers registra transferência entre duas contas do mesmo usuário.
- Uma operação cria o registro de transferência e duas movimentações vinculadas: saída e entrada.
- As gravações são atômicas na mesma transação do banco.
- A transferência não cria renda ou despesa econômica líquida: os dois lados se compensam.
- As contas devem pertencer ao usuário e usar a mesma moeda.
- Contas de crédito não são aceitas nesta versão.
- A chave de idempotência é única por usuário.

## Estornos
- POST /api/v1/finance/transactions/{transaction_id}/reverse?idempotency_key=... cria uma movimentação compensatória.
- A movimentação original permanece imutável.
- O estorno tem o mesmo valor, tipo oposto e referência à movimentação original.
- Só é permitido um estorno por movimentação.
- Movimentações vinculadas a transferências não podem ser estornadas individualmente.
- Estornos de transferências exigem um fluxo pareado, planejado para uma próxima etapa.

## Limitações
- Não há transferências entre moedas diferentes.
- Não há transferências envolvendo cartões de crédito.
- Não há edição ou exclusão de movimentações.
- A data do estorno é o momento da compensação, sem reescrever o passado.
- A migração 0004_transfers_reversals não é aplicada automaticamente e não foi executada no Neon.
