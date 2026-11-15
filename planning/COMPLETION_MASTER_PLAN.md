## Reorientação obrigatória pelo PROMPT MESTRE — 15/11/2026

A especificação atual substitui decisões anteriores incompatíveis. SFI é ferramenta pessoal de gestão, não plataforma educacional.

### Bloqueios arquiteturais
- [x] README e especificação reposicionados para uso pessoal/Desktop.
- [x] Educação removida da navegação e telas da interface.
- [x] Arquitetura local-first documentada.
- [x] SQLite definido como fonte local; Neon somente sync opt-in.
- [ ] FastAPI empacotado como sidecar Windows sem Python instalado.
- [ ] Lifecycle do sidecar, loopback dinâmico e encerramento confiável.
- [ ] Migrations compatíveis com SQLite e atualização segura.
- [ ] Diretórios privados de dados/documentos e proteção de segredos.
- [ ] Backup/restore SQLite integrado ao app.
- [ ] Instalação limpa, offline, atualização e desinstalação verificadas.

### Escopo funcional pendente
Cartões/faturas, conciliação, OFX/XLSX, dívidas, financiamentos, metas, investimentos, indicadores, calculadoras, compras, listas favoritas, histórico de preços, estoque, XML/PDF/OCR, patrimônio, documentos, exportação universal, relatórios, diagramas interativos, temas personalizados e assistente de IA opcional.

### Regra de status
Nenhum módulo é concluído apenas por documentação, rota, tabela, botão ou scaffold. Aceite exige jornada funcional, persistência, integração, tratamento de erros, testes e documentação. Recursos externos (assinatura, IA, cotações e sync) são opcionais e não podem bloquear operação offline.
