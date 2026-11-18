import {useEffect,useState} from "react";
import type {ChangeEvent} from "react";
import {api,type Account,type BankStatementEntry,type ReconciliationSuggestion,type ReconciliationSummary} from "./api";

type Format="csv"|"json"|"ofx";
const money=(value:string,currency:string)=>new Intl.NumberFormat("pt-BR",{style:"currency",currency}).format(Number(value));
const date=(value:string)=>new Date(value).toLocaleDateString("pt-BR");

export default function ReconciliationPage({accounts}:{accounts:Account[]}){
 const [accountId,setAccountId]=useState(accounts[0]?.id??"");
 const [format,setFormat]=useState<Format>("csv"),[content,setContent]=useState(""),[filename,setFilename]=useState("");
 const [entries,setEntries]=useState<BankStatementEntry[]>([]),[summary,setSummary]=useState<ReconciliationSummary|null>(null);
 const [activeEntry,setActiveEntry]=useState<string|null>(null),[suggestions,setSuggestions]=useState<ReconciliationSuggestion[]>([]);
 const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 async function reload(){
  const [rows,totals]=await Promise.all([api.reconciliationEntries(accountId||undefined),api.reconciliationSummary()]);
  setEntries(rows);setSummary(totals);
 }
 useEffect(()=>{void reload().catch(e=>setError(e instanceof Error?e.message:"Falha ao carregar conciliação."));},[accountId]);
 async function chooseFile(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  const ext=file.name.toLowerCase().split(".").pop();
  if(ext!=="csv"&&ext!=="json"&&ext!=="ofx"){setError("Selecione um arquivo CSV, JSON ou OFX.");return;}
  if(file.size>5*1024*1024){setError("O extrato excede 5 MB.");return;}
  try{setContent(await file.text());setFilename(file.name);setFormat(ext);setError("");setNotice("Arquivo carregado. A importação criará itens pendentes, sem criar movimentações.");}
  catch{setError("Não foi possível ler o arquivo.");}
 }
 async function importStatement(){
  if(!accountId||!content.trim())return;
  setBusy(true);setError("");setNotice("");
  try{
   const result=await api.reconciliationImport({format,content,account_id:accountId});
   setNotice(`Extrato importado: ${result.created} registros novos; ${result.duplicates_skipped} duplicados ignorados.`);
   setContent("");setFilename("");setActiveEntry(null);await reload();
  }catch(e){setError(e instanceof Error?e.message:"Falha ao importar extrato.");}
  finally{setBusy(false);}
 }
 async function loadSuggestions(entryId:string){
  setBusy(true);setError("");setActiveEntry(entryId);
  try{setSuggestions(await api.reconciliationSuggestions(entryId));}
  catch(e){setError(e instanceof Error?e.message:"Falha ao buscar correspondências.");}
  finally{setBusy(false);}
 }
 async function perform(action:()=>Promise<unknown>,message:string){
  setBusy(true);setError("");setNotice("");
  try{await action();setNotice(message);setActiveEntry(null);await reload();}
  catch(e){setError(e instanceof Error?e.message:"Não foi possível atualizar a conciliação.");}
  finally{setBusy(false);}
 }
 const totals=summary?.entries_by_currency??[];
 const pending=entries.filter(x=>x.status==="pending").length;
 const matched=entries.filter(x=>x.status==="matched").length;
 const ignored=entries.filter(x=>x.status==="ignored").length;
 return <section className="content-grid reconciliation-page">
  <div className="welcome-row"><div><h2>Compare o extrato com seus lançamentos.</h2><p className="muted">A conciliação não cria nem altera movimentações. Você confirma cada correspondência manualmente.</p></div></div>
  {notice&&<div className="alert success" role="status">{notice}</div>}{error&&<div className="alert error" role="alert">{error}</div>}
  <div className="metric-grid"><article className="metric-card"><span>AGUARDANDO</span><strong>{pending}</strong><small>Registros sem correspondência</small></article><article className="metric-card"><span>CONCILIADOS</span><strong>{matched}</strong><small>Correspondências confirmadas</small></article><article className="metric-card"><span>IGNORADOS</span><strong>{ignored}</strong><small>Registros fora da conciliação</small></article></div>
  <section className="panel"><div className="panel-heading"><div><h2>Importar extrato</h2><p>CSV, JSON ou OFX · até 5 MB · sem criar receitas ou despesas</p></div></div>
   <div className="form-stack">
    <div className="form-row"><label className="field"><span>Conta bancária</span><select value={accountId} onChange={e=>setAccountId(e.target.value)}><option value="">Selecione</option>{accounts.filter(a=>a.account_type!=="credit").map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</select></label><label className="field"><span>Arquivo de extrato</span><input type="file" accept=".csv,.json,.ofx" onChange={e=>void chooseFile(e)}/></label></div>
    {filename&&<p className="form-hint">Arquivo: {filename} · Formato: {format.toUpperCase()}</p>}
    <button className="button primary" type="button" disabled={busy||!accountId||!content.trim()} onClick={()=>void importStatement()}>Importar registros do extrato</button>
    <small className="form-hint">O SFI guarda os dados necessários à conciliação. Registros repetidos são ignorados por identificador externo ou impressão digital.</small>
   </div>
  </section>
  <section className="panel"><div className="panel-heading"><div><h2>Registros do extrato</h2><p>Até 500 registros mais recentes da conta selecionada</p></div><button className="button secondary" type="button" disabled={busy} onClick={()=>void reload()}>Atualizar</button></div>
   {!entries.length?<p className="muted">Importe um extrato para começar a conciliação.</p>:<div className="data-list">{entries.map(entry=><article className="reconciliation-entry" key={entry.id}>
    <div className="reconciliation-entry-main"><div><strong>{entry.description}</strong><small>{date(entry.occurred_at)} · {entry.external_id??"Sem ID bancário"} · {entry.transaction_type==="expense"?"Débito":"Crédito"}</small></div><div className="reconciliation-entry-value"><strong>{money(entry.amount,entry.currency)}</strong><span className={entry.status==="matched"?"status":"status over"}>{entry.status==="matched"?"Conciliado":entry.status==="ignored"?"Ignorado":"Pendente"}</span></div></div>
    <div className="button-row">{entry.status==="pending"&&<><button className="button secondary" type="button" disabled={busy} onClick={()=>void loadSuggestions(entry.id)}>Buscar correspondências</button><button className="button secondary" type="button" disabled={busy} onClick={()=>void perform(()=>api.reconciliationIgnore(entry.id),"Registro ignorado.")}>Ignorar</button></>}{entry.status==="matched"&&<button className="button secondary" type="button" disabled={busy} onClick={()=>void perform(()=>api.reconciliationUnmatch(entry.id),"Conciliação desfeita.")}>Desfazer conciliação</button>}</div>
    {activeEntry===entry.id&&<div className="reconciliation-suggestions"><strong>Correspondências sugeridas</strong>{suggestions.length?<div className="data-list">{suggestions.map(s=><div className="data-row" key={s.transaction_id}><div><strong>{s.description}</strong><small>{date(s.occurred_at)} · diferença de {s.date_difference_days} dia(s) · similaridade {Math.round(s.description_similarity*100)}%</small></div><div className="reconciliation-entry-value"><strong>{money(s.amount,s.currency)}</strong><small>Compatibilidade {s.score}%</small><button className="button primary" type="button" disabled={busy} onClick={()=>void perform(()=>api.reconciliationMatch(entry.id,s.transaction_id),"Movimentação conciliada.")}>Confirmar</button></div></div>)}</div>:<p className="muted">Nenhuma correspondência exata encontrada em até 7 dias. Você pode revisar a movimentação ou deixá-la pendente.</p>}</div>}
   </article>)}</div>}
  </section>
  {totals.length>0&&<section className="panel"><div className="panel-heading"><div><h2>Resumo por moeda</h2><p>Contagem de registros importados</p></div></div><div className="currency-summary-grid">{totals.map(x=><article key={x.currency}><span>{x.currency}</span><strong>{x.pending} pendentes</strong><small>{x.matched} conciliados · {x.ignored} ignorados</small></article>)}</div></section>}
 </section>;
}
