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
- PDF e QIF ainda não estão nesta fatia. Backup completo e restauração local estão documentados abaixo.


## Backup completo e restauração

- `GET /api/v1/backup/export` gera um arquivo JSON versionado com os registros financeiros de todas as tabelas pertencentes ao usuário autenticado, incluindo contas, categorias, movimentações, cartões/faturas/pagamentos, dívidas, metas, investimentos, patrimônio, compras/listas, produtos/preços, estoque, documentos fiscais, recorrências e conciliação.
- O backup preserva os identificadores e os relacionamentos entre registros. O identificador do usuário é reassociado ao usuário autenticado durante a restauração; o e-mail, hash de senha, tokens e eventos de segurança não são exportados nem substituídos.
- `POST /api/v1/backup/preview` valida versão, estrutura, tabelas, colunas, tipos e limites sem gravar dados.
- `POST /api/v1/backup/restore` exige `confirmed: true` e substitui os dados financeiros do usuário em uma única transação SQLite. Se qualquer restrição de integridade falhar, toda a restauração é revertida.
- A restauração integral está restrita ao SQLite local; não executa alterações no Neon nem em bancos PostgreSQL remotos.
- Limites: 50 MiB e 250.000 registros. Backups com versão ou conjunto de tabelas incompatível são rejeitados, não convertidos silenciosamente.
- O backup é um arquivo JSON legível e não é criptografado. O usuário deve armazená-lo em local protegido; a criptografia do arquivo e backups automáticos agendados continuam pendentes.
- Recomenda-se gerar um backup atual antes de restaurar. A prévia informa quantos registros serão substituídos, e a interface exige confirmação adicional.
