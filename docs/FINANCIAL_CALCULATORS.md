# Calculadoras financeiras determinísticas

As rotas /api/v1/calculators/* fornecem projeções sem gravar movimentações, alterar contas ou criar obrigações.

## Juros compostos
POST /api/v1/calculators/compound-interest aceita principal, aporte mensal, taxa anual nominal percentual e prazo em meses. A taxa nominal é dividida por 12 e os aportes ocorrem no fim de cada mês.

## Price e SAC
POST /api/v1/calculators/loan-schedule recebe principal, taxa anual nominal, quantidade de parcelas, primeiro vencimento e método. Retorna o cronograma completo com saldo inicial/final, amortização, juros e prestação.

## Rentabilidade real
POST /api/v1/calculators/real-return calcula ((1 + retorno nominal) / (1 + inflação) - 1) × 100.

## Taxas equivalentes
POST /api/v1/calculators/equivalent-rate converte taxa nominal anual em taxa efetiva anual para uma frequência de capitalização.

## Limites e avisos
- Usa Decimal e arredondamento HALF_UP para centavos.
- Prazo máximo: 1.200 meses em juros compostos e 600 parcelas em cronogramas.
- Os resultados são estimativas matemáticas; não substituem CET, contrato, tributos, tarifas, seguros, indexadores ou aconselhamento profissional.
- Nenhuma rota altera dados financeiros do usuário.
