# Preview local

Na raiz do repositório:

```powershell
pnpm preview:dev
```

Abra <http://localhost:5173>. O Vite mantém HMR ativo e a API FastAPI reinicia com `--reload`.

Para encerrar:

```powershell
pnpm preview:stop
```

O ambiente usa SQLite descartável/local em `.sfi-preview/data`, migrations locais e uma chave JWT própria. Nunca usa Neon ou o banco do aplicativo desktop. Recursos exclusivos do Tauri, como DPAPI e backup automático, continuam sendo testados no desktop; os demais fluxos funcionam no navegador.
