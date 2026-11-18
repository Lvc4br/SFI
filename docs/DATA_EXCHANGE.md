# Importação e exportação de movimentações

A primeira fatia do intercâmbio de dados oferece importação com prévia e confirmação humana para CSV, JSON e OFX, além de exportação CSV/JSON.

## Formatos de importação
- CSV: cabeçalhos date/occurred_at, type/transaction_type, amount, description e account_id/account_name opcionais; category_id/category_name opcionais.
- JSON: array de objetos ou objeto com a propriedade transactions.
- OFX: extratos SGML com blocos STMTTRN, DTPOSTED, TRNAMT, TRNTYPE, FITID, NAME e MEMO.

## Fluxo seguro
1. Envie o conteúdo para POST /api/v1/exchange/transactions/preview.
2. Corrija linhas inválidas e confira os duplicados.
3. Confirme explicitamente via POST /api/v1/exchange/transactions/import.
4. A importação é atômica: se uma linha for inválida, nenhuma movimentação é criada.
5. Chave determinística por usuário/conta/categoria/tipo/valor/data/descrição/ID externo evita reimportação duplicada.

## Limites
- 5 MB e 10.000 linhas por arquivo.
- Contas/categorias precisam pertencer ao usuário e estar ativas.
- Nenhuma transação existente é alterada ou removida.
- Importação não cria contas/categorias automaticamente e não converte moedas.
- XLSX, PDF, QIF e exportação de todo o banco ainda não estão nesta fatia.
