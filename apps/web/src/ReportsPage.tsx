import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Summary } from "./api";

type MonthData = { month: string; income: bigint; expense: bigint; net: bigint };
type CategoryData = { id: string; name: string; amount: bigint };
const monthNames = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const cents = (value: string): bigint => {
  const negative = value.startsWith("-");
  const normalized = negative ? value.slice(1) : value;
  const [units, fraction = ""] = normalized.split(".");
  const amount = BigInt(units || "0") * 100n + BigInt((fraction + "00").slice(0, 2));
  return negative ? -amount : amount;
};
const decimal = (value: bigint): string => {
  const absolute = value < 0n ? -value : value;
  return (value < 0n ? "-" : "") + (absolute / 100n).toString() + "." + String(absolute % 100n).padStart(2, "0");
};
const money = (value: bigint, currency: string): string => {
  const absolute = value < 0n ? -value : value;
  const formatter = new Intl.NumberFormat("pt-BR", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const parts = formatter.formatToParts(0);
  const integerIndex = parts.findIndex(part => part.type === "integer");
  const fractionIndex = parts.findIndex(part => part.type === "fraction");
  const prefix = parts.slice(0, integerIndex).map(part => part.value).join("");
  const suffix = parts.slice(fractionIndex + 1).map(part => part.value).join("");
  const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(absolute / 100n);
  return (value < 0n ? "-" : "") + prefix + integer + "," + String(absolute % 100n).padStart(2, "0") + suffix;
};
const percentageChange = (current: bigint, previous: bigint): string => {
  if (previous === 0n) return current === 0n ? "0,0%" : "Sem base anterior";
  const basisPoints = (current - previous) * 10000n / (previous < 0n ? -previous : previous);
  const sign = basisPoints > 0n ? "+" : "";
  const absolute = basisPoints < 0n ? -basisPoints : basisPoints;
  return sign + (basisPoints < 0n ? "-" : "") + (absolute / 100n).toString() + "," + String(absolute % 100n).padStart(2, "0") + "%";
};

export default function ReportsPage() {
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [currency, setCurrency] = useState("BRL");
  const [comparePreviousYear, setComparePreviousYear] = useState(false);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [previousSummaries, setPreviousSummaries] = useState<Summary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      setBusy(true);
      setError("");
      try {
        const selectedYear = Number(year);
        if (!Number.isInteger(selectedYear) || selectedYear < 2000 || selectedYear > 2100) {
          throw new Error("Informe um ano entre 2000 e 2100.");
        }
        const loadYear = (targetYear: number) => Promise.all(Array.from({ length: 12 }, (_, index) => {
          const month = String(index + 1).padStart(2, "0");
          const endDay = new Date(Date.UTC(targetYear, index + 1, 0)).getUTCDate();
          return api.summary(targetYear + "-" + month + "-01", targetYear + "-" + month + "-" + String(endDay).padStart(2, "0"));
        }));
        const [current, previous] = await Promise.all([
          loadYear(selectedYear),
          comparePreviousYear ? loadYear(selectedYear - 1) : Promise.resolve([] as Summary[]),
        ]);
        if (active) {
          setSummaries(current);
          setPreviousSummaries(previous);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Não foi possível gerar o relatório.");
      } finally {
        if (active) setBusy(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [year, comparePreviousYear]);

  const currencies = useMemo(
    () => Array.from(new Set(summaries.flatMap(summary => summary.totals_by_currency.map(item => item.currency)))).sort(),
    [summaries],
  );
  useEffect(() => {
    if (currencies.length && !currencies.includes(currency)) setCurrency(currencies.includes("BRL") ? "BRL" : currencies[0]);
  }, [currencies, currency]);

  const toMonths = (values: Summary[]): MonthData[] => values.map((summary, index) => {
    const row = summary.totals_by_currency.find(item => item.currency === currency);
    const income = cents(row?.income_total ?? "0.00");
    const expense = cents(row?.expense_total ?? "0.00");
    return { month: monthNames[index], income, expense, net: income - expense };
  });
  const data = toMonths(summaries);
  const previousData = toMonths(previousSummaries);
  const aggregate = (items: MonthData[]) => ({
    income: items.reduce((sum, item) => sum + item.income, 0n),
    expense: items.reduce((sum, item) => sum + item.expense, 0n),
    net: items.reduce((sum, item) => sum + item.net, 0n),
  });
  const totals = aggregate(data);
  const previousTotals = aggregate(previousData);
  const max = data.reduce((value, item) => item.income > value ? item.income : item.expense > value ? item.expense : value, 0n);
  const width = (value: bigint) => max === 0n ? 0 : Number(value * 10000n / max) / 100;
  const categoryTotals = new Map<string, CategoryData>();
  for (const summary of summaries) {
    for (const item of summary.spending_by_category) {
      if (item.currency !== currency) continue;
      const existing = categoryTotals.get(item.category_id);
      categoryTotals.set(item.category_id, {
        id: item.category_id,
        name: item.category_name,
        amount: (existing?.amount ?? 0n) + cents(item.amount),
      });
    }
  }
  const categories = Array.from(categoryTotals.values()).sort((a, b) => a.amount > b.amount ? -1 : a.amount < b.amount ? 1 : a.name.localeCompare(b.name, "pt-BR"));
  const categoryTotal = categories.reduce((sum, item) => sum + item.amount, 0n);
  const categoryWidth = (value: bigint) => categoryTotal === 0n ? 0 : Number(value * 10000n / categoryTotal) / 100;

  function exportCsv() {
    const rows = [
      ["Tipo", "Período", "Moeda", "Categoria", "Receitas", "Despesas", "Resultado"],
      ...data.map(item => ["Mensal", item.month + "/" + year, currency, "", decimal(item.income), decimal(item.expense), decimal(item.net)]),
      ...categories.map(item => ["Categoria", year, currency, item.name, "", decimal(item.amount), ""]),
    ];
    const csv = "\uFEFF" + rows.map(row => row.map(value => '"' + String(value).replace(/"/g, '""') + '"').join(";")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "sfi-relatorio-" + year + "-" + currency + ".csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return <section className="content-grid">
    <section className="panel">
      <div className="panel-heading"><div><h3>Relatórios e análises</h3><p className="muted">Receitas, despesas, resultado e concentração de gastos por categoria. Cada moeda é analisada separadamente.</p></div></div>
      <div className="form-row">
        <label className="field">Ano<input type="number" min="2000" max="2100" value={year} onChange={event => setYear(event.target.value)} /></label>
        <label className="field">Moeda<select value={currency} onChange={event => setCurrency(event.target.value)}>{(currencies.length ? currencies : ["BRL"]).map(item => <option key={item} value={item}>{item}</option>)}</select></label>
      </div>
      <label className="checkbox-field"><input type="checkbox" checked={comparePreviousYear} onChange={event => setComparePreviousYear(event.target.checked)} /> Comparar com o ano anterior</label>
      {busy && <p className="muted" role="status">Calculando os períodos selecionados...</p>}
      {error && <div className="alert error" role="alert">{error}</div>}
    </section>
    {!busy && !error && <section className="panel">
      <div className="panel-heading"><div><h3>Consolidado de {year}</h3><p className="muted">Totais calculados a partir das movimentações confirmadas.</p></div><button className="button secondary" type="button" onClick={exportCsv}>Exportar CSV</button></div>
      <div className="metric-grid">
        <article className="metric-card"><span>RECEITAS NO ANO</span><strong>{money(totals.income, currency)}</strong>{comparePreviousYear && <small className="muted">vs. {money(previousTotals.income, currency)} ({percentageChange(totals.income, previousTotals.income)})</small>}</article>
        <article className="metric-card"><span>DESPESAS NO ANO</span><strong>{money(totals.expense, currency)}</strong>{comparePreviousYear && <small className="muted">vs. {money(previousTotals.expense, currency)} ({percentageChange(totals.expense, previousTotals.expense)})</small>}</article>
        <article className="metric-card"><span>RESULTADO ANUAL</span><strong className={totals.net >= 0n ? "positive" : "negative"}>{money(totals.net, currency)}</strong>{comparePreviousYear && <small className="muted">vs. {money(previousTotals.net, currency)} ({percentageChange(totals.net, previousTotals.net)})</small>}</article>
      </div>
      <div className="category-bars" role="group" aria-label="Comparação mensal de receitas e despesas">
        {data.map(item => <div className="bar-item" key={item.month}>
          <div><strong>{item.month}</strong><span>Receitas {money(item.income, currency)}</span></div>
          <div className="bar-track"><span style={{ width: width(item.income) + "%" }} /></div>
          <div><span>Despesas {money(item.expense, currency)}</span><strong className={item.net >= 0n ? "positive" : "negative"}>{money(item.net, currency)}</strong></div>
          <div className="bar-track"><span style={{ width: width(item.expense) + "%", background: "#bd6b5e" }} /></div>
        </div>)}
      </div>
      <div className="table-wrap"><table><caption>Dados mensais detalhados em {currency}</caption><thead><tr><th>Mês</th><th>Receitas</th><th>Despesas</th><th>Resultado</th></tr></thead><tbody>{data.map(item => <tr key={item.month}><td>{item.month}</td><td>{money(item.income, currency)}</td><td>{money(item.expense, currency)}</td><td className={item.net >= 0n ? "positive" : "negative"}>{money(item.net, currency)}</td></tr>)}</tbody></table></div>
    </section>}
    {!busy && !error && <section className="panel">
      <div className="panel-heading"><div><h3>Despesas por categoria</h3><p className="muted">Distribuição das despesas confirmadas no ano selecionado.</p></div></div>
      {categories.length ? <>
        <div className="category-bars" role="group" aria-label="Participação das categorias nas despesas">
          {categories.map(item => <div className="bar-item" key={item.id}>
            <div><strong>{item.name}</strong><span>{money(item.amount, currency)} · {categoryTotal ? (Number(item.amount * 10000n / categoryTotal) / 100).toFixed(2).replace(".", ",") : "0,00"}%</span></div>
            <div className="bar-track"><span style={{ width: categoryWidth(item.amount) + "%" }} /></div>
          </div>)}
        </div>
        <div className="table-wrap"><table><caption>Ranking de despesas por categoria em {currency}</caption><thead><tr><th>Categoria</th><th>Despesas</th><th>Participação</th></tr></thead><tbody>{categories.map(item => <tr key={item.id}><td>{item.name}</td><td>{money(item.amount, currency)}</td><td>{categoryTotal ? (Number(item.amount * 10000n / categoryTotal) / 100).toFixed(2).replace(".", ",") : "0,00"}%</td></tr>)}</tbody></table></div>
      </> : <p className="muted">Não há despesas categorizadas nesta moeda e período.</p>}
    </section>}
  </section>;
}
