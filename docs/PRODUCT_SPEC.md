# Especificação do Produto — SFI

## 1. Objetivo
O SFI é um aplicativo desktop pessoal para administrar finanças, compras, documentos fiscais, investimentos informativos, patrimônio e planejamento econômico.

**Fora do objetivo:** educação financeira como produto, cursos, aulas, avaliações, trilhas pedagógicas, gamificação educacional ou plataforma para ensinar terceiros.

## 2. Plataforma
- Windows 10/11 x64.
- Tauri 2 + React + TypeScript + Vite.
- FastAPI empacotado como processo local/sidecar.
- SQLite local como fonte de verdade primária.
- Neon PostgreSQL somente para sincronização remota opcional.
- Arquivos fiscais/anexos no diretório privado do aplicativo.
- IA, cotações e indicadores externos opcionais.

O aplicativo deve funcionar sem navegador externo, serviço hospedado, internet, Docker, Node, Python ou banco instalado pelo usuário.

## 3. Módulos
Dashboard personalizável; contas, cartões e movimentações; orçamento e fluxo de caixa; dívidas, crédito, parcelamentos e financiamentos; reservas e metas; investimentos sem execução de ordens; calculadoras; indicadores brasileiros; listas de compras favoritas e personalizadas; compras e histórico de preços; estoque doméstico; documentos fiscais XML/PDF/imagem/OCR/QR; patrimônio; documentos pessoais; importação/exportação; gráficos, diagramas e relatórios; temas; IA pessoal opcional; backup, restauração e portabilidade.

## 4. Jornadas integradas
- Lista → compra → revisão de documento → confirmação → despesa, histórico de preços e estoque.
- Nota fiscal → extração → validação → correção manual → confirmação humana → registro.
- Movimentação → orçamento → dashboard → relatório/visualização.
- Ativos, investimentos e passivos → patrimônio líquido e evolução.
- Importação → prévia → mapeamento → validação → confirmação → relatório.

## 5. Regras
- Cálculos determinísticos; Decimal no domínio e representação exata no banco.
- Nunca misturar moedas sem conversão explícita, taxa, fonte e data.
- Transferências próprias não são renda nem consumo consolidado.
- Projeções/estimativas identificadas.
- IA usa ferramentas tipadas, não é fonte de verdade e não executa ações críticas sem confirmação.
- OCR não comprova autenticidade fiscal; QR não garante documento completo.
- Duplicidades são sinalizadas, não descartadas silenciosamente.
- Movimentação confirmada corrigida por estorno/compensação.
- Sync opcional nunca sobrescreve dados financeiros silenciosamente.

## 6. Privacidade
Dados permanecem locais por padrão. Conexões externas são explícitas, configuráveis e revogáveis. Indicadores externos exibem fonte, data e último cache. Falha de internet não bloqueia o núcleo.

## 7. Critério de aceite
Instalador funcional em Windows limpo, SQLite local persistente, funções essenciais offline, módulos integrados, importação/exportação e recuperação verificadas, testes unitários/integração/E2E/segurança e ciclo de instalação/atualização/desinstalação aprovados. Build verde isolado não significa produto concluído.
