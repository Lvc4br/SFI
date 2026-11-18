import {useState} from "react";
import type {ChangeEvent,FormEvent} from "react";
import {api,type Account,type Category,type ExchangePreview,type BackupDocument,type BackupPreview} from "./api";

type ImportFormat="csv"|"json"|"ofx"|"xlsx";
export default function DataExchangePage({accounts,categories}:{accounts:Account[];categories:Category[]}){
 const [format,setFormat]=useState<ImportFormat>("csv"),[content,setContent]=useState(""),[filename,setFilename]=useState("");
 const [accountId,setAccountId]=useState(accounts[0]?.id??""),[categoryId,setCategoryId]=useState("");
 const [preview,setPreview]=useState<ExchangePreview|null>(null),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [busy,setBusy]=useState(false);\n const [backup,setBackup]=useState<BackupDocument|null>(null),[backupPreview,setBackupPreview]=useState<BackupPreview|null>(null);\n const [backupFilename,setBackupFilename]=useState(""),[backupError,setBackupError]=useState(""),[backupNotice,setBackupNotice]=useState("");
 async function chooseFile(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setError("");setNotice("");setPreview(null);
  const extension=file.name.toLowerCase().split(".").pop();
  if(extension!=="csv"&&extension!=="json"&&extension!=="ofx"&&extension!=="xlsx"){setError("Formato não suportado. Use CSV, JSON, OFX ou XLSX.");return;}
  if(file.size>5*1024*1024){setError("O arquivo excede o limite de 5 MB.");return;}
  try{
   if(extension==="xlsx"){
    const bytes=new Uint8Array(await file.arrayBuffer());let binary="";
    for(let offset=0;offset<bytes.length;offset+=0x8000){binary+=String.fromCharCode(...bytes.subarray(offset,offset+0x8000));}
    setContent(btoa(binary));
   }else{setContent(await file.text());}
   setFilename(file.name);setFormat(extension);setNotice("Arquivo carregado. Gere a prévia antes de confirmar.");
  }
  catch{setError("Não foi possível ler o arquivo selecionado.");}
 }
 async function makePreview(event?:FormEvent){
  event?.preventDefault();setBusy(true);setError("");setNotice("");
  try{const result=await api.exchangePreview({format,content,default_account_id:accountId||null,default_category_id:categoryId||null});setPreview(result);setNotice("Prévia calculada. Nenhum dado foi gravado.");}
  catch(e){setError(e instanceof Error?e.message:"Falha ao analisar o arquivo.");}
  finally{setBusy(false);}
 }
 async function confirmImport(){
  if(!preview||preview.invalid>0||preview.valid===0)return;
  setBusy(true);setError("");setNotice("");
  try{
   const result=await api.exchangeImport({format,content,default_account_id:accountId||null,default_category_id:categoryId||null,confirmed:true});
   setNotice(`Importação concluída: ${result.created} registros criados; ${result.duplicates_skipped} duplicados ignorados.`);
   await makePreview();
  }catch(e){setError(e instanceof Error?e.message:"Falha ao importar movimentações.");}
  finally{setBusy(false);}
 }
 async function download(formatOut:"csv"|"json"|"xlsx"){
  setBusy(true);setError("");
  try{const blob=await api.exportTransactions(formatOut);const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`sfi-transactions.${formatOut}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setNotice(`Exportação ${formatOut.toUpperCase()} gerada.`);}
  catch(e){setError(e instanceof Error?e.message:"Falha ao exportar movimentações.");}
  finally{setBusy(false);}
 }

 async function downloadBackup(){
  setBusy(true);setBackupError("");setBackupNotice("");
  try{const blob=await api.exportFullBackup();const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="sfi-backup.json";document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setBackupNotice("Backup completo gerado. Guarde o arquivo em local seguro.");}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao gerar backup completo.");}
  finally{setBusy(false);}
 }
 async function chooseBackup(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setBackup(null);setBackupPreview(null);setBackupError("");setBackupNotice("");
  if(file.size>50*1024*1024){setBackupError("O backup excede o limite de 50 MB.");return;}
  try{
   const parsed=JSON.parse(await file.text()) as BackupDocument;
   if(parsed.format!=="sfi-personal-data"||parsed.version!==1||!parsed.tables)throw new Error("Arquivo não é um backup SFI compatível.");
   setBackup(parsed);setBackupFilename(file.name);setBackupNotice("Arquivo carregado. Analise a prévia antes de restaurar.");
  }catch(e){setBackupError(e instanceof Error?e.message:"Não foi possível ler o backup.");}
 }
 async function previewBackup(){
  if(!backup)return;setBusy(true);setBackupError("");setBackupNotice("");
  try{const result=await api.previewBackupRestore(backup);setBackupPreview(result);setBackupNotice("Prévia validada. Nenhum dado foi alterado.");}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao validar o backup.");}
  finally{setBusy(false);}
 }
 async function restoreBackup(){
  if(!backup||!backupPreview)return;
  const confirmed=window.confirm("A restauração substituirá os dados financeiros atuais deste usuário pelos dados do backup. Faça um backup atual antes de continuar. Deseja prosseguir?");
  if(!confirmed)return;
  setBusy(true);setBackupError("");setBackupNotice("");
  try{const result=await api.restoreFullBackup(backup);setBackupNotice(`Restauração concluída: ${result.records_restored} registros em ${result.tables_restored} tabelas.`);setBackup(null);setBackupPreview(null);setBackupFilename("");}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao restaurar o backup.");}
  finally{setBusy(false);}
 }
\n const validRows=preview?.rows.filter(row=>row.status==="valid")??[];
 return <div className="content-grid exchange-page">
  <section className="panel"><h3>Importar movimentações</h3><p className="muted">Carregue um extrato, confira a prévia e só então confirme. O sistema não altera nem apaga lançamentos existentes.</p>
   {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-hint" role="status">{notice}</p>}
   <form className="form-stack" onSubmit={makePreview}>
    <label>Arquivo de extrato<input type="file" accept=".csv,.json,.ofx,.xlsx,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={chooseFile}/></label>
    {filename&&<small className="muted">Arquivo: {filename} · Formato: {format.toUpperCase()}</small>}
    <label>Conta padrão (quando o arquivo não informar a conta)<select value={accountId} onChange={e=>setAccountId(e.target.value)}><option value="">Exigir conta por linha</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</select></label>
    <label>Categoria padrão (opcional)<select value={categoryId} onChange={e=>setCategoryId(e.target.value)}><option value="">Sem categoria padrão</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name} · {c.category_type==="expense"?"Despesa":"Receita"}</option>)}</select></label>
    <button className="button primary" disabled={busy||!content.trim()}>Analisar e gerar prévia</button>
   </form>
  </section>
  <section className="panel"><h3>Exportar movimentações</h3><p className="muted">Exporte os lançamentos do usuário autenticado, mantendo valores monetários e moedas originais.</p><div className="button-row"><button className="button secondary" type="button" disabled={busy} onClick={()=>void download("csv")}>Exportar CSV</button><button className="button secondary" type="button" disabled={busy} onClick={()=>void download("json")}>Exportar JSON</button><button className="button secondary" type="button" disabled={busy} onClick={()=>void download("xlsx")}>Exportar Excel</button></div></section>
  {preview&&<section className="panel"><h3>Prévia da importação</h3><div className="metric-grid"><article className="metric-card"><span className="eyebrow">LINHAS</span><strong>{preview.total}</strong></article><article className="metric-card"><span className="eyebrow">PRONTAS</span><strong>{preview.valid}</strong></article><article className="metric-card"><span className="eyebrow">DUPLICADAS</span><strong>{preview.duplicates}</strong></article><article className="metric-card"><span className="eyebrow">INVÁLIDAS</span><strong>{preview.invalid}</strong></article></div>
   <div className="table-wrap"><table><thead><tr><th>Linha</th><th>Status</th><th>Descrição</th><th>Valor</th><th>Detalhe</th></tr></thead><tbody>{preview.rows.map(row=><tr key={row.line}><td>{row.line}</td><td>{row.status==="valid"?"Pronta":row.status==="duplicate"?"Duplicada":"Inválida"}</td><td>{row.description||"—"}</td><td>{row.amount||"—"} {row.currency}</td><td>{row.error||"—"}</td></tr>)}</tbody></table></div>
   <button className="button primary" type="button" disabled={busy||preview.invalid>0||preview.valid===0} onClick={()=>void confirmImport()}>Confirmar importação de {validRows.length} movimentações</button>
   {preview.invalid>0&&<p className="muted">Corrija todas as linhas inválidas no arquivo e gere uma nova prévia. A importação é atômica.</p>}
  </section>}

  <section className="panel backup-panel"><h3>Backup completo e restauração</h3><p className="muted">Inclui contas, categorias, movimentações, cartões, faturas, dívidas, metas, investimentos, patrimônio, compras, estoque, documentos fiscais, recorrências e conciliação. Tokens e eventos de segurança não são exportados.</p>
   {backupError&&<p className="form-error" role="alert">{backupError}</p>}{backupNotice&&<p className="form-hint" role="status">{backupNotice}</p>}
   <div className="button-row"><button className="button primary" type="button" disabled={busy} onClick={()=>void downloadBackup()}>Gerar backup completo</button></div>
   <label>Arquivo de backup SFI (.json)<input type="file" accept=".json,application/json" onChange={chooseBackup}/></label>
   {backupFilename&&<small className="muted">Arquivo: {backupFilename}</small>}
   {backup&&<button className="button secondary" type="button" disabled={busy} onClick={()=>void previewBackup()}>Validar e visualizar restauração</button>}
   {backupPreview&&<><div className="metric-grid"><article className="metric-card"><span className="eyebrow">REGISTROS NO BACKUP</span><strong>{backupPreview.records_in_backup}</strong></article><article className="metric-card"><span className="eyebrow">REGISTROS ATUAIS</span><strong>{backupPreview.records_current}</strong></article></div><p className="muted">A restauração substitui os registros financeiros atuais deste usuário. O perfil de autenticação e os dados de outros usuários não são substituídos.</p><div className="table-wrap"><table><thead><tr><th>Módulo/tabela</th><th>No backup</th><th>Atuais</th></tr></thead><tbody>{backupPreview.tables.filter(row=>row.backup_records||row.current_records).map(row=><tr key={row.name}><td>{row.name}</td><td>{row.backup_records}</td><td>{row.current_records}</td></tr>)}</tbody></table></div><button className="button danger" type="button" disabled={busy} onClick={()=>void restoreBackup()}>Substituir dados pelos do backup</button></>}
   <small className="muted">Limite de 50 MB e 250.000 registros. Restauração integral disponível no SQLite local; backups incompatíveis com o esquema atual são rejeitados. Faça um backup atual antes de restaurar.</small>
  </section>\n  <section className="panel"><h3>Regras de segurança</h3><ul className="muted"><li>Prévia não grava dados.</li><li>Confirmação é obrigatória; arquivos com linhas inválidas são rejeitados por inteiro.</li><li>Contas e categorias precisam pertencer à sua conta SFI.</li><li>Duplicatas são detectadas por chave determinística e ignoradas em reimportações.</li><li>Limite de 5 MB e 10.000 movimentações por arquivo. Planilhas XLSX usam a primeira aba e a primeira linha como cabeçalho.</li></ul></section>
 </div>;
}
