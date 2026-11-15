# Arquitetura de IA — SFI

## Papel

Assistente analítico pessoal e ferramenta de automação sob controle do usuário. Não é sistema contábil nem autoridade matemática; não oferece cursos, aulas ou uma plataforma de educação financeira.

## Componentes

AI Gateway, Policy Engine, Retrieval/RAG, Tool Registry, Redaction e Evaluation.

## Ferramentas permitidas

Consultar resumo financeiro autorizado, categorias e orçamento; executar calculadora determinística; simular cenários sem persistir; consultar fontes externas explicitamente habilitadas; criar rascunhos de metas/listas; gerar relatórios para revisão.

## Ferramentas proibidas na primeira versão

Transferir dinheiro, pagar faturas, comprar/vender ativos, contratar crédito, enviar dados sem consentimento, executar SQL arbitrário ou acessar arquivos fora do escopo autorizado.

## Confirmação humana

Ações persistentes apresentam resumo e impacto e exigem confirmação explícita. IA prepara rascunhos, não confirma silenciosamente. Cálculos, saldos e totais são sempre produzidos por serviços determinísticos.

## Privacidade e avaliação

Consentimento granular, minimização, redação de identificadores e retenção configurável. Testar erros aritméticos, alucinação de taxas, confusão entre saldo e fluxo, prompt injection em documentos, vazamento entre usuários e recomendações arriscadas. A IA é opcional e nunca bloqueia o uso offline.
