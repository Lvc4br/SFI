# Pipeline de Documentos Fiscais

## Fluxo

Upload seguro → validação de formato/tamanho → antimalware → hash/duplicidade → parser XML ou OCR → normalização → confiança por campo → revisão humana → confirmação → integração financeira/estoque/preços.

## Regras

- XML estruturado é preferível quando disponível.
- OCR é extração, não prova autenticidade.
- QR Code não garante acesso integral ao documento.
- Validar chave fiscal, emissor, número, data, totais, descontos, frete e cancelamento quando a fonte permitir.
- Não assumir acesso irrestrito a serviços SEFAZ ou municipais.
- Produto deve ser identificado por GTIN/EAN, descrição, variante e unidade; manter score e permitir correção.
- Unidades e preços precisam ser normalizados sem perder valor original.

## Revisão e confirmação

Campos incertos são destacados. O usuário confirma ou corrige antes de criar despesa, compra ou estoque. A confirmação deve ser idempotente e auditável.

## Duplicidade

Usar hash do arquivo, chave fiscal, emissor, número, data e total. Sinalizar possíveis duplicatas para revisão; não descartar silenciosamente.

## Casos especiais

Devoluções, notas canceladas, descontos, frete, itens por peso, divergência de total, OCR ilegível e documentos incompletos.
