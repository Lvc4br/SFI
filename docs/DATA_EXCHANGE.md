# Importação e exportação de movimentações

A primeira fatia do intercâmbio de dados oferece importação com prévia e confirmação humana para CSV, JSON, OFX e XLSX, além de exportação CSV/JSON/XLSX.

## Formatos de importação
- CSV: cabeçalhos date/occurred_at, type/transaction_type, amount, description e account_id/account_name opcionais; category_id/category_name opcionais.
- JSON: array de objetos ou objeto com a propriedade transactions.
- OFX: extratos SGML com blocos STMTTRN, DTPOSTED, TRNAMT, TRNTYPE, FITID, NAME e MEMO.
- XLSX: primeira aba, cabeçalhos na primeira linha; conteúdo binário enviado em Base64. Datas do Excel sem fuso são interpretadas como UTC.

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
- Planilhas XLSX são limitadas a 5 MiB, 10.000 linhas e 25 MiB descompactados; a primeira aba é utilizada.
- XLSX exportado contém identificadores, conta/categoria, tipo, valor textual, moeda, descrição e data.
- PDF, QIF e exportação/restauração de todo o banco ainda não estão nesta fatia.
