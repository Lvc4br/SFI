# Investimentos

Cadastro pessoal de ativos e livro de operações de compra, venda, dividendos, taxas e impostos. A carteira é calculada pelo histórico usando Decimal e custo médio ponderado. Vendas reduzem o custo proporcional e calculam resultado realizado; dividendos aparecem separadamente.

## Limites e semântica
- Não há integração com corretoras, custódia, cotações ou preços em tempo real.
- Operações são informativas e não movimentam contas bancárias; não comprovam liquidação financeira.
- Resultado realizado não inclui dividendos.
- Custo remanescente e preço médio não representam cotação de mercado nem rentabilidade total.
- Não há recomendação de investimento nem cálculo tributário.

## API
- POST /api/v1/investments/assets
- GET /api/v1/investments/assets
- POST /api/v1/investments/assets/{id}/operations
- GET /api/v1/investments/assets/{id}/operations
- GET /api/v1/investments/portfolio

Compra/venda exigem quantidade, preço unitário e valor total consistente. Venda acima da posição é rejeitada. Chave de idempotência única por usuário.
