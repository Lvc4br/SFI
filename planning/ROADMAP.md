# Roadmap do SFI — Desktop pessoal

Escopo vinculante em [PRODUCT_SPEC.md](../docs/PRODUCT_SPEC.md), arquitetura em [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) e gates em [COMPLETION_MASTER_PLAN.md](COMPLETION_MASTER_PLAN.md).

1. **Auditoria e reorientação:** retirar posicionamento educacional; mapear compatibilidade SQLite/PostgreSQL; preservar regras financeiras.
2. **Runtime Desktop local:** Tauri gerencia FastAPI empacotado, health check, loopback dinâmico, encerramento, diretórios e atualização.
3. **SQLite e núcleo offline:** migrations locais, backup pré-migration, contas, categorias, transações, transferências, estornos, recorrências, orçamento e dashboard.
4. **Importação/exportação e backup:** CSV/XLSX/OFX/JSON/QIF/PDF para movimentações, staging, mapeamento, duplicidade, validação, relatório, backup e restore. PDF exportado é relatório, não extrato bancário oficial; OCR e layouts bancários específicos permanecem pendentes.
5. **Cartões, dívidas e objetivos:** faturas, empréstimos, projeções estimadas Price/SAC, amortização, reservas e metas; CET, multas, mora e refinanciamento permanecem pendentes.
6. **Compras e consumo:** listas favoritas, produtos, estabelecimentos, compras, preços e integração idempotente com despesas.
7. **Documentos fiscais e estoque:** XML NF-e/NFC-e, PDF/DANFE, imagens, OCR, QR, revisão humana e estoque.
8. **Patrimônio e investimentos:** ativos, passivos, carteira, rendimentos, preço médio e snapshots; sem ordens.
9. **Indicadores e calculadoras:** fontes, datas, cache, fórmulas e projeções determinísticas.
10. **Visualizações, relatórios e temas:** gráficos/diagramas com dados reais, filtros, presets, cores, exportação e acessibilidade.
11. **IA pessoal opcional:** ferramentas tipadas, mínimo acesso, consentimento, sem SQL arbitrário ou ações críticas.
12. **Sync remoto opcional:** Neon opt-in, outbox, conflitos explícitos e revogação de dispositivos.
13. **Qualidade e lançamento:** instalação/atualização/desinstalação, recuperação, segurança, acessibilidade, documentação e assinatura.

**Fora do produto:** cursos, aulas, trilhas, avaliações pedagógicas, gamificação educacional, plataforma para ensinar terceiros, pagamentos e execução de ordens de investimento.
