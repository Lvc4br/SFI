# Exceções temporárias de auditoria de dependências

## GHSA-fc5q-39xc-vjpf / CVE-2026-112366

- **Pacote:** picomatch 4.0.7.
- **Caminho no lockfile:** Vite → fdir → picomatch.
- **Severidade publicada:** alta (ReDoS por extglobs de ramo único).
- **Uso no SFI:** dependência transitiva de ferramenta de desenvolvimento/build; não é dependência de produção do aplicativo financeiro empacotado.
- **Situação em 17/11/2026:** a base de advisories não indica versão corrigida publicada. O npm continua oferecendo 4.0.7 como latest; o advisory registra patched version desconhecida.
- **Decisão:** exceção temporária e explícita no arquivo pnpm-workspace.yaml para que a auditoria continue falhando para outros advisories, sem fingir que este foi corrigido.
- **Mitigação:** não aceitar padrões glob fornecidos por usuários no pipeline de build; não expor Vite/dev server na distribuição; manter Vite apenas em devDependencies.
- **Revisão obrigatória:** 17/12/2026 ou antes, se sair versão corrigida ou orientação do mantenedor.

A exceção não significa que a vulnerabilidade foi corrigida. Remova a exceção assim que existir uma versão corrigida e atualize o lockfile.
