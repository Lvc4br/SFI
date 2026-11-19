# Arquitetura — SFI Desktop Local-first

## Princípio
O dispositivo é o ambiente primário de execução e persistência. Rede é opcional; nenhuma função essencial depende de site, API hospedada ou Neon.

## Componentes
- Desktop: Tauri 2, Windows x64.
- UI: React + TypeScript + Vite incorporados ao bundle.
- Backend local: FastAPI empacotado como sidecar/processo filho gerenciado pelo Tauri.
- Persistência: SQLite no diretório privado do usuário.
- Domínio/ORM: SQLAlchemy; regras e cálculos determinísticos no backend.
- Migrações: Alembic com suporte explícito a SQLite.
- Arquivos: diretório privado local com metadados no SQLite.
- Sync: adaptador PostgreSQL/Neon opcional e desligado por padrão.
- IA/indicadores: provedores externos opcionais.

## Inicialização
1. Tauri resolve diretórios de dados/cache e inicia sidecar.
2. Sidecar recebe configuração local não secreta.
3. Backend abre SQLite e valida/migra schema com backup prévio.
4. Backend vincula em loopback, escolhe porta efêmera e comunica endereço por canal privado.
5. UI aguarda health check e libera navegação.
6. Encerramento solicita shutdown e finaliza processo após timeout.

Não expor porta fixa na LAN, não exigir endpoint remoto e não aceitar origem arbitrária.

## Integridade
SQLite com FK, busy_timeout, WAL quando adequado e transações. Dinheiro em representação decimal exata (texto decimal validado ou inteiro em unidade mínima); nunca REAL. Operações idempotentes. Dados fora do diretório de instalação. Migrações testadas em banco vazio e com dados.

## Sync
Neon pode ser habilitado para sync entre dispositivos/backup remoto. Outbox, IDs estáveis, idempotência, cursores e resolução explícita. Movimentações confirmadas não usam last-write-wins.

## Segurança
API local somente loopback, token efêmero UI/sidecar, capabilities mínimas, validação de arquivos, segredos no cofre do SO quando possível, logs sem dados financeiros e backup criptografado.

## Estado
A API FastAPI e o cliente Tauri existem, mas sidecar empacotado, lifecycle, SQLite padrão, migrations locais e operação offline ainda precisam ser implementados e testados. Não declarar local-first concluído antes desses gates.
