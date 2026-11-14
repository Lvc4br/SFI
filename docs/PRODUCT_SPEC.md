# Especificação do Produto — SFI

## 1. Objetivo

Construir um sistema multiplataforma que ensine educação financeira e permita organizar a vida financeira, consumo, documentos fiscais e patrimônio em um só ambiente. Deve atender iniciantes sem limitar usuários experientes.

## 2. Plataformas

- Web: React + TypeScript.
- Desktop: Tauri + React + TypeScript.
- Mobile: React Native + Expo.
- API: Python + FastAPI.
- Persistência central: Neon PostgreSQL.
- Arquivos privados: object storage compatível com S3.

## 3. Módulos do produto

1. Dashboard; 2. contas e movimentações; 3. orçamento e fluxo de caixa; 4. educação financeira; 5. dívidas e crédito; 6. reservas e objetivos; 7. investimentos informativos; 8. calculadoras; 9. economia e indicadores; 10. compras e projetos; 11. patrimônio; 12. segurança financeira; 13. relatórios; 14. IA; 15. configurações; 16. documentos fiscais; 17. listas de compras; 18. despensa/estoque; 19. inteligência de consumo.

## 4. Jornadas integradas

Lista de compras → compra realizada → documento fiscal → extração de itens → revisão humana → confirmação → despesa financeira + estoque + histórico de preços. Deve ser possível registrar compras não planejadas.

## 5. Requisitos transversais

- Autenticação, autorização e isolamento por usuário.
- Responsividade, acessibilidade e experiência consistente nas três plataformas.
- Operação degradada offline com sincronização segura.
- Exportação e exclusão de dados.
- Auditoria para operações sensíveis.
- Fontes e datas para indicadores externos.
- Observabilidade sem exposição de dados pessoais.

## 6. Regras e limites

- Cálculos financeiros determinísticos no backend.
- Dinheiro em Decimal/Numeric.
- IA não pode executar pagamentos, transferências, ordens de investimento, SQL arbitrário ou persistência relevante sem confirmação.
- OCR não comprova autenticidade fiscal.
- QR Code de documento fiscal não garante acesso integral ao documento.
- Correspondência de produtos deve considerar GTIN/EAN, variantes, unidades e confiança.
- Duplicidades devem ser sinalizadas por hash, chave fiscal, emissor, número, data e total, com revisão humana.
- Estoque e reposição são estimativas ajustáveis.

## 7. Fora do escopo inicial

Movimentação bancária, pagamentos, execução de ordens de investimento e aconselhamento personalizado sem controles regulatórios. Integrações bancárias futuras dependem de avaliação jurídica, segurança e consentimento.

## 8. Critérios de aceite

Uma entrega precisa de critérios verificáveis, autorização, validação, testes, tratamento de erros, acessibilidade, documentação e trilha de auditoria proporcional ao risco.
