# Implantação e Operação

## Ambientes
Local com execução direta de Python/Node (Docker opcional), CI, staging e produção com credenciais e dados separados.

## Neon
Projetos/branches separados por ambiente; credenciais de menor privilégio; URL somente no backend; migrações controladas; pooling e limites monitorados.

## Backend e workers
FastAPI em plataforma ASGI, workers separados para tarefas demoradas, health checks, migrações antes do deploy e segredos em secret manager.

## Clientes
Web com HTTPS, CSP e headers; Desktop Tauri com builds assinados e canal beta; Mobile via Expo EAS ou equivalente, certificados protegidos e testes em aparelhos reais.

## Backup e recuperação
Backups gerenciados, exportação lógica adicional, versionamento/retention do storage, criptografia e testes periódicos de restauração. Definir RPO/RTO antes da produção.

## Operação
Monitorar disponibilidade, latência, erros, conexões, filas, OCR, sincronização, custo de IA, armazenamento e tentativas indevidas.

## Custos
Estimar Neon, API, workers/fila, storage, OCR, IA, e-mail, domínio, assinatura e distribuição. Criar quotas e alertas de custo.
