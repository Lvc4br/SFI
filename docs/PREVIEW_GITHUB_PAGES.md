# Preview temporário SFI via GitHub Pages

O workflow `.github/workflows/sfi-preview.yml` constrói a aplicação Web e publica o artefato `apps/web/dist` no GitHub Pages quando há push para a branch `design/orpiofin-inspired-dashboard` ou acionamento manual.

## Ativação
1. GitHub: Settings → Pages.
2. Em Build and deployment, selecione **GitHub Actions** como fonte.
3. Acesse Actions e aguarde a execução do workflow **SFI Temporary Preview**.
4. O link do site será exibido no job de deploy / environment `github-pages`.

## Observações
- É um preview publicado na internet: não usar dados reais, segredos, ou conteúdo privado.
- O preview é cancelado/substituído pelo deploy seguinte (concurrency).
- O workflow assume que o build gera `apps/web/dist`. Se o output do build for diferente, ajustar o caminho.
- Para funcionar em URL de projeto GitHub Pages, o frontend pode precisar configurar o base path `/SFI/` e roteamento SPA; validar antes de considerar o preview funcional.
- A API não é publicada por Pages (Pages hospeda conteúdo estático); componentes que dependem da API podem precisar de configuração segura, mock/demo ou ambiente backend disponível.
