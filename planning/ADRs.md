# Registros de Decisões Arquiteturais (ADRs)

## ADR-001 — Desktop Windows
Tauri 2 para Windows 10/11 x64. React é incorporado à janela nativa; não há site permanente como produto.

## ADR-002 — Local-first e SQLite
SQLite local é a persistência primária; nenhuma função essencial depende de internet. Motivo: autonomia, privacidade e portabilidade.

## ADR-003 — FastAPI empacotado
Manter FastAPI e regras de domínio, empacotando runtime Python como sidecar gerenciado pelo Tauri. Sidecar e lifecycle ainda precisam ser implementados e validados.

## ADR-004 — Neon opcional
Neon PostgreSQL deixa de ser banco obrigatório/central do Desktop e poderá ser usado somente por sincronização remota opt-in.

## ADR-005 — Monólito modular
Manter FastAPI modular, sem microserviços sem necessidade comprovada.

## ADR-006 — Migrations SQLite explícitas
Schema local versionado. Migrations PostgreSQL não são automaticamente portáveis; diferenças de dialeto devem ser tratadas explicitamente.

## ADR-007 — Privacidade por padrão
Dados e documentos permanecem locais; IA, indicadores externos e sync são opcionais.

## ADR-008 — IA com limites
Ferramentas tipadas; cálculos determinísticos; operações críticas exigem confirmação.

## ADR-009 — Valores exatos
Decimal no domínio e representação decimal exata no banco; nunca float/SQLite REAL para dinheiro.

## ADR-010 — Compras e documentos integrados
Compra confirmada pode gerar despesa, estoque e histórico de preços idempotentemente; documento fiscal exige revisão humana.

## ADR-011 — Sem produto educacional
Cursos, aulas, glossário pedagógico, trilhas e linguagem de ensino não fazem parte do SFI.
