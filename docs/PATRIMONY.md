# Patrimônio pessoal

Cadastro de bens e passivos com avaliações datadas. O patrimônio líquido é calculado por moeda como ativos menos passivos, utilizando para cada item a avaliação mais recente até a data consultada.

## Tipos
- Bens: imóveis, veículos, dinheiro, valores a receber, investimentos e outros.
- Passivos: empréstimos, financiamentos, cartões, tributos e outros.
- Avaliações aceitam zero e valores positivos, moeda do item, data com fuso horário e chave de idempotência.

## API
- POST /api/v1/patrimony — cadastrar bem/passivo.
- GET /api/v1/patrimony — listar itens.
- PATCH /api/v1/patrimony/{id} — arquivar/reativar.
- POST /api/v1/patrimony/{id}/valuations — registrar avaliação.
- GET /api/v1/patrimony/{id}/valuations — histórico do item.
- GET /api/v1/patrimony/summary?as_of=YYYY-MM-DD — posição consolidada por moeda.
- GET /api/v1/patrimony/history — evolução em datas de avaliação.

## Semântica e limites
- Moedas diferentes não são somadas nem convertidas; não há taxa cambial implícita.
- A avaliação é informada manualmente e não representa cotação oficial, laudo, preço de venda garantido ou saldo bancário.
- O módulo não duplica automaticamente dívidas, investimentos ou contas existentes. O usuário deve cadastrar e manter esses itens sem duplicar posições.
- Arquivar remove o item dos resumos atuais e históricos recalculados; preserve o histórico bruto para auditoria.
- Não há integração automática com cartórios, bancos, corretoras, registradoras ou bureaus de crédito.
