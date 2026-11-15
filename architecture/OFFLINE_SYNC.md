# Persistência Local e Sincronização Opcional — SFI

## Objetivo
O SFI funciona offline nas funcionalidades essenciais. Persistência local é a fonte de verdade; sincronização remota é uma opção ativada conscientemente.

## Armazenamento
SQLite no diretório privado do aplicativo; originais/anexos em armazenamento local gerenciado; FK, transações, WAL/busy_timeout quando adequados e migrations versionadas. Dados financeiros não dependem de IndexedDB ou API hospedada.

## Operação offline
Dashboard, contas, categorias, movimentações, transferências, estornos, orçamentos, listas, documentos importados, patrimônio, relatórios e exportações locais devem continuar disponíveis sem internet. Cotação, IA externa e sync mostram indisponibilidade e data do último cache sem bloquear o restante.

## Sync futuro
Sync desligado por padrão. Cada instalação tem device_id/cursor. Alterações geram IDs estáveis e outbox idempotente. Servidor valida schema/autorização/integridade. Conflitos são explícitos; não usar last-write-wins em dados financeiros. Operações rejeitadas permanecem auditáveis. Revogação impede novos envios.

## Limites
Neon não é necessário para iniciar, registrar ou consultar dados locais. Sync não substitui banco local. Documentos/dados sensíveis não são enviados sem configuração e consentimento.
