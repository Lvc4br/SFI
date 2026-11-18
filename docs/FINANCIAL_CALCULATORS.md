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


## CET estimado por fluxo de caixa

POST /api/v1/calculators/cet-estimate recebe crédito bruto, custos descontados na liberação, valor da parcela, encargos mensais, número de parcelas, data de contratação e primeiro vencimento. Resolve a taxa interna efetiva anual a partir dos fluxos do tomador, usando dias reais/365 e datas mensais ajustadas ao calendário. A interface apresenta a taxa mensal equivalente e o cronograma considerado.

O resultado é uma estimativa baseada nos dados informados pelo usuário. Não substitui o CET oficial da instituição, não consulta contrato, IOF, seguros ou tarifas automaticamente e não valida conformidade regulatória. Encargos variáveis devem ser incluídos nos pagamentos informados.

## Encargos por atraso

POST /api/v1/calculators/late-payment-estimate recebe principal, vencimento, data prevista de pagamento, multa, juros mensais, método simples/composto e fator de correção informado manualmente. Calcula dias de atraso, principal corrigido, multa única, juros proporcionais a períodos de 30 dias e total estimado. Não consulta índices nem decide se percentuais são legalmente aplicáveis; informe somente condições do contrato e legislação pertinente.
