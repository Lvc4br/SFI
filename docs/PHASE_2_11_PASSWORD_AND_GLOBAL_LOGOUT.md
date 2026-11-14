# Fase 2.11 — Alteração de senha e encerramento global de sessões

## Objetivo
Permitir que o usuário altere sua senha autenticado e encerre todas as sessões de sua conta.

## Implementação
- Adiciona `users.token_version`, incrementado em operações de invalidação global.
- JWTs passam a carregar a claim obrigatória `ver`.
- A dependência central compara a versão do token com a versão atual do usuário.
- `POST /api/v1/auth/change-password` exige senha atual e nova senha com pelo menos 12 caracteres.
- A alteração de senha incrementa a versão e revoga todos os refresh tokens ativos.
- `POST /api/v1/auth/logout-all` encerra todas as sessões e invalida imediatamente todos os access tokens anteriores.
- Migration Alembic `0009_user_token_version`.

## Compatibilidade e segurança
- JWTs emitidos antes desta mudança não contêm `ver` e serão rejeitados após a implantação; usuários precisarão autenticar novamente.
- O access token usado na alteração de senha ou logout global também fica inválido imediatamente.
- Senhas nunca são armazenadas em texto puro.
- A migration foi criada, não aplicada ao banco.
- Recuperação de senha por e-mail e verificação de e-mail permanecem pendentes de infraestrutura de envio de mensagens.
