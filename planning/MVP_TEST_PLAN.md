# Plano de Testes — MVP Web

## 1. Camadas

- **Unitário:** fórmulas, regras de período, formatação, validação e componentes isolados.
- **Integração API/banco:** persistência, autorização, transações atômicas, idempotência e migrations.
- **Contrato:** cliente Web alinhado ao OpenAPI e schemas reais.
- **E2E:** jornadas completas no navegador com banco de teste.
- **Segurança:** isolamento entre usuários, sessão, validação de entrada e exposição de segredos.
- **Acessibilidade:** teclado, foco, labels, mensagens e leitores de tela quando possível.

## 2. Casos financeiros obrigatórios

1. Receita aumenta o saldo da conta compatível.
2. Despesa reduz o saldo da conta compatível.
3. Transferência debita e credita contas pelo mesmo valor, sem alterar resultado consolidado.
4. Estorno preserva original e compensa corretamente.
5. Repetição idempotente não duplica operação.
6. Orçamento soma somente despesas elegíveis.
7. Estorno é refletido conforme regra temporal documentada.
8. Recorrência futura não altera saldo realizado.
9. Moedas distintas não são somadas sem conversão.
10. Decimal preserva precisão em cálculos e persistência.
11. Períodos respeitam timezone e limites inclusivos/exclusivos definidos.
12. Valores zero, limites e arredondamentos são tratados.

## 3. Segurança e autorização

- Usuário A não lista, lê, altera ou estorna registros de B.
- IDs forjados não permitem acessar contas/categorias de terceiros.
- Rotas privadas não exibem cache de sessão anterior.
- Refresh/logout revogam sessão conforme contrato.
- Tokens não aparecem em logs, mensagens de erro ou armazenamento inseguro.
- Dados externos e textos são exibidos com escape apropriado.

## 4. Web e UX

- Cadastro e login com validação e feedback.
- Sessão expirada e API indisponível.
- Listas vazias e carregamento.
- Erro ao salvar sem perda indevida do formulário.
- Duplo clique/submissão repetida.
- Filtros sem resultados e paginação.
- Responsividade em largura móvel e desktop.
- Navegação por teclado e foco visível.

## 5. E2E principal

1. Criar usuário de teste.
2. Entrar.
3. Criar ou selecionar conta.
4. Criar ou selecionar categoria de receita/despesa.
5. Registrar receita.
6. Registrar despesa.
7. Criar transferência entre duas contas.
8. Criar orçamento mensal.
9. Conferir histórico, saldos, resumo e orçamento.
10. Estornar movimentação de teste e conferir trilha.
11. Sair e confirmar bloqueio da área privada.

Os testes E2E devem usar banco isolado, credenciais efêmeras e limpeza segura; nunca apontar para o Neon de produção por padrão.

## 6. Gates de CI
- Instalação reprodutível via lockfile.
- Testes API.
- Lint/format conforme ferramentas configuradas.
- Typecheck Web.
- Build Web.
- Testes E2E em ambiente isolado quando disponíveis.
- Verificação de dependências/segredos conforme pipeline existente.

## 7. Bloqueadores
Qualquer acesso cruzado, perda/duplicação de dinheiro, divergência de cálculo, sessão que permita acesso após revogação, segredo exposto ou migração destrutiva bloqueia release.


## 8. Segurança da cadeia de dependências

- O CI executa auditoria de dependências Python e Web; não ignorar findings sem justificativa documentada.
- Pytest deve permanecer em versão corrigida (>= 9.0.3) após finding PYSEC-2026-1845 em 8.4.2.
- CodeQL analisa Python e JavaScript/TypeScript em PRs e execução semanal.
