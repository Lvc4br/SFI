# Importação de NF-e/NFC-e (XML)

## Fluxo

1. O usuário seleciona um XML de NF-e/NFC-e de até 2 MiB.
2. A API rejeita XML malformado e qualquer declaração DOCTYPE/ENTITY.
3. A prévia extrai chave de acesso, número, série, emitente, CPF/CNPJ, data, total e produtos.
4. O usuário revisa os dados e decide se deseja criar uma despesa.
5. A confirmação grava metadados e SHA-256, sem reter o XML original. Se solicitada, a despesa é criada na mesma transação.

## Segurança e integridade

- Autenticação obrigatória e isolamento por usuário.
- Chave de acesso única por usuário.
- DTD e entidades externas proibidos; limite de tamanho de 2 MiB.\n- Chave de acesso com 44 dígitos e dígito verificador validado pelo módulo 11.
- XML bruto não persistido; itens guardados como JSON extraído.
- Despesa opcional, sempre após confirmação explícita.
- Conta da despesa precisa pertencer ao usuário, estar ativa, não ser do tipo crédito e estar em BRL.
- Idempotência da movimentação usa a chave de acesso da NF-e.

## Limitações

Não consulta SEFAZ nem verifica autorização/protocolo, assinatura digital, situação fiscal ou autenticidade do emitente. Não interpreta PDF/DANFE/imagem, não executa OCR/QR Code e não importa CT-e ou NFS-e. O módulo é um leitor e organizador de dados para conferência humana, não um validador fiscal.
