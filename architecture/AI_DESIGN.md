# Arquitetura de IA — SFI

## Papel

Professor e assistente analítico, não sistema contábil nem autoridade matemática.

## Componentes

AI Gateway, Policy Engine, Retrieval/RAG, Tool Registry, Redaction e Evaluation.

## Ferramentas permitidas

Consultar resumo financeiro autorizado, categorias e orçamento; executar calculadora determinística; simular cenários sem persistir; consultar conteúdo educacional e indicadores com fonte; criar rascunhos de metas/listas; gerar relatórios para revisão.

## Ferramentas proibidas na primeira versão

Transferir dinheiro, pagar faturas, comprar/vender ativos, contratar crédito, enviar dados sem consentimento, executar SQL arbitrário ou acessar arquivos fora do escopo autorizado.

## Confirmação humana

Ações persistentes apresentam resumo e impacto e exigem confirmação explícita. IA prepara rascunhos, não confirma silenciosamente.

## Privacidade e avaliação

Consentimento granular, minimização, redação de identificadores e retenção configurável. Testar erros aritméticos, alucinação de taxas, confusão entre saldo e fluxo, prompt injection em documentos, vazamento entre usuários e recomendações arriscadas.
