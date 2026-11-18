import {useEffect,useState} from "react";
import type {ChangeEvent,FormEvent} from "react";
import {api,isDesktopApp,type Account,type Category,type ExchangePreview,type BackupDocument,type BackupPreview,type AutomaticBackupStatus} from "./api";

type ImportFormat="csv"|"json"|"ofx"|"xlsx"|"qif"|"pdf";
export default function DataExchangePage({accounts,categories}:{accounts:Account[];categories:Category[]}){
 const [format,setFormat]=useState<ImportFormat>("csv"),[content,setContent]=useState(""),[filename,setFilename]=useState("");
 const [accountId,setAccountId]=useState(accounts[0]?.id??""),[categoryId,setCategoryId]=useState("");
 const [preview,setPreview]=useState<ExchangePreview|null>(null),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [busy,setBusy]=useState(false);
 const [automaticStatus,setAutomaticStatus]=useState<AutomaticBackupStatus|null>(null),[automaticCadence,setAutomaticCadence]=useState<"daily"|"weekly">("daily"),[automaticTime,setAutomaticTime]=useState("20:00"),[automaticError,setAutomaticError]=useState(""),[automaticNotice,setAutomaticNotice]=useState("");
 const [backup,setBackup]=useState<BackupDocument|null>(null),[backupPreview,setBackupPreview]=useState<BackupPreview|null>(null);
 const [backupFilename,setBackupFilename]=useState(""),[backupError,setBackupError]=useState(""),[backupNotice,setBackupNotice]=useState("");
 const [backupPassphrase,setBackupPassphrase]=useState(""),[encryptedEnvelope,setEncryptedEnvelope]=useState<Record<string,unknown>|null>(null);
 useEffect(()=>{if(!isDesktopApp)return;api.automaticBackupStatus().then(status=>{setAutomaticStatus(status);if(status.cadence)setAutomaticCadence(status.cadence);if(status.local_time)setAutomaticTime(status.local_time);}).catch(error=>setAutomaticError(error instanceof Error?error.message:"Não foi possível consultar o backup automático."));},[]);
 async function chooseFile(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setError("");setNotice("");setPreview(null);
  const extension=file.name.toLowerCase().split(".").pop();
  if(extension!=="csv"&&extension!=="json"&&extension!=="ofx"&&extension!=="xlsx"&&extension!=="qif"&&extension!=="pdf"){setError("Formato não suportado. Use CSV, JSON, OFX, XLSX, QIF ou PDF.");return;}
  if(file.size>5*1024*1024){setError("O arquivo excede o limite de 5 MB.");return;}
  try{
   if(extension==="xlsx"||extension==="pdf"){
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
  try{if(backupPassphrase.length<12)throw new Error("Defina uma senha de pelo menos 12 caracteres para criptografar o backup.");const envelope=await api.exportEncryptedBackup(backupPassphrase);const blob=new Blob([JSON.stringify(envelope)],{type:"application/json"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="sfi-backup-encrypted.json";document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setBackupNotice("Backup criptografado gerado. A senha não é armazenada pelo SFI.");}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao gerar backup completo.");}
  finally{setBusy(false);}
 }

 async function saveAutomaticBackup(){
  setBusy(true);setAutomaticError("");setAutomaticNotice("");
  try{if(backupPassphrase.length<12)throw new Error("Defina uma senha de pelo menos 12 caracteres no campo de senha do backup.");const result=await api.configureAutomaticBackup({cadence:automaticCadence,local_time:automaticTime,passphrase:backupPassphrase});const status=await api.automaticBackupStatus();setAutomaticStatus(status);setAutomaticNotice("Backup automático "+(result.cadence==="daily"?"diário":"semanal")+" configurado para "+result.local_time+". A senha foi protegida pelo Windows DPAPI.");}
  catch(e){setAutomaticError(e instanceof Error?e.message:"Não foi possível configurar o backup automático.");}
  finally{setBusy(false);}
 }

 async function downloadAutomaticBackup(filename:string){
  setBusy(true);setAutomaticError("");
  try{const blob=await api.downloadAutomaticBackup(filename);const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setAutomaticNotice("Backup automático baixado. Use a senha configurada para validar e restaurar o arquivo.");}
  catch(e){setAutomaticError(e instanceof Error?e.message:"Não foi possível baixar o backup.");}
  finally{setBusy(false);}
 }
 async function removeAutomaticBackup(){
  setBusy(true);setAutomaticError("");setAutomaticNotice("");
  try{await api.disableAutomaticBackup();setAutomaticStatus(await api.automaticBackupStatus());setAutomaticNotice("Agendamento automático desativado. Os backups já criados foram preservados.");}
  catch(e){setAutomaticError(e instanceof Error?e.message:"Não foi possível desativar o backup automático.");}
  finally{setBusy(false);}
 }
 async function chooseBackup(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setBackup(null);setEncryptedEnvelope(null);setBackupPreview(null);setBackupError("");setBackupNotice("");
  if(file.size>70*1024*1024){setBackupError("O backup excede o limite de 70 MB.");return;}
  try{
   const parsed=JSON.parse(await file.text()) as Record<string,unknown>;
   if(parsed.format==="sfi-encrypted-backup"){setEncryptedEnvelope(parsed);setBackup(null);setBackupFilename(file.name);setBackupNotice("Backup criptografado carregado. Informe a senha e valide a prévia.");}
   else{const legacy=parsed as unknown as BackupDocument;if(legacy.format!=="sfi-personal-data"||legacy.version!==1||!legacy.tables)throw new Error("Arquivo não é um backup SFI compatível.");setBackup(legacy);setBackupFilename(file.name);setBackupNotice("Backup JSON legado sem criptografia carregado. Valide a prévia antes de restaurar.");}
  }catch(e){setBackupError(e instanceof Error?e.message:"Não foi possível ler o backup.");}
 }
 async function previewBackup(){
  if(!backup&&!encryptedEnvelope)return;if(encryptedEnvelope&&backupPassphrase.length<12){setBackupError("Informe a senha usada para criptografar o backup.");return;}setBusy(true);setBackupError("");setBackupNotice("");
  try{const result=encryptedEnvelope?await api.previewEncryptedBackup(encryptedEnvelope,backupPassphrase):await api.previewBackupRestore(backup!);setBackupPreview(result);setBackupNotice("Prévia validada. Nenhum dado foi alterado.");}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao validar o backup.");}
  finally{setBusy(false);}
 }
 async function restoreBackup(){
  if((!backup&&!encryptedEnvelope)||!backupPreview)return;
  const confirmed=window.confirm("A restauração substituirá os dados financeiros atuais deste usuário pelos dados do backup. Faça um backup atual antes de continuar. Deseja prosseguir?");
  if(!confirmed)return;
  setBusy(true);setBackupError("");setBackupNotice("");
  try{const result=encryptedEnvelope?await api.restoreEncryptedBackup(encryptedEnvelope,backupPassphrase):await api.restoreFullBackup(backup!);setBackupNotice(`Restauração concluída: ${result.records_restored} registros em ${result.tables_restored} tabelas.`);window.location.reload();}
  catch(e){setBackupError(e instanceof Error?e.message:"Falha ao restaurar o backup.");}
  finally{setBusy(false);}
 }

 const validRows=preview?.rows.filter(row=>row.status==="valid")??[];
 return <div className="content-grid exchange-page">
  <section className="panel"><h3>Importar movimentações</h3><p className="muted">Carregue CSV, JSON, OFX, Excel, QIF ou PDF, confira a prévia e só então confirme. PDFs digitalizados e layouts não reconhecidos não são importados automaticamente.</p>
   {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-hint" role="status">{notice}</p>}
   <form className="form-stack" onSubmit={makePreview}>
    <label>Arquivo de extrato<input type="file" accept=".csv,.json,.ofx,.xlsx,.qif,.pdf,text/csv,application/json,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={chooseFile}/></label>
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
   <label>Senha do backup (mínimo 12 caracteres)<input type="password" minLength={12} maxLength={1024} autoComplete="new-password" value={backupPassphrase} onChange={e=>setBackupPassphrase(e.target.value)} placeholder="Crie uma senha forte para o arquivo"/></label><div className="button-row"><button className="button primary" type="button" disabled={busy||backupPassphrase.length<12} onClick={()=>void downloadBackup()}>Gerar backup criptografado</button></div>
   <label>Arquivo de backup SFI (.json)<input type="file" accept=".json,application/json" onChange={chooseBackup}/></label>
   {backupFilename&&<small className="muted">Arquivo: {backupFilename}</small>}
   {(backup||encryptedEnvelope)&&<button className="button secondary" type="button" disabled={busy||(!!encryptedEnvelope&&backupPassphrase.length<12)} onClick={()=>void previewBackup()}>Validar e visualizar restauração</button>}
   {backupPreview&&<><div className="metric-grid"><article className="metric-card"><span className="eyebrow">REGISTROS NO BACKUP</span><strong>{backupPreview.records_in_backup}</strong></article><article className="metric-card"><span className="eyebrow">REGISTROS ATUAIS</span><strong>{backupPreview.records_current}</strong></article></div><p className="muted">A restauração substitui os registros financeiros atuais deste usuário. O perfil de autenticação e os dados de outros usuários não são substituídos.</p><div className="table-wrap"><table><thead><tr><th>Módulo/tabela</th><th>No backup</th><th>Atuais</th></tr></thead><tbody>{backupPreview.tables.filter(row=>row.backup_records||row.current_records).map(row=><tr key={row.name}><td>{row.name}</td><td>{row.backup_records}</td><td>{row.current_records}</td></tr>)}</tbody></table></div><button className="button danger" type="button" disabled={busy} onClick={()=>void restoreBackup()}>Substituir dados pelos do backup</button></>}
   <small className="muted">Novos arquivos são criptografados com AES-256-GCM e scrypt. A senha não é armazenada e não pode ser recuperada. Backups JSON antigos sem criptografia continuam aceitos para compatibilidade. Limite de 50 MB e 250.000 registros. Restauração disponível somente no SQLite local; faça um backup atual antes de restaurar.</small>
  </section>

  {isDesktopApp&&<section className="panel"><h3>Backup automático do Windows</h3><p className="muted">O SFI gera backups criptografados em segundo plano enquanto o aplicativo estiver aberto. A senha fica protegida pelo Windows DPAPI e não é gravada em texto puro. São mantidas até 10 versões; ao exceder o limite, as mais antigas são removidas.</p>
   {automaticError&&<p className="form-error" role="alert">{automaticError}</p>}{automaticNotice&&<p className="form-hint" role="status">{automaticNotice}</p>}
   <label>Frequência<select value={automaticCadence} onChange={e=>setAutomaticCadence(e.target.value as "daily"|"weekly")}><option value="daily">Todos os dias</option><option value="weekly">A cada 7 dias</option></select></label>
   <label>Horário local<input type="time" value={automaticTime} onChange={e=>setAutomaticTime(e.target.value)}/></label>
   <div className="button-row"><button className="button primary" type="button" disabled={busy||backupPassphrase.length<12} onClick={()=>void saveAutomaticBackup()}>{automaticStatus?.enabled?"Atualizar agendamento":"Ativar backup automático"}</button>{automaticStatus?.enabled&&<button className="button secondary" type="button" disabled={busy} onClick={()=>void removeAutomaticBackup()}>Desativar</button>}</div>
   {automaticStatus&&<><p className="muted">Status: {automaticStatus.enabled?"Ativo":"Desativado"} · Retenção: {automaticStatus.retention} versões · Último backup: {automaticStatus.last_run?new Date(automaticStatus.last_run).toLocaleString():"Ainda não executado"}</p>{automaticStatus.last_error&&<p className="form-error">Última tentativa falhou ({automaticStatus.last_error}). O SFI tentará novamente no próximo ciclo.</p>}<div className="table-wrap"><table><thead><tr><th>Arquivo</th><th>Data</th><th>Tamanho</th><th>Ação</th></tr></thead><tbody>{automaticStatus.history.map(item=><tr key={item.filename}><td>{item.filename}</td><td>{new Date(item.created_at).toLocaleString()}</td><td>{(item.size_bytes/1024/1024).toFixed(2)} MB</td><td><button className="button secondary" type="button" disabled={busy} onClick={()=>void downloadAutomaticBackup(item.filename)}>Baixar</button></td></tr>)}</tbody></table></div></>}
  </section>}
  <section className="panel"><h3>Regras de segurança</h3><ul className="muted"><li>Prévia não grava dados.</li><li>Confirmação é obrigatória; arquivos com linhas inválidas são rejeitados por inteiro.</li><li>Contas e categorias precisam pertencer à sua conta SFI.</li><li>Duplicatas são detectadas por chave determinística e ignoradas em reimportações.</li><li>Limite de 5 MB e 10.000 movimentações por arquivo. Planilhas XLSX usam a primeira aba e a primeira linha como cabeçalho. PDFs precisam conter texto selecionável e linhas com data, descrição e valor assinado ou indicador D/C; OCR e layouts bancários específicos ainda não estão disponíveis. QIF usa o sinal do valor para classificar receita/despesa.</li></ul></section>
 </div>;
}
