# Confirmação de compras

## Fluxo

Uma lista comum (não modelo) pode ser convertida em uma compra pela ação **Confirmar compra**. O usuário escolhe uma conta ativa em BRL. A API exige pelo menos um item e preço unitário preenchido em todos os itens.

O total é calculado com aritmética decimal: soma de quantidade × preço unitário. A confirmação cria uma única movimentação do tipo despesa, marca os itens como comprados, arquiva a lista e registra observações de preço e entradas no estoque para cada item vinculado a um produto do catálogo.

## Integridade e segurança

- A lista, a conta, a categoria opcional e os produtos pertencem ao usuário autenticado.
- Apenas contas ativas em BRL são aceitas; não há conversão cambial implícita.
- A categoria, quando informada, precisa ser uma categoria ativa do tipo despesa.
- A chave de idempotência é determinística por lista (`shopping-purchase:{list_id}`), impedindo uma segunda despesa para a mesma lista.
- A movimentação, as observações de preço, a marcação dos itens e o arquivamento são persistidos na mesma transação de banco.
- Uma falha de integridade provoca rollback integral.
- O endpoint não grava nem sincroniza dados em Neon por conta própria.

## Limitações desta etapa

- Todos os itens precisam ter preço informado; itens sem preço não são estimados silenciosamente.
- O método de pagamento/cartão ainda não é tratado como fatura. A conta escolhida representa a conta financeira de saída.
- O estoque doméstico usa um ledger próprio; veja [Estoque doméstico](HOUSEHOLD_STOCK.md). Baixa de estoque por consumo e ajustes já estão disponíveis; estorno/reabertura de compra ainda exige fluxo próprio.
- A confirmação não importa notas fiscais automaticamente.
