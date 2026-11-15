# Escopo da primeira entrega Desktop — SFI

**Produto:** aplicativo pessoal instalável Windows, local-first. Este recorte não elimina o escopo completo de [PRODUCT_SPEC.md](PRODUCT_SPEC.md).

## Resultado esperado
Tauri incorpora React, inicia backend local empacotado, cria/abre SQLite no diretório de dados do usuário e permite administrar o núcleo financeiro sem internet ou serviço remoto.

## Núcleo local inicial
- Inicialização/encerramento do aplicativo e processo local.
- SQLite persistente, migrations e integridade.
- Perfil local e proteção de sessão/segredos.
- Contas, categorias, receitas, despesas e transferências.
- Estornos compensatórios e auditoria.
- Recorrências/projeções identificadas.
- Orçamento, dashboard, filtros e histórico.
- Importação/exportação financeira inicial e backup/restore local.
- Temas e estados de interface.

## Requisitos Desktop
- Sem endpoint HTTPS ou login remoto obrigatório.
- API local somente loopback, porta dinâmica ou canal privado.
- Dados em diretório do usuário, fora da instalação.
- Migrations com backup prévio e rollback seguro.
- Processo local encerrado junto com o app.
- Atualização preserva dados e verifica compatibilidade.
- Desinstalação não apaga dados pessoais silenciosamente.

## Regras financeiras
Decimal/Numeric; moeda explícita; transferências neutras no resultado; transações idempotentes; lançamentos confirmados corrigidos por estorno; exclusão/arquivamento preservam integridade.

## Fora da primeira fatia, mas obrigatório no produto completo
Cartões/faturas; conciliação/OFX; dívidas/amortizações; metas; investimentos; calculadoras; indicadores; listas/compras; estoque; XML/PDF/OCR; patrimônio; documentos; importação/exportação universal; relatórios; diagramas; IA; sync opcional; hardening e acessibilidade.

## Aceite
Instalação limpa sem ambiente de desenvolvimento, criação SQLite, jornada financeira offline, dados preservados após reinício, backup/restore, migration versionada, desinstalação sem perda silenciosa e E2E no aplicativo instalado.
