# Conciliação bancária

## Fluxo disponível

1. Selecione uma conta ativa, não creditícia.
2. Importe um extrato CSV, JSON ou OFX (até 5 MiB) para a conta selecionada.
3. O SFI guarda as linhas do extrato como registros pendentes, sem criar receitas ou despesas.
4. A tela oferece sugestões automáticas por conta, moeda, tipo, valor exato e data dentro de uma janela de sete dias.
5. O usuário confirma manualmente a correspondência, ignora uma linha ou desfaz uma conciliação.

## Integridade

- Os registros pertencem ao usuário e à conta selecionada.
- Reimportação idempotente: identificador externo bancário ou impressão digital estável.
- Um lançamento financeiro não pode ser conciliado duas vezes.
- A correspondência exige conta, moeda, tipo e valor exatos.
- Transferências e estornos ficam fora das sugestões automáticas nesta etapa.
- Nenhuma movimentação existente é editada, criada ou excluída pela importação do extrato.
- Conflitos concorrentes são rejeitados e exigem atualização da lista.

## Limitações conhecidas

- A conciliação é um vínculo entre uma linha bancária e um lançamento já existente; não cria automaticamente lançamento ausente.
- Correspondência aproximada é apenas sugestão; confirmação humana obrigatória.
- Não há conexão direta com bancos/Open Finance, OFX SGML é interpretado pelo parser atual e layouts proprietários podem exigir adaptação.
- Não há conciliação de faturas de cartão, transferências internas, estornos, tarifas agrupadas ou divisão de uma linha em vários lançamentos.
- A lista de interface mostra os 500 registros mais recentes da conta.
