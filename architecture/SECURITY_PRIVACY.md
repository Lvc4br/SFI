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


## Estado dos controles no MVP (14/11/2026)

### Implementado nesta branch em validação
- Access JWT curto e refresh token opaco com hash SHA-256 persistido, rotação de uso único e detecção de reutilização da família.
- Revogação de sessões por logout, logout global e versão de token do usuário.
- Para o cliente Web: refresh token em cookie HttpOnly, rotação por cookie e proteção CSRF double-submit (cookie legível + header) nos endpoints de refresh/logout.
- Cookies de refresh com SameSite configurável, Secure obrigatório em ambiente production e escopo restrito a /api/v1/auth; cookie CSRF fica no escopo / para leitura pelo frontend.
- Rate limiting persistido no banco por combinação de e-mail normalizado + endereço remoto: cinco falhas em janela de 15 minutos acionam bloqueio de 15 minutos; login bem-sucedido limpa as falhas.
- Headers base na API: nosniff, frame deny, referrer policy, permissions policy e no-store para respostas da API; HSTS apenas quando SFI_ENV=production.
- Isolamento de recursos por usuário; contas/categorias arquivadas deixam de aceitar novos lançamentos/recorrências. Arquivamento de conta exige saldo zero e ausência de recorrências ativas.

### Ainda obrigatório antes de beta público
- O access token Web permanece apenas em memória JavaScript e não é persistido em sessionStorage/localStorage. Após recarregar a página, a sessão é restaurada pelo refresh cookie HttpOnly com CSRF; chamadas simultâneas compartilham uma única renovação em andamento.
- Aplicar CSP e headers no servidor/CDN que entrega apps/web (o middleware FastAPI protege a API, não substitui a política da origem Web).
- Rate limit por e-mail+IP no banco não substitui proteção de borda por IP/WAF; configurar proxy confiável e proteção contra abuso distribuído.
- Verificação de e-mail, recuperação de senha e MFA TOTP com códigos de recuperação ainda não implementados.
- Auditoria de segurança, alertas e observabilidade ainda não concluídos.
- Backup automático, política de retenção, RPO/RTO e restauração em ambiente isolado ainda precisam de execução documentada e evidência.
- Executar testes independentes de CSRF, fixação/roubo de sessão, rotação concorrente, abuso de login, autorização horizontal, carga e dependências.

### Configuração de cookies
- Desenvolvimento HTTP: SFI_REFRESH_COOKIE_SECURE=false.
- Produção: SFI_REFRESH_COOKIE_SECURE=true, HTTPS obrigatório.
- SFI_REFRESH_COOKIE_SAMESITE=lax quando frontend/API forem same-site. Usar none somente com HTTPS e frontend/API realmente cross-site.
- Definir SFI_REFRESH_COOKIE_DOMAIN somente se houver necessidade real de compartilhar cookies entre subdomínios.
- Não usar wildcard em CORS com credenciais. Manter origens exatas.

### Rate limit
O controle usa estado compartilhado no banco, portanto funciona entre múltiplas instâncias da API, diferentemente de um contador em memória. A chave armazenada é hash SHA-256 do e-mail normalizado e IP remoto; não persistimos e-mail/IP em claro na tabela de tentativas. O proxy/ingress deve preservar o IP real de forma confiável; nunca confiar cegamente em X-Forwarded-For vindo diretamente do cliente.


### Auditoria de eventos de autenticação (implementada nesta branch)
- Eventos registrados: criação de conta, login bem-sucedido/falho, bloqueio por tentativas, rotação de refresh, reutilização detectada, logout, alteração de senha e logout global.
- O usuário autenticado pode consultar os eventos recentes em GET /api/v1/auth/security-events; a interface exibe a atividade na página Configurações.
- Não são armazenados tokens, senhas ou IP em claro. O IP remoto é persistido como hash SHA-256; User-Agent é limitado a 256 caracteres.
- A tabela possui índices por usuário/data e tipo/data.
- Política de retenção, exportação e alertas centralizados ainda precisam ser definidos antes do beta. Hash de IP continua sendo dado pseudonimizado e deve receber retenção limitada.


### Datas e fuso horário
- O usuário possui timezone IANA validado por ZoneInfo, com default America/Sao_Paulo e opção de alteração na interface.
- Instantes são persistidos em UTC; limites de dia/mês do dashboard, orçamento e filtros de calendário são convertidos do fuso do usuário para UTC.
- A distribuição tzdata é incluída para suportar Windows e imagens mínimas sem banco IANA nativo.
- Testes cobrem movimentações próximas à meia-noite e a alteração de fuso de America/Sao_Paulo para UTC.

### Retenção de tentativas de login
- Registros de rate limit sem atualização há mais de 30 dias são removidos durante novas tentativas de login.
- A retenção de eventos de segurança ainda precisa de decisão explícita; não apagar auditoria sem política aprovada.
