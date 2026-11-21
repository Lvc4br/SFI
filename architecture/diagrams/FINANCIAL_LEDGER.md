# Modelo conceitual — fluxo de registro financeiro

```mermaid
flowchart TD
  CMD[Comando do usuário] --> AUTH[Autorização / tenant]
  AUTH --> VALID[Validar moeda, valor, conta e estado]
  VALID --> IDEM[Idempotência / deduplicação]
  IDEM --> TX[Transação atômica]
  TX --> ENTRY[Registro imutável / ledger]
  TX --> BAL[Saldo / projeção derivada]
  TX --> AUD[Audit event]
  TX --> OUT[Outbox para integrações]
  ENTRY --> VIEW[Dashboard / relatórios]
  BAL --> VIEW
```

Diagrama conceitual. Verificar se o código atual usa ledger imutável, projeções, audit event e outbox; não inferir implementação a partir desta representação.

## Regras de qualidade do domínio

- Valores exatos: Decimal/Numeric ou integer minor units com moeda e política de arredondamento documentada.
- Toda mutação financeira deve ser autorizada, atômica, idempotente e rastreável.
- Correções: reversão ou compensação auditável, não apagar histórico silenciosamente.
- Não misturar transações reais, estimativas, projeções e simulações.
- Transferências internas não representam receita/despesa consolidada.
- Validar consistência entre ledger, saldos e relatórios.