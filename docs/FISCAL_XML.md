# Documentos fiscais — NF-e/NFC-e

## Fluxo suportado

1. O usuário seleciona XML (até 2 MiB), PDF (até 10 MiB) ou imagem PNG/JPEG/WEBP/TIFF (até 10 MiB).
2. XML: rejeita DTD/entidades e extrai chave, número, série, emitente, CPF/CNPJ, data, total e itens.
3. PDF: extrai texto selecionável; se não houver texto, renderiza até 10 páginas e executa OCR local em português/inglês.
4. Imagem: valida formato e limite de 20 megapixels e executa OCR local.
5. A prévia exige revisão humana. A confirmação grava metadados e SHA-256, sem reter o arquivo original. A despesa opcional é criada na mesma transação.

## OCR empacotado

- Tesseract OCR com dados de idioma português e inglês é incluído no instalador Windows.
- PDFium renderiza páginas PDF para imagens; Pillow normaliza imagens antes do OCR.
- Tempo máximo por imagem OCR: 45 segundos; tamanho máximo do documento: 10 MiB; até 10 páginas por PDF.
- O OCR pode errar caracteres, datas, valores e identificadores. A prévia deve ser conferida antes da confirmação.
- O OCR não extrai todos os itens do DANFE; a captura detalhada de itens é mais confiável via XML.

## Segurança e integridade

- Autenticação obrigatória e isolamento por usuário.
- Chave de acesso única por usuário, com dígito verificador validado.
- DTD e entidades externas proibidos; limite de tamanho e páginas.
- XML/PDF/imagem originais não são persistidos; somente dados extraídos e hash SHA-256.
- Despesa opcional, sempre após confirmação explícita.
- Conta da despesa precisa pertencer ao usuário, estar ativa, não ser do tipo crédito e estar em BRL.
- QR Code pode ser informado manualmente ou lido pela câmera quando o navegador oferece BarcodeDetector e permissão do usuário; a chave é comparada com o documento.

## Limitações

Não consulta SEFAZ nem verifica autorização/protocolo, assinatura digital, situação fiscal ou autenticidade do emitente. Não importa CT-e ou NFS-e. O OCR e a comparação de chave do QR são ferramentas auxiliares para conferência humana, não validadores fiscais oficiais.
