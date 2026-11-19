# Checklist de testes operacionais — SFI Desktop 0.1.0

**Build:** commit `5e6e72bd0ddb68b812799620208e24865f12947c`  
**Plataforma:** Windows 10/11 x64  
**Estado:** instaladores NSIS e MSI compilados no GitHub Actions; CI, segurança e E2E aprovados. Ainda não houve execução em uma máquina Windows de destino.

Este roteiro é para validar o instalador real e o comportamento do SFI no computador do operador. Use somente dados fictícios. O SFI Desktop desta versão usa SQLite local; não precisa de Neon, PostgreSQL, internet, Python, Node, Rust ou VS Code para executar.

## 1. Arquivos e segurança antes da instalação

O artefato de CI contém:
- `nsis/SFI_0.1.0_x64-setup.exe`
- `msi/SFI_0.1.0_x64_en-US.msi`

Escolha **um** instalador para a primeira instalação. O NSIS é a opção recomendada para o teste inicial; o MSI é uma alternativa para validar distribuição corporativa. Não instale os dois sobre a mesma instalação.

Este build ainda não está assinado com certificado de publicação. O Windows pode exibir aviso de editor desconhecido/SmartScreen. Não desative o antivírus nem a proteção do Windows para contornar avisos. Se o arquivo for bloqueado, interrompa o teste e registre a mensagem.

Antes de instalar:
1. Confirme que o Windows é 64 bits.
2. Feche outras instâncias do SFI.
3. Se já existir uma instalação anterior, faça backup pelo próprio SFI e guarde-o fora da pasta de instalação.
4. Não use arquivos financeiros reais, documentos fiscais de terceiros ou credenciais reais durante a homologação.

## 2. Instalação limpa e primeira inicialização

- [ ] Instalar pelo NSIS (ou MSI, em rodada separada).
- [ ] Confirmar que o aplicativo aparece no menu Iniciar e abre sem Python/Node/Rust instalados.
- [ ] Confirmar que a janela principal abre sem erro de inicialização do sidecar.
- [ ] Criar uma conta de teste com e-mail fictício e senha forte (mínimo 12 caracteres).
- [ ] Fechar o aplicativo normalmente e abrir novamente.
- [ ] Confirmar que o login funciona e os dados locais permanecem disponíveis.
- [ ] Desconectar a internet e repetir abertura/login; o núcleo local deve continuar funcional.
- [ ] Conferir que não é solicitada URL de Neon, PostgreSQL ou servidor remoto.

**Resultado esperado:** o processo FastAPI local inicia em loopback, o SQLite é criado em AppLocalData e o usuário consegue entrar. A sessão é mantida em memória; depois de fechar o aplicativo, é normal precisar entrar novamente.

## 3. Fluxos financeiros fundamentais

Crie uma conta corrente fictícia em BRL e categorias de receita/despesa.

- [ ] Criar receita e conferir o saldo.
- [ ] Criar despesa e conferir o saldo.
- [ ] Editar descrição/categoria de uma movimentação permitida.
- [ ] Estornar uma movimentação; conferir que o lançamento original permanece e existe compensação.
- [ ] Criar transferência entre duas contas BRL; conferir débito e crédito.
- [ ] Tentar transferir entre moedas diferentes e confirmar rejeição segura.
- [ ] Criar orçamento mensal e conferir planejado versus realizado.
- [ ] Criar recorrência; conferir configuração, próxima data e prevenção de duplicidade.
- [ ] Testar filtros, paginação, período, atualização e exportação CSV.
- [ ] Fechar e reabrir; conferir saldos, movimentações e orçamento.

**Não** use o saldo exibido como única evidência: confira também os lançamentos e os registros compensatórios.

## 4. Módulos adicionais

### Cartões e faturas
- [ ] Criar cartão de teste e ciclo de fechamento/vencimento.
- [ ] Registrar compra à vista e parcelada.
- [ ] Conferir distribuição de parcelas e fatura correta.
- [ ] Registrar pagamento parcial e total.
- [ ] Conferir que pagar fatura não duplica a despesa da compra.

### Dívidas e calculadoras
- [ ] Criar dívida de teste e registrar pagamento.
- [ ] Conferir separação entre amortização e juros.
- [ ] Gerar cronograma Price e SAC sem gravar pagamentos.
- [ ] Testar refinanciamento sem alterar a dívida original.
- [ ] Testar CET estimado com datas e custos conhecidos; registrar que é estimativa, não CET oficial.
- [ ] Testar encargos por atraso com multa, juros e fator informados; não interpretar o resultado como validação jurídica.

### Metas, investimentos e patrimônio
- [ ] Criar meta, registrar aporte e retirada; conferir histórico e progresso.
- [ ] Criar ativo e registrar compra/venda/dividendo; conferir quantidade e custo médio.
- [ ] Cadastrar bem e passivo com avaliação datada; conferir patrimônio líquido por moeda.
- [ ] Confirmar que esses módulos informativos não movimentam automaticamente o saldo bancário.

### Compras e estoque
- [ ] Criar lista e adicionar produtos com quantidade/unidade.
- [ ] Confirmar uma compra com conta BRL; conferir que a despesa e entradas de estoque ocorrem uma única vez.
- [ ] Repetir a confirmação e conferir idempotência.
- [ ] Registrar consumo/ajuste/perda; conferir saldo do livro-razão.
- [ ] Tentar saída maior que o estoque e conferir rejeição.

### Importação, exportação e conciliação
- [ ] Importar um arquivo fictício CSV/JSON/OFX/XLSX/QIF e conferir prévia antes da confirmação.
- [ ] Testar linha inválida, duplicada e conta/categoria incompatível.
- [ ] Exportar os formatos disponíveis e reabrir os arquivos.
- [ ] Importar extrato para conciliação; conferir sugestões, confirmação humana e desfazer.
- [ ] Confirmar que importar extrato não cria lançamentos financeiros automaticamente.

## 5. Documentos fiscais e OCR

Use uma NF-e/NFC-e de teste legalmente disponibilizada ou um fixture fictício de desenvolvimento. Não envie documentos pessoais reais para terceiros.

- [ ] Importar XML NF-e/NFC-e válido e revisar chave, emitente, data, total e itens.
- [ ] Importar XML malformado e conferir rejeição.
- [ ] Tentar XML com DTD/entidade e conferir rejeição.
- [ ] Importar DANFE PDF com texto selecionável.
- [ ] Importar PDF digitalizado e observar OCR.
- [ ] Importar imagem PNG/JPG/WEBP/TIFF.
- [ ] Comparar manualmente os valores reconhecidos com o documento original.
- [ ] Ler QR Code pela câmera se o WebView2 oferecer suporte e a permissão for concedida; caso contrário, testar colagem manual.
- [ ] Testar QR cuja chave não corresponde ao documento e conferir rejeição.
- [ ] Confirmar uma nota sem criar despesa; depois, em outra nota, confirmar criação de despesa e conferir idempotência.
- [ ] Conferir que o histórico guarda metadados/hash e não mantém o arquivo original.

**Limitação fiscal:** OCR e comparação de chave do QR auxiliam a conferência. Esta versão não consulta SEFAZ, não verifica protocolo/assinatura/autorização e não importa CT-e/NFS-e. Não use o resultado como prova de autenticidade fiscal.

## 6. Backup, criptografia e recuperação local

Faça esta rodada com uma conta de teste descartável.

- [ ] Criar backup manual e guardar o arquivo fora da pasta de instalação.
- [ ] Criar backup criptografado com senha forte.
- [ ] Tentar abrir com senha incorreta e conferir rejeição sem alteração do banco.
- [ ] Alterar um byte/corromper uma cópia e conferir rejeição de integridade.
- [ ] Restaurar o backup válido no perfil de teste e conferir IDs, contas, movimentações e saldos.
- [ ] Configurar backup automático em horário próximo, aguardar execução e conferir histórico/arquivo.
- [ ] Reiniciar o computador e confirmar que o agendamento continua funcional.

Nunca teste restauração sobre um perfil com dados que deseja preservar. Restauração é uma operação destrutiva para o banco de destino.

## 7. Encerramento, atualização e desinstalação

- [ ] Fechar pelo X e conferir que o processo SFI/sidecar encerra.
- [ ] Reiniciar o Windows e reabrir o SFI.
- [ ] Instalar uma atualização somente quando houver um novo build identificado; não testar downgrade.
- [ ] Desinstalar pelo Windows e conferir o comportamento dos dados locais.
- [ ] Reinstalar e verificar se o comportamento corresponde à política de preservação de dados.
- [ ] Se os dados forem removidos ou alterados inesperadamente, interromper e preservar logs/backup.

A assinatura de código e a atualização automática segura ainda não fazem parte deste build. Não distribuir publicamente como release estável antes de assinatura, política de atualização e testes reais.

## 8. O que ainda depende de credenciais, fornecedores ou infraestrutura

| Integração | O que precisa ser fornecido/configurado |
|---|---|
| SEFAZ | Certificado A1 válido e senha, UF, ambiente (homologação/produção), endpoints oficiais e autorização do titular. Começar exclusivamente em homologação. |
| CT-e / NFS-e | XMLs de amostra de cada padrão/provedor e município; regras de serviço/ambiente e validação fiscal apropriada. |
| E-mail transacional | Provedor SMTP/API, domínio remetente e SPF/DKIM/DMARC; segredo configurado fora do Git. |
| MFA e recuperação de conta | Decisão de política, armazenamento seguro de segredos (DPAPI/KMS/secret manager), canal de recuperação e fluxo de suporte. |
| Open Finance | Provedor autorizado, sandbox, credenciais, consentimento e contrato de integração. |
| IA opcional | Provedor/modelo, chave de API guardada localmente/secret manager, orçamento e política de dados. Nunca colocar chave no repositório. |
| Sincronização Neon | Projeto/branch de staging isolado, URL/credenciais como secrets, política de conflito e testes de restauração. Não usar o Neon de produção nesta homologação. |
| Aplicativo móvel | Escopo Android/iOS, ambiente Expo, credenciais de assinatura e backend remoto de sync. |
| Distribuição pública | Certificado de assinatura de código, política de atualização, privacidade/LGPD, suporte e revisão independente. |

## 9. Registro de defeito

Para cada problema, anote:
- Versão/build e instalador usado (NSIS/MSI).
- Windows (edição, versão e arquitetura).
- Passos exatos para reproduzir.
- Resultado esperado e resultado observado.
- Horário aproximado e captura da mensagem (oculte e-mails, valores e dados pessoais).
- Se ocorreu offline ou online.
- Se o problema se repetiu após fechar e abrir.

Não envie banco SQLite, backups, tokens, certificados, senhas ou documentos fiscais reais em um relatório de bug.

## Critério de homologação

O SFI só deve ser considerado pronto para beta pessoal depois de:
1. instalação e primeira inicialização sem ferramentas de desenvolvimento;
2. operações financeiras, backup e restauração aprovados em perfil descartável;
3. teste offline e persistência após reinício;
4. ausência de perda/duplicação de lançamentos;
5. registro e resolução de todos os defeitos bloqueadores.

A aprovação de CI no GitHub não substitui esta homologação no Windows real.
