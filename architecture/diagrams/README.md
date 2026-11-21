# Diagramas de Arquitetura SFI

Diagramas vivos: manter alinhados com ADRs, código, schema e release. Diagramas descrevem arquitetura **proposta/observada** e não certificam implementações.

## 1. Contexto do sistema

```mermaid
flowchart TD
  U[Pessoa usuária] --> C[Web / Desktop / Mobile]
  C --> API[API / camada de domínio]
  API --> DB[(Persistência)]
  API --> W[Workers: importação, OCR, relatórios]
  W --> FS[Armazenamento privado]
  API --> AI[Gateway IA - opcional]
  AI --> EX[Provedores externos]
  API --> EXT[Fontes externas autorizadas]
```

**Status:** abstração conceitual. Persistência, runtime e plataformas ainda precisam de decisão arquitetural consolidada (ADR pendente).

## 2. Arquitetura de referência em camadas

```mermaid
flowchart TB
  subgraph Clients[Clientes]
    WEB[Web React / TS]
    DESK[Desktop Tauri]
    MOB[Mobile Expo]
  end
  subgraph Core[API - monólito modular]
    AUTH[Identity / Sessions / Authorization]
    FIN[Domain: ledger / accounts / transactions]
    PLAN[Budget / Goals / Debt / Forecast]
    CON[Import / Reconciliation / Fiscal]
    REP[Reports]
    AUD[Audit / Privacy]
  end
  subgraph Infra[Adapters / Infrastructure]
    DB[(Database)]
    OBJ[Private Object Storage]
    WORK[Workers]
    AIG[AI Gateway - optional]
  end
  WEB --> AUTH
  DESK --> AUTH
  MOB --> AUTH
  AUTH --> FIN
  FIN --> PLAN
  FIN --> CON
  FIN --> REP
  FIN --> AUD
  Core --> DB
  CON --> WORK
  WORK --> OBJ
  Core --> AIG
```

**Boundary:** clientes não acessam diretamente banco, segredo de servidor ou fornecedor de IA. Toda mutação passa por validação, autorização e domínio; ações persistentes/extraídas exigem revisão humana quando aplicável.

## 3. Runtime desktop local-first (PR #17; proposta de branch, não integrada em main)

```mermaid
flowchart LR
  UI[Tauri UI] --> IPC[IPC / bridge restrita]
  IPC --> API[Sidecar FastAPI em loopback]
  API --> DB[(SQLite local)]
  API --> DP[Proteção de segredos / DPAPI]
  API --> BK[Backup criptografado]
  API -. futura sincronização .-> SY[Sync client]
  SY -.-> SR[Servidor remoto]
```

**Status:** arquitetura descrita no PR #17. Não tratar como arquitetura aprovada até decisão explícita e inspeção/revisão do PR.

## 4. Fluxo financeiro (lançamento confirmado)

```mermaid
sequenceDiagram
  actor User
  participant UI as Cliente
  participant API as API
  participant D as Domain / Validator
  participant DB as Database
  User->>UI: Preenche e confirma
  UI->>API: comando + idempotency key
  API->>D: validação e regra
  D->>DB: transação atômica
  DB-->>D: resultado persistido
  D-->>API: resultado / evento auditável
  API-->>UI: confirmação
  UI-->>User: estado atualizado
```

**Garantias a exigir nos testes:** atomicidade, idempotência, Decimal, autorização, controle de concorrência, auditabilidade, sem double-posting.

## 5. Sincronização futura

```mermaid
sequenceDiagram
  participant L as Local store
  participant Q as Outbox
  participant S as Sync API
  participant R as Remote store
  L->>Q: operação identificada e versionada
  Q->>S: batch + cursor + idempotency keys
  S->>S: auth / validation / conflict policy
  S->>R: commit atômico
  R-->>S: accepted / rejected / conflict
  S-->>Q: status por operação + cursor
  Q->>L: marcar / reconciliar / manter conflito
```

**Não implementado como protocolo completo:** diagrama de destino; conflitos financeiros não podem usar sobrescrita silenciosa.

## 6. Fluxo de documento fiscal

```mermaid
flowchart LR
  UP[Upload / arquivo local] --> LIM[Limites e validação]
  LIM --> PAR[Parser / OCR]
  PAR --> EX[Campos extraídos + confiança]
  EX --> RV[Revisão humana]
  RV -->|Confirmar| TX[Comando financeiro idempotente]
  RV -->|Corrigir / rejeitar| HOLD[Registro de revisão / descarte]
  TX --> DB[(Persistência)]
```

**Segurança:** parser isolado, limites, tratamento de arquivos hostis, minimização e autorização por usuário.

## 7. Matriz de status dos diagramas

| Diagrama | Estado |
|---|---|
| Contexto | Conceitual |
| Camadas | Referência |
| Runtime desktop local-first | Proposta no PR #17 |
| Lançamento financeiro | Fluxo alvo; verificar implementação |
| Sync | Futuro / não comprovado |
| Documento fiscal | Fluxo alvo; verificar implementação |

Atualizar estes diagramas no mesmo PR que alterar boundaries, protocolo, schema ou runtime.