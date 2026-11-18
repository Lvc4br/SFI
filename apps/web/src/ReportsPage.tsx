import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Summary } from "./api";

type MonthData = {month:string;income:number;expense:number;net:number};
const monthNames=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const money=(value:number,currency:string)=>new Intl.NumberFormat("pt-BR",{style:"currency",currency}).format(value);

export default function ReportsPage() {
  const [year,setYear]=useState(String(new Date().getFullYear()));
  const [currency,setCurrency]=useState("BRL");
  const [summaries,setSummaries]=useState<Summary[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    async function load(){
      setBusy(true);setError("");
      try{
        const y=Number(year);
        if(!Number.isInteger(y)||y<2000||y>2100)throw new Error("Informe um ano entre 2000 e 2100.");
        const values=await Promise.all(Array.from({length:12},(_,index)=>{
          const start=String(index+1).padStart(2,"0");
          const endDay=new Date(Date.UTC(y,index+1,0)).getUTCDate();
          return api.summary(y+"-"+start+"-01",y+"-"+start+"-"+String(endDay).padStart(2,"0"));
        }));
        if(active)setSummaries(values);
      }catch(reason){if(active)setError(reason instanceof Error?reason.message:"Não foi possível gerar o relatório.");}
      finally{if(active)setBusy(false);}
    }
    void load();
    return ()=>{active=false;};
  },[year]);
  const currencies=useMemo(()=>Array.from(new Set(summaries.flatMap(s=>s.totals_by_currency.map(x=>x.currency)))).sort(),[summaries]);
  useEffect(()=>{if(currencies.length&&!currencies.includes(currency))setCurrency(currencies.includes("BRL")?"BRL":currencies[0]);},[currencies,currency]);
  const data:MonthData[]=summaries.map((summary,index)=>{
    const row=summary.totals_by_currency.find(item=>item.currency===currency);
    return {month:monthNames[index],income:Number(row?.income_total??0),expense:Number(row?.expense_total??0),net:Number(row?.net_flow??0)};
  });
  const max=Math.max(1,...data.flatMap(x=>[x.income,x.expense]));
  const totalIncome=data.reduce((sum,x)=>sum+x.income,0);
  const totalExpense=data.reduce((sum,x)=>sum+x.expense,0);
  function exportCsv(){
    const rows=[["Mês","Moeda","Receitas","Despesas","Resultado"],...data.map(x=>[x.month,currency,x.income.toFixed(2),x.expense.toFixed(2),x.net.toFixed(2)])];
    const csv="\uFEFF"+rows.map(row=>row.map(value=>'"'+String(value).replace(/"/g,'""')+'"').join(";")).join("\r\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const link=document.createElement("a");link.href=url;link.download="sfi-relatorio-"+year+"-"+currency+".csv";link.click();URL.revokeObjectURL(url);
  }
  return <section className="content-grid">
    <section className="panel">
      <div className="panel-heading"><div><h3>Relatório anual</h3><p className="muted">Comparação mensal de receitas, despesas e resultado por moeda, sem conversão cambial.</p></div></div>
      <div className="form-row">
        <label className="field">Ano<input type="number" min="2000" max="2100" value={year} onChange={e=>setYear(e.target.value)}/></label>
        <label className="field">Moeda<select value={currency} onChange={e=>setCurrency(e.target.value)}>{(currencies.length?currencies:["BRL"]).map(item=><option key={item} value={item}>{item}</option>)}</select></label>
      </div>
      {busy&&<p className="muted" role="status">Calculando os doze períodos...</p>}
      {error&&<div className="alert error" role="alert">{error}</div>}
    </section>
    {!busy&&!error&&<section className="panel">
      <div className="panel-heading"><div><h3>Consolidado de {year}</h3><p className="muted">Totais calculados a partir das movimentações confirmadas.</p></div><button className="button secondary" type="button" onClick={exportCsv}>Exportar CSV</button></div>
      <div className="metric-grid"><article className="metric-card"><span>RECEITAS NO ANO</span><strong>{money(totalIncome,currency)}</strong></article><article className="metric-card"><span>DESPESAS NO ANO</span><strong>{money(totalExpense,currency)}</strong></article><article className="metric-card"><span>RESULTADO ANUAL</span><strong className={totalIncome-totalExpense>=0?"positive":"negative"}>{money(totalIncome-totalExpense,currency)}</strong></article></div>
      <div className="category-bars" role="group" aria-label="Comparação mensal de receitas e despesas">
        {data.map(item=><div className="bar-item" key={item.month}>
          <div><strong>{item.month}</strong><span>Receitas {money(item.income,currency)}</span></div>
          <div className="bar-track"><span style={{width:(item.income/max*100)+"%"}}/></div>
          <div><span>Despesas {money(item.expense,currency)}</span><strong className={item.net>=0?"positive":"negative"}>{money(item.net,currency)}</strong></div>
          <div className="bar-track"><span style={{width:(item.expense/max*100)+"%",background:"#bd6b5e"}}/></div>
        </div>)}
      </div>
      <div className="table-wrap"><table><caption>Dados mensais detalhados em {currency}</caption><thead><tr><th>Mês</th><th>Receitas</th><th>Despesas</th><th>Resultado</th></tr></thead><tbody>{data.map(item=><tr key={item.month}><td>{item.month}</td><td>{money(item.income,currency)}</td><td>{money(item.expense,currency)}</td><td className={item.net>=0?"positive":"negative"}>{money(item.net,currency)}</td></tr>)}</tbody></table></div>
    </section>}
  </section>;
}
