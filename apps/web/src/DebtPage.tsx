import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Account, Debt } from "./api";

const money = (value: string, currency = "BRL") =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value));
const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

export default function DebtPage({ accounts }: { accounts: Account[] }) {
  const [debts, setDebts] = useState<Debt[]>([]);
  const [selected, setSelected] = useState("");
  const [creditor, setCreditor] = useState("");
  const [description, setDescription] = useState("");
  const [kind, setKind] = useState<Debt["debt_type"]>("other");
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState("0");
  const [installmentCount, setInstallmentCount] = useState("12");
  const [schedule, setSchedule] = useState<Awaited<ReturnType<typeof api.debtSchedule>> | null>(null);
  const [contractedAt, setContractedAt] = useState(today());
  const [firstDue, setFirstDue] = useState(today());
  const [method, setMethod] = useState<Debt["amortization_method"]>("manual");
  const [accountId, setAccountId] = useState("");
  const [principal, setPrincipal] = useState("");
  const [interest, setInterest] = useState("0.00");
  const [nextDue, setNextDue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setDebts(await api.debts());
  }, []);
  useEffect(() => { void reload().catch(e => setError(e instanceof Error ? e.message : "Falha ao carregar dívidas.")); }, [reload]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      await api.createDebt({
        creditor, debt_type: kind, description, currency: "BRL",
        original_amount: amount, annual_interest_rate: rate,
        amortization_method: method, contracted_at: contractedAt,
        first_due_date: firstDue, installment_count: method === "manual" ? null : Number(installmentCount),
      });
      setCreditor(""); setDescription(""); setAmount(""); setRate("0"); setSchedule(null);
      setNotice("Dívida cadastrada."); await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível cadastrar."); }
    finally { setBusy(false); }
  }

  async function pay(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api.payDebt(selected, {
        source_account_id: accountId, principal_amount: principal,
        interest_amount: interest, paid_at: new Date().toISOString(),
        next_due_date: nextDue || null, idempotency_key: crypto.randomUUID(),
      });
      setPrincipal(""); setInterest("0.00"); setNextDue(""); setSchedule(null);
      setNotice("Pagamento registrado e despesa lançada na conta."); await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível registrar o pagamento."); }
    finally { setBusy(false); }
  }

  const active = debts.filter(debt => debt.status === "active");
  const selectedDebt = active.find(debt => debt.id === selected);
  async function loadSchedule() {
    if (!selected) return;
    setBusy(true); setError(""); setSchedule(null);
    try { setSchedule(await api.debtSchedule(selected)); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível calcular a projeção."); }
    finally { setBusy(false); }
  }
  const paymentAccounts = accounts.filter(account => !account.archived_at && account.account_type !== "credit" && account.currency === (selectedDebt?.currency ?? "BRL"));

  return <section className="content-grid">
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel">
      <div className="panel-heading"><div><h2>Cadastrar obrigação</h2><p className="muted">Empréstimos, financiamentos e dívidas pessoais.</p></div></div>
      <form className="form-stack" onSubmit={create}>
        <label>Credor<input value={creditor} onChange={e => setCreditor(e.target.value)} maxLength={120} required /></label>
        <label>Descrição<input value={description} onChange={e => setDescription(e.target.value)} maxLength={160} required /></label>
        <div className="form-row">
          <label>Tipo<select value={kind} onChange={e => setKind(e.target.value as Debt["debt_type"])}><option value="other">Outro</option><option value="loan">Empréstimo</option><option value="financing">Financiamento</option><option value="personal">Pessoal</option><option value="mortgage">Imobiliário</option><option value="vehicle">Veículo</option></select></label>
          <label>Amortização informada<select value={method} onChange={e => { setMethod(e.target.value as Debt["amortization_method"]); setSchedule(null); }}><option value="manual">Manual</option><option value="price">Price</option><option value="sac">SAC</option></select></label>
        </div>
        <div className="form-row">
          <label>Valor original (R$)<input type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required /></label>
          <label>Taxa anual (%)<input type="number" min="0" step="0.000001" value={rate} onChange={e => setRate(e.target.value)} /></label>
        </div>
        <div className="form-row">
          <label>Contratação<input type="date" value={contractedAt} onChange={e => setContractedAt(e.target.value)} required /></label>
          <label>Primeiro vencimento<input type="date" value={firstDue} onChange={e => setFirstDue(e.target.value)} required /></label>
        </div>
        <button className="button primary" disabled={busy || !creditor.trim() || !description.trim() || !amount || Number(amount) <= 0}>Cadastrar dívida</button>
      </form>
    </section>
    <section className="panel">
      <div className="panel-heading"><div><h2>Obrigações registradas</h2><p className="muted">Saldo principal em aberto e próximos vencimentos.</p></div></div>
      {debts.length === 0 ? <p className="muted">Nenhuma dívida cadastrada.</p> : <div className="data-list">
        {debts.map(debt => <article className="data-row" key={debt.id}>
          <div><strong>{debt.description}</strong><small>{debt.creditor} · {debt.debt_type} · {debt.status}</small></div>
          <div><strong>{money(debt.outstanding_principal, debt.currency)}</strong><small>{debt.next_due_date ? `Vence em ${new Date(debt.next_due_date + "T12:00:00").toLocaleDateString("pt-BR")}` : "Sem vencimentos pendentes"}</small></div>
        </article>)}
      </div>}
    </section>
    <section className="panel">
      <div className="panel-heading"><div><h2>Registrar pagamento</h2><p className="muted">Separe amortização e juros para preservar a composição.</p></div></div>
      <form className="form-stack" onSubmit={pay}>
        <label>Dívida<select value={selected} onChange={e => { setSelected(e.target.value); setSchedule(null); }} required><option value="">Selecione</option>{active.map(debt => <option key={debt.id} value={debt.id}>{debt.description} · saldo {money(debt.outstanding_principal, debt.currency)}</option>)}</select></label>
        {selectedDebt && selectedDebt.amortization_method !== "manual" && <button className="button secondary" type="button" disabled={busy} onClick={() => void loadSchedule()}>Calcular cronograma estimado</button>}
        <label>Conta de origem<select value={accountId} onChange={e => setAccountId(e.target.value)} required><option value="">Selecione</option>{paymentAccounts.map(account => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
        <div className="form-row">
          <label>Amortização (R$)<input type="number" min="0.01" step="0.01" value={principal} onChange={e => setPrincipal(e.target.value)} required /></label>
          <label>Juros (R$)<input type="number" min="0" step="0.01" value={interest} onChange={e => setInterest(e.target.value)} required /></label>
        </div>
        <label>Próximo vencimento (se houver)<input type="date" value={nextDue} onChange={e => setNextDue(e.target.value)} /></label>
        <p className="muted">Total da saída: {money((Number(principal || 0) + Number(interest || 0)).toFixed(2), selectedDebt?.currency ?? "BRL")}</p>
        <button className="button primary" disabled={busy || !selected || !accountId || !principal || Number(principal) <= 0}>Registrar pagamento</button>
      </form>
      {schedule && <section aria-live="polite">
        <h3>Projeção {schedule.method.toUpperCase()} — estimativa</h3>
        <div className="metric-grid">
          <article className="metric-card"><span className="eyebrow">PRINCIPAL</span><strong>{money(schedule.principal_total, schedule.currency)}</strong></article>
          <article className="metric-card"><span className="eyebrow">JUROS ESTIMADOS</span><strong>{money(schedule.interest_total, schedule.currency)}</strong></article>
          <article className="metric-card"><span className="eyebrow">TOTAL ESTIMADO</span><strong>{money(schedule.payment_total, schedule.currency)}</strong></article>
        </div>
        <div className="table-wrap"><table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Amortização</th><th>Juros</th><th>Prestação</th><th>Saldo</th></tr></thead>
          <tbody>{schedule.installments.map(item => <tr key={item.number}><td>{item.number}</td><td>{new Date(item.due_date + "T12:00:00").toLocaleDateString("pt-BR")}</td><td>{money(item.principal, schedule.currency)}</td><td>{money(item.interest, schedule.currency)}</td><td>{money(item.payment, schedule.currency)}</td><td>{money(item.closing_balance, schedule.currency)}</td></tr>)}</tbody>
        </table></div>
        <ul className="muted">{schedule.assumptions.map(item => <li key={item}>{item}</li>)}</ul>
      </section>}
    </section>
  </section>;
}
