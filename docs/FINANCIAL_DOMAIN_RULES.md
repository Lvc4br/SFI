# Regras do Domínio Financeiro — MVP

Este documento define semânticas que devem ser consistentes na API, banco, interface, relatórios e conteúdo educacional.

## 1. Vocabulário

- **Conta:** local lógico onde um saldo ou obrigação é acompanhado.
- **Movimentação:** evento financeiro registrado em uma conta.
- **Receita:** entrada classificada como receita para o usuário.
- **Despesa:** saída classificada como consumo, serviço, obrigação ou outro gasto.
- **Transferência própria:** deslocamento entre duas contas do mesmo usuário.
- **Saldo de conta:** posição calculada da conta em um instante, segundo o conjunto de lançamentos e regras aplicáveis.
- **Fluxo de caixa:** entradas e saídas em um intervalo de tempo.
- **Resultado do período:** receitas menos despesas reconhecidas no período, excluindo transferências próprias.
- **Orçamento:** plano/limite para gastos de um período; não é saldo bancário.
- **Projeção:** estimativa futura baseada em regras e eventos conhecidos; não é movimentação realizada.

## 2. Tipos de conta e interpretação

A implementação atual deve ser verificada antes de ampliar tipos. No mínimo, a interface deve evitar tratar conta de crédito como dinheiro disponível.

- Contas de depósito/pagamento e dinheiro: representam recursos.
- Conta de crédito: representa obrigação/uso de crédito, não renda.
- Limite disponível de crédito não compõe saldo positivo.
- Contas em moedas diferentes são exibidas separadamente até que exista conversão explícita.

Não inferir patrimônio líquido apenas somando saldos de contas sem modelar ativos e passivos de forma completa.

## 3. Regras de movimentação

- Valor deve ser positivo; o tipo determina o sentido econômico.
- Uma receita aumenta o saldo da conta compatível.
- Uma despesa reduz o saldo da conta compatível.
- Categoria de receita só pode classificar receita; categoria de despesa só pode classificar despesa.
- Data/hora deve ser interpretada com timezone definido e armazenada de forma consistente.
- Descrição deve ser preservada e apresentada com escape seguro.
- Requisições repetidas não podem criar lançamentos duplicados.
- A API deve validar a propriedade da conta e categoria em toda operação.

## 4. Transferências

Uma transferência própria:
- Debita a conta de origem e credita a conta de destino pelo mesmo valor e moeda.
- Deve ser atômica: ambas as pernas existem ou nenhuma existe.
- Não altera receitas, despesas ou resultado consolidado.
- Não pode ligar contas de usuários diferentes.
- Não pode misturar moedas sem um fluxo cambial explícito.
- Deve ter idempotência no nível da operação de transferência.
- Estorno deve compensar ambas as pernas, com vínculo auditável à transferência original.

A interface deve agrupar as duas pernas como uma única transferência e não exibi-las como receita e despesa comuns nos indicadores consolidados.

## 5. Estornos e correções

- Lançamentos confirmados são imutáveis.
- Estorno cria lançamento compensatório vinculado ao original.
- Um lançamento não pode ser estornado mais de uma vez.
- Estorno de transferência ocorre pelo fluxo específico e compensa as duas pernas.
- Não apagar trilha histórica para corrigir erro.
- A interface deve mostrar claramente o lançamento original e seu estorno.

## 6. Orçamentos

Para uma categoria e período:
- **Realizado:** soma das despesas confirmadas elegíveis no período.
- **Restante:** limite menos realizado; pode ser negativo.
- **Uso percentual:** realizado / limite × 100.
- Limite zero deve ser tratado explicitamente, sem divisão por zero.
- Estornos reduzem o realizado conforme a data/regra de reconhecimento adotada e documentada.
- Transferências e projeções não entram como despesas realizadas.
- O sistema deve indicar quando não há orçamento cadastrado; ausência não significa orçamento ilimitado.

## 7. Recorrências e projeções

- Regra recorrente descreve uma ocorrência esperada.
- Ocorrência projetada não altera saldo realizado.
- Somente confirmação/geração explícita cria movimentação real.
- Cancelamentos, pausas e alterações de regra devem preservar o histórico.
- Dashboard deve separar realizado, previsto e combinado.

## 8. Precisão e apresentação

- Python: Decimal; PostgreSQL: NUMERIC com precisão e escala definidas.
- Nunca converter valor monetário para float em cálculos de domínio.
- Arredondamento deve ser explícito no limite de apresentação ou regra de negócio.
- Persistir moeda junto ao valor.
- Formatação brasileira (ex.: R$ 1.234,56) é apresentação, não representação de cálculo.
- Testar valores zero, pequenos, grandes, arredondamento e limites de precisão.

## 9. Métricas e fórmulas do MVP

Para um período e moeda:
- Receitas realizadas = soma das movimentações do tipo receita elegíveis.
- Despesas realizadas = soma das movimentações do tipo despesa elegíveis.
- Resultado = receitas realizadas − despesas realizadas.
- Fluxo líquido de caixa = entradas externas − saídas externas; transferências próprias são neutras no consolidado.
- Saldo por conta = saldo inicial definido + entradas − saídas, respeitando o modelo de conta e os lançamentos.
- Orçamento restante = limite − despesas realizadas elegíveis.
- Projeção de fechamento = realizado até a data + projeções futuras identificadas, nunca rotulada como resultado realizado.

A fórmula de saldo inicial precisa corresponder ao modelo efetivamente implementado. Não criar saldo inicial implícito sem requisito, validação e trilha.

## 10. Casos que exigem decisão de produto antes de implementação

- Datas de competência versus datas de pagamento.
- Saldo inicial e ajuste de saldo.
- Estorno contabilizado no período atual ou no período original.
- Despesas parceladas e faturas de cartão.
- Reembolsos e devoluções.
- Contas com saldo negativo e cheque especial.
- Conversão cambial e taxas.
- Transferência entre contas do mesmo usuário com titulares/contas externas.

Até essas decisões serem implementadas, a interface deve declarar limites e não simular suporte.
