# Registros de Decisões Arquiteturais (ADRs)

## ADR-001 — PostgreSQL gerenciado no Neon
**Decisão:** Neon PostgreSQL como banco central.  
**Motivo:** serviço PostgreSQL gerenciado e adequado ao modelo relacional. Clientes acessam apenas a API.

## ADR-002 — Backend FastAPI
**Decisão:** Python + FastAPI para API e regras de domínio.  
**Motivo:** validação, tipagem, ecossistema Python e integração com processamento de documentos.

## ADR-003 — Monólito modular inicial
**Decisão:** iniciar com monólito modular e workers assíncronos; não iniciar com microserviços.  
**Motivo:** reduzir complexidade operacional até haver escala ou limites organizacionais comprovados.

## ADR-004 — Clientes por plataforma
**Decisão:** React/TypeScript na Web, Tauri no Desktop e React Native/Expo no Mobile.  
**Motivo:** reutilizar contratos e padrões sem forçar uma única UI em todas as plataformas.

## ADR-005 — Docker opcional
**Decisão:** Docker não é pré-requisito para desenvolvimento local.  
**Motivo:** executar diretamente Python e Node; usar contêineres quando agregarem valor a serviços auxiliares/CI.

## ADR-006 — SQLite não central
**Decisão:** Neon é a fonte central; banco local transacional pode apoiar recursos offline, se necessário.  
**Motivo:** separar persistência local e consistência compartilhada.

## ADR-007 — IA com limites e confirmação
**Decisão:** IA via gateway, ferramentas tipadas e confirmação humana para persistência.  
**Motivo:** segurança, auditabilidade e prevenção de ações financeiras indevidas.

## ADR-008 — Valores financeiros determinísticos
**Decisão:** Decimal/Numeric e motor de cálculo testável.  
**Motivo:** evitar erros de ponto flutuante e separar cálculo de geração de linguagem.
