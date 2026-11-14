# Estratégia de Testes

## Pirâmide
Unitários para domínio/cálculos; integração para banco/API/fila/storage/autenticação; contrato para OpenAPI; E2E nas jornadas críticas; segurança para autorização, upload, sessão e dependências; usabilidade e acessibilidade.

## Casos financeiros obrigatórios
Decimal e arredondamento; saldos; transferência neutra no patrimônio líquido; estorno com trilha; parcelas/vencimentos; juros por período; rentabilidade real com período alinhado à inflação; limites e moedas.

## Casos fiscais
XML válido/inválido; imagem legível/ilegível; duplicidade; nota cancelada; devolução; desconto/frete; produto por peso; unidade incompatível; total divergente; OCR de baixa confiança; correção e confirmação manual.

## Sincronização
Retry, lote interrompido, edições concorrentes, dispositivo revogado, relógio incorreto, migração local e restauração.

## Segurança
Acesso cruzado entre usuários, RLS, upload malicioso, prompt injection, segredos em bundle, rate limiting, sessão expirada, CORS/CSRF, exportação e exclusão.

## Bloqueios de release
Falha de integridade financeira, vulnerabilidade crítica/alta não mitigada, acesso cruzado, perda/duplicação, migração sem recuperação, segredo exposto ou backup sem restauração comprovada.
