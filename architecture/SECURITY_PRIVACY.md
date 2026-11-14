# Segurança e Privacidade — SFI

## Princípios

Privacy by design, minimização, consentimento granular, menor privilégio, defesa em profundidade e transparência.

## Controles

- Autenticação robusta e gestão de sessões/dispositivos.
- Autorização no backend em cada recurso.
- Isolamento por usuário; RLS como camada adicional.
- TLS em trânsito e criptografia em repouso conforme serviço.
- Segredos somente em secret manager/ambiente de servidor.
- Upload privado, validação de tipo/tamanho, antimalware e URLs temporárias.
- Rate limiting, proteção contra abuso e dependências monitoradas.
- Logs redigidos; nunca registrar tokens, documentos integrais ou segredos.
- Auditoria de operações financeiras, consentimentos e exportações.

## LGPD e direitos

Documentar finalidade, base legal, retenção, operadores e compartilhamentos. Implementar acesso, correção, exportação e exclusão conforme obrigações legais. Consentimento para uso de IA deve ser claro e revogável.

## Resposta a incidentes

Definir responsáveis, severidade, contenção, preservação de evidências, comunicação e recuperação. Testar backups e restauração.

## Revisão de risco

Revisar arquitetura antes de integrações bancárias, pagamentos, investimentos ou processamento de documentos em escala.
