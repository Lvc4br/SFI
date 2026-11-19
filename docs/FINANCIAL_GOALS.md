# Metas financeiras e reservas

A migration `0020_financial_goals` adiciona metas pessoais e um livro-razão de alocações.

## Modelo

- `financial_goals`: nome, descrição, moeda, valor-alvo, saldo alocado, data desejada e estado.
- `goal_entries`: movimentos imutáveis de aporte ou retirada, valor, descrição, data e chave de idempotência.
- Valores persistidos em `Numeric(18,2)`; nenhum cálculo monetário usa ponto flutuante.
- Chaves estrangeiras compostas impedem que uma entrada seja associada a uma meta de outra pessoa.
- A meta é marcada como concluída quando o valor alocado alcança o alvo; uma retirada pode reabri-la.

## API autenticada

| Método | Rota | Uso |
|---|---|---|
| POST | `/api/v1/goals` | Criar meta |
| GET | `/api/v1/goals` | Listar metas |
| GET | `/api/v1/goals?include_archived=true` | Incluir arquivadas |
| GET | `/api/v1/goals/{id}` | Consultar meta |
| PATCH | `/api/v1/goals/{id}` | Alterar nome, descrição, alvo, data ou estado |
| GET | `/api/v1/goals/{id}/entries` | Histórico |
| POST | `/api/v1/goals/{id}/entries` | Registrar aporte/retirada |

Os movimentos exigem data com fuso horário e chave de idempotência de 16 a 100 caracteres. Retiradas acima do saldo são rejeitadas. Metas arquivadas são somente leitura.

## Semântica contábil importante

Aporte e retirada são **alocações internas de planejamento**, não movimentações bancárias. Não alteram saldos de contas, não criam receitas/despesas e não representam prova de que o dinheiro está separado em uma conta ou aplicação real. A tela explica essa distinção. Para representar transferência bancária real, use a funcionalidade de transferência entre contas e registre a alocação na meta separadamente.

A funcionalidade não calcula rentabilidade, juros compostos, inflação, impostos ou recomendação de investimento. A meta mede o montante nominal informado pelo usuário.

## Interface

A página Metas permite criar objetivos, acompanhar progresso, pausar/retomar/arquivar, registrar aportes e retiradas e consultar histórico. A lista não inclui metas arquivadas por padrão.

## Testes

`services/api/tests/test_goals.py` cobre criação, conclusão automática, reabertura após retirada, histórico, idempotência, validação de saldo, atualização, arquivamento e isolamento entre usuários. A suíte de migração SQLite também verifica a revisão 0020.
