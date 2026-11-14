# Escopo do MVP — SFI

**Status:** especificação de produto para orientar a primeira versão utilizável.  
**Regra:** este documento recorta a primeira entrega; não substitui nem elimina o escopo completo de 19 módulos do produto.

## 1. Resultado esperado

Entregar uma aplicação Web responsiva na qual uma pessoa consiga criar uma conta, entrar com segurança, cadastrar suas contas financeiras, organizar categorias, registrar receitas e despesas, fazer transferências, planejar limites mensais e compreender a própria situação financeira.

O MVP não é apenas um CRUD. Cada jornada deve oferecer três camadas complementares:

1. **Operacional:** registrar, consultar, corrigir por fluxo auditável e organizar informações.
2. **Analítica:** calcular saldos, totais, comparações e projeções com regras determinísticas.
3. **Educacional:** explicar o significado dos números, conceitos relevantes e limites das interpretações, sem julgamento.

## 2. Público e princípios de experiência

- Iniciantes em organização financeira devem conseguir começar sem conhecer termos técnicos.
- Usuários experientes não devem ficar presos a fluxos simplistas.
- Linguagem clara, neutra, inclusiva e sem culpabilização.
- Não presumir que toda receita é salário ou que toda despesa é mensal.
- Separar valores realizados, planejados, estimados e projetados.
- Exibir moeda e período em todo indicador financeiro relevante.
- A interface deve funcionar em celular, tablet e desktop.

## 3. Incluído no MVP

### 3.1 Identidade e sessão
- Cadastro, login, logout, renovação de sessão e perfil autenticado já existentes na API.
- Interface para cadastro e login.
- Estados de carregamento, erro, sessão expirada e saída.
- Nunca armazenar senha ou segredo no cliente.
- Recuperação de senha, verificação de e-mail e MFA permanecem requisitos de evolução antes de uma exposição pública ampla.

### 3.2 Contas
- Listar, cadastrar e editar dados permitidos de contas.
- Exibir tipo, nome, instituição opcional, moeda e saldo calculado.
- Diferenciar dinheiro disponível, contas de crédito e obrigações.
- Limite de crédito não é renda nem saldo disponível.
- Não permitir que o cliente envie ou altere saldo calculado diretamente.

### 3.3 Categorias
- Listar categorias padrão e personalizadas.
- Criar e editar categorias de receita ou despesa.
- Impedir associação de categoria incompatível com o tipo de movimentação.
- Preparar metadados educacionais: essencialidade, frequência e natureza, sem obrigar preenchimento no primeiro cadastro.

### 3.4 Movimentações
- Registrar e consultar receitas e despesas.
- Filtrar por período, conta, categoria, tipo e faixa de valor.
- Exibir detalhes e histórico.
- Transferências internas devem ser uma operação própria e neutra para o resultado consolidado.
- Corrigir movimentações confirmadas por estorno/lançamento compensatório, nunca por sobrescrita silenciosa.
- Recorrências futuras devem ser identificadas como projeções, não como lançamentos realizados.

### 3.5 Orçamento mensal
- Criar e consultar limite mensal por categoria de despesa.
- Exibir limite, realizado, restante e percentual utilizado.
- Distinguir orçamento planejado de gasto efetivo.
- Alertas devem ser informativos e configuráveis, sem linguagem punitiva.

### 3.6 Dashboard
- Resumo do período selecionado.
- Saldos por conta e total consolidado por moeda.
- Receitas, despesas e resultado do período.
- Orçamento planejado versus realizado.
- Próximos compromissos recorrentes como projeções.
- Acesso rápido às ações principais.
- Explicações curtas sobre os indicadores e suas limitações.

### 3.7 Educação contextual
- Glossário e explicações vinculados às telas.
- Conteúdo inicial sobre orçamento, fluxo de caixa, saldo, receita, despesa, transferência, dívida, reserva e juros.
- Dicas não prescritivas baseadas em regras explícitas.
- Não exigir um curso completo para utilizar as funções financeiras.

## 4. Fora do MVP

Permanecem no roadmap maior, sem serem descartados:
- Cartões de crédito completos, faturas, fechamento e pagamento com conciliação.
- Importação automática de extratos e Open Finance.
- Conciliação bancária avançada.
- Dívidas com cronogramas completos e estratégias de quitação.
- Objetivos, reserva de emergência e patrimônio.
- Cursos, avaliações e trilhas educacionais completas.
- Calculadoras avançadas.
- Investimentos, indicadores econômicos e rentabilidade.
- Compras, documentos fiscais, OCR, estoque e inteligência de preços.
- Assistente de IA.
- Sincronização offline e clientes Desktop/Mobile nativos.

## 5. Regras de produto inegociáveis

- O backend é a autoridade para autorização, cálculos e persistência.
- Valores monetários usam Decimal no domínio e NUMERIC no banco.
- Não misturar moedas em um total sem conversão explícita e fonte/taxa identificada.
- Uma transferência entre contas próprias não é receita nem despesa consolidada.
- Não confundir saldo de conta, fluxo de caixa, resultado do período e patrimônio líquido.
- Projeções não podem ser apresentadas como fatos realizados.
- Dados de um usuário nunca podem ser consultados por outro.
- Operações mutáveis devem tratar repetição de requisição e idempotência.
- Toda ação sensível deve ter confirmação, validação e resposta compreensível.
- Não executar pagamentos ou ordens de investimento.

## 6. Critério de conclusão do MVP

O MVP será considerado funcional quando uma pessoa puder completar a jornada principal de ponta a ponta na Web, com dados persistidos no Neon, sem intervenção manual no banco, e quando os critérios de aceite e testes deste pacote forem cumpridos. Um build verde ou endpoints isolados não significam, por si só, produto concluído.

## 7. Dependências e lacunas a validar

Antes de considerar a especificação fechada para implementação:
- Confirmar contratos e métodos HTTP de todos os endpoints existentes.
- Confirmar suporte de CRUD de contas e categorias, incluindo edição e exclusão segura.
- Confirmar comportamento de saldo inicial, ajustes e contas de crédito.
- Definir semântica de período e timezone do usuário.
- Confirmar limites e paginação das consultas.
- Avaliar recuperação de senha e verificação de e-mail antes de beta público.
- Validar acessibilidade e linguagem com usuários iniciantes.
