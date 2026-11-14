# Sincronização Offline — SFI

## Objetivo

Permitir consulta e registros offline limitados, sincronizando com o backend sem duplicar ou perder operações.

## Armazenamento local

- Web/Desktop: IndexedDB.
- Mobile: persistência local transacional apropriada à plataforma.
- Dados locais devem ser minimizados, protegidos e removíveis no logout/revogação do dispositivo.

## Protocolo

1. Cada dispositivo possui device_id e cursor de sincronização.
2. Operações locais recebem UUID e chave de idempotência.
3. Cliente envia lotes ordenados com versão/base_version.
4. Servidor valida identidade, autorização, schema e idempotência.
5. Servidor confirma operações aceitas e devolve cursor/delta.
6. Conflitos são explicitados para resolução; não usar last-write-wins em dados financeiros.

## Integridade

- Transações financeiras não podem ser duplicadas por retry.
- Lançamentos confirmados são corrigidos por estorno/compensação.
- Operações rejeitadas permanecem visíveis para resolução.
- Revogação de dispositivo invalida novas sincronizações.
- Migrações locais e restauração precisam de testes.

## Política

Começar com leitura offline e rascunhos. Ampliar escrita offline após testes de conflito, idempotência e segurança.
