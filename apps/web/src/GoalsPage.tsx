import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Goal, GoalEntry } from "./api";

const money = (value: string, currency = "BRL") =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value));
const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [target, setTarget] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [entryType, setEntryType] = useState<"contribution" | "withdrawal">("contribution");
  const [amount, setAmount] = useState("");
  const [entryDescription, setEntryDescription] = useState("");
  const [history, setHistory] = useState<GoalEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    const result = await api.goals();
    setGoals(result);
    if (selected && !result.some(goal => goal.id === selected)) setSelected("");
  }, [selected]);
  useEffect(() => {
    void reload().catch(e => setError(e instanceof Error ? e.message : "Falha ao carregar metas."));
  }, [reload]);
  useEffect(() => {
    if (selected) void api.goalEntries(selected).then(setHistory).catch(e => setError(e instanceof Error ? e.message : "Falha ao carregar histórico."));
    else setHistory([]);
  }, [selected, goals]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const goal = await api.createGoal({
        name, description: description || null, currency: "BRL",
        target_amount: target, target_date: targetDate || null,
      });
      setName(""); setDescription(""); setTarget(""); setTargetDate("");
      setSelected(goal.id); setNotice("Meta criada."); await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível criar a meta."); }
    finally { setBusy(false); }
  }

  async function addEntry(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api.createGoalEntry(selected, {
        entry_type: entryType, amount, description: entryDescription || null,
        occurred_at: new Date().toISOString(), idempotency_key: crypto.randomUUID(),
      });
      setAmount(""); setEntryDescription("");
      setNotice(entryType === "contribution" ? "Aporte registrado." : "Retirada registrada.");
      await reload();
      setHistory(await api.goalEntries(selected));
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível registrar o movimento."); }
    finally { setBusy(false); }
  }

  async function changeStatus(goal: Goal, status: "active" | "paused" | "archived") {
    setBusy(true); setError(""); setNotice("");
    try {
      await api.updateGoal(goal.id, { status });
      setNotice(status === "archived" ? "Meta arquivada." : status === "paused" ? "Meta pausada." : "Meta reativada.");
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível atualizar a meta."); }
    finally { setBusy(false); }
  }

  const active = goals.filter(goal => goal.status !== "archived");
  const selectedGoal = active.find(goal => goal.id === selected);
  const progress = selectedGoal
    ? Math.min(100, Number(selectedGoal.current_amount) / Number(selectedGoal.target_amount) * 100)
    : 0;

  return <section className="content-grid">
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel">
      <div className="panel-heading"><div><h2>Criar objetivo</h2><p className="muted">Defina um valor e, se quiser, uma data para alcançar.</p></div></div>
      <form className="form-stack" onSubmit={create}>
        <label>Nome da meta<input value={name} onChange={e => setName(e.target.value)} maxLength={120} required placeholder="Ex.: Reserva de emergência"/></label>
        <label>Descrição (opcional)<input value={description} onChange={e => setDescription(e.target.value)} maxLength={500}/></label>
        <div className="form-row">
          <label>Valor-alvo (R$)<input type="number" min="0.01" step="0.01" value={target} onChange={e => setTarget(e.target.value)} required/></label>
          <label>Data desejada<input type="date" min={today()} value={targetDate} onChange={e => setTargetDate(e.target.value)}/></label>
        </div>
        <button className="button primary" disabled={busy || !name.trim() || !target || Number(target) <= 0}>Criar meta</button>
      </form>
    </section>
    <section className="panel">
      <div className="panel-heading"><div><h2>Suas metas</h2><p className="muted">Valores acumulados por alocações registradas.</p></div></div>
      {!active.length ? <p className="muted">Nenhuma meta cadastrada.</p> : <div className="data-list">
        {active.map(goal => {
          const pct = Math.min(100, Number(goal.current_amount) / Number(goal.target_amount) * 100);
          return <article className="data-row" key={goal.id}>
            <div className="goal-summary">
              <button className="text-button" type="button" onClick={() => setSelected(goal.id)}>{goal.name}</button>
              <small>{goal.status === "completed" ? "Concluída" : goal.status === "paused" ? "Pausada" : "Em andamento"}{goal.target_date ? " · até " + new Date(goal.target_date + "T12:00:00").toLocaleDateString("pt-BR") : ""}</small>
              <div className="progress-track"><span style={{width: pct + "%"}}/></div>
              <small>{pct.toLocaleString("pt-BR",{maximumFractionDigits:1})}% · {money(goal.current_amount)} de {money(goal.target_amount)}</small>
            </div>
            <div className="goal-actions">
              <strong>{money(goal.target_amount - Number(goal.current_amount))} restantes</strong>
              <div className="button-row">
                {goal.status === "active" ? <button className="button secondary" type="button" disabled={busy} onClick={() => void changeStatus(goal,"paused")}>Pausar</button> : goal.status === "paused" && <button className="button secondary" type="button" disabled={busy} onClick={() => void changeStatus(goal,"active")}>Retomar</button>}
                <button className="button secondary" type="button" disabled={busy} onClick={() => void changeStatus(goal,"archived")}>Arquivar</button>
              </div>
            </div>
          </article>;
        })}
      </div>}
    </section>
    <section className="panel">
      <div className="panel-heading"><div><h2>Movimentar meta</h2><p className="muted">Registre aportes ou retiradas do valor reservado.</p></div></div>
      <form className="form-stack" onSubmit={addEntry}>
        <label>Meta<select value={selected} onChange={e => setSelected(e.target.value)} required><option value="">Selecione</option>{active.filter(goal => goal.status !== "paused").map(goal => <option key={goal.id} value={goal.id}>{goal.name} · {money(goal.current_amount)}</option>)}</select></label>
        <label>Tipo de movimento<select value={entryType} onChange={e => setEntryType(e.target.value as "contribution" | "withdrawal")}><option value="contribution">Aporte</option><option value="withdrawal">Retirada</option></select></label>
        <label>Valor (R$)<input type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required/></label>
        <label>Descrição (opcional)<input value={entryDescription} onChange={e => setEntryDescription(e.target.value)} maxLength={200}/></label>
        {selectedGoal && <p className="muted">Saldo reservado: {money(selectedGoal.current_amount)}. Esta movimentação organiza a meta, mas não transfere dinheiro entre contas nem cria receita/despesa.</p>}
        <button className="button primary" disabled={busy || !selected || !amount || Number(amount) <= 0}>Registrar movimento</button>
      </form>
      <div className="panel-heading"><div><h3>Histórico</h3></div></div>
      {!history.length ? <p className="muted">Selecione uma meta para consultar os movimentos.</p> : <div className="data-list">{history.map(entry => <article className="data-row" key={entry.id}><div><strong>{entry.entry_type === "contribution" ? "Aporte" : "Retirada"}</strong><small>{entry.description || "Sem descrição"} · {new Date(entry.occurred_at).toLocaleDateString("pt-BR")}</small></div><strong>{entry.entry_type === "contribution" ? "+" : "−"} {money(entry.amount)}</strong></article>)}</div>}
    </section>
  </section>;
}
