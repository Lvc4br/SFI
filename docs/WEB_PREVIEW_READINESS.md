# Web preview — critérios de avanço

## Estado atual
- [x] Dashboard demonstrativo
- [x] Navegação lateral (altera o título/contexto)
- [x] Resumo ilustrativo, gráfico e tabela de exemplos
- [x] Ocultação visual dos valores
- [x] Layout responsivo básico
- [x] Banner de demo e aviso de ausência de dados reais
- [x] Workflow de preview GitHub Pages configurado

## Limitações explícitas
A navegação dos módulos não é implementação funcional de cada módulo. Nesta fase, outras áreas ainda reutilizam a apresentação do dashboard e não devem ser interpretadas como CRUD ou serviço financeiro. Os valores são estáticos, não há conexão com banco/API, autenticação, sincronização ou armazenamento persistente.

## Critérios mínimos antes de publicar como produto
- [ ] Build e TypeScript verificados no CI
- [ ] Testes de interface e acessibilidade
- [ ] Navegação implementada por módulo e estados vazio/loading/error
- [ ] API, sessão e autorização por usuário
- [ ] Dados persistidos, validação e regras financeiras determinísticas
- [ ] Testes de integração e concorrência PostgreSQL
- [ ] Revisão de segurança, privacidade e LGPD
- [ ] Fluxos de exportação/importação testados
- [ ] Aplicação desktop/mobile e offline/sincronização testadas

## Próximo trabalho
Priorizar uma navegação realmente funcional com módulos que indiquem claramente estado vazio/indisponível, seguida por transações e contas conectadas ao backend, sem expor dados reais no preview público.
