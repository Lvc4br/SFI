# Direção visual — Dashboard SFI (referências OrpioFin)

## Objetivo
Adaptar padrões visuais das imagens de referência ao SFI, sem copiar identidade ou comprometer as regras financeiras existentes.

## Padrões
- Sidebar persistente, clara e agrupada por áreas; item ativo em contraste forte.
- Fundo geral branco/cinza muito claro; cartões com borda sutil, raio moderado e sombra discreta.
- Verde escuro/emerald como acento principal, reservando cores semânticas para estados de receita/despesa e alertas.
- Hierarquia de dashboard: resumo de saldo, cards de contas/metas, fluxo de caixa e movimentações recentes.
- Gráfico com alternância de período e tooltips acessíveis.
- Cabeçalho com título contextual, filtros e ações.
- Tabelas com pesquisa, filtros, status, valores alinhados e números tabulares.
- Responsividade: sidebar adaptável, cards em coluna e tabelas com overflow/alternativa compacta.

## Aplicação ao SFI
- Não usar os dados monetários fictícios das referências.
- Usar apenas dados reais da API SFI; estados loading, empty, error e partial.
- Não duplicar nem recalcular regras financeiras no frontend.
- Garantir contraste WCAG, navegação por teclado, focus visível, labels e preferências de redução de movimento.
- Manter tokens e componentes compartilhados para consistência.
- Design deve ser validado em desktop e mobile.

## Tokens iniciais propostos (a validar na implementação)
- Accent: emerald/verde profundo.
- Canvas: neutro muito claro.
- Surface: branco.
- Text: grafite.
- Border: cinza neutro suave.
- Success / warning / danger: semânticos, não dependentes somente da cor.

## Próximos passos
1. Identificar o componente e a estrutura atual de frontend/dashboard.
2. Mapear componentes e tokens existentes antes de substituir estilos.
3. Implementar em branch separada.
4. Verificar acessibilidade, responsividade, testes e build.
