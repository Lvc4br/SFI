# Fase 2.6 — estorno pareado de transferências

## Objetivo

Permitir desfazer uma transferência interna sem deixar apenas uma das contas compensada. O estorno é registrado como um evento próprio e cria duas movimentações compensatórias em uma única transação de banco de dados.

## Endpoint

```http
POST /api/v1/finance/transfers/{transfer_id}/reverse?idempotency_key=<unique-key>
Authorization: Bearer <access_token>
```

A resposta inclui o identificador do estorno e as duas movimentações compensatórias.

## Regras

- A conta de origem recebe uma movimentação de receita.
- A conta de destino recebe uma movimentação de despesa.
- Os valores e a moeda correspondem exatamente à transferência original.
- A criação do registro de estorno e das duas movimentações é atômica.
- Uma transferência só pode ser estornada uma vez.
- As pernas originais e compensatórias não podem ser estornadas individualmente.
- A chave de idempotência é única por usuário.
- O histórico de transferências informa se houve estorno, seu identificador e a data.

## Integridade

- A migration `0006_transfer_reversals` cria o registro próprio de estorno e a referência nas movimentações.
- Constraints garantem ownership e no máximo um estorno por transferência.
- Se as duas movimentações originais não corresponderem ao registro da transferência, o estorno é recusado.
- Nenhuma movimentação existente é editada ou excluída.
- Nenhum banco externo ou conta bancária é movimentado.
