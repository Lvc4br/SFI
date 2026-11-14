import { useEffect, useState } from "react";
type ApiHealth = { status: string; app: string; environment: string };
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export default function App() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(API_URL + "/api/v1/health/live", { signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error("API respondeu HTTP " + response.status); return await response.json() as ApiHealth; })
      .then(setHealth).catch((error: unknown) => { if (error instanceof Error && error.name !== "AbortError") setApiError(error.message); });
    return () => controller.abort();
  }, []);
  return <main className="shell">
    <header className="topbar"><a className="brand" href="/"><span className="brand-mark">S</span><span>SFI</span></a><span className="topbar-label">SISTEMA FINANCEIRO INTELIGENTE</span></header>
    <section className="hero"><div className="eyebrow"><span/> FUNDAÇÃO DO PROJETO</div><h1>Sua vida financeira,<br/><em>com clareza e direção.</em></h1>
      <p className="intro">Um espaço para aprender, organizar e tomar decisões melhores sobre o seu dinheiro. O SFI está em construção — esta é a primeira base funcional do produto.</p>
      <div className="status-card"><div><span className="status-label">API BACKEND</span><strong>{health ? "Conectada" : apiError ? "Não disponível" : "Verificando..."}</strong><small>{health ? health.app + " · " + health.environment : apiError ?? "Consultando serviço local"}</small></div><span className={health ? "status-dot online" : "status-dot"}/></div>
    </section>
    <section className="pillars"><article><span>01</span><h2>Aprender</h2><p>Educação financeira acessível, do básico ao avançado.</p></article><article><span>02</span><h2>Organizar</h2><p>Contas, movimentações, orçamento e objetivos em um só lugar.</p></article><article><span>03</span><h2>Decidir</h2><p>Dados, planejamento e inteligência para escolhas conscientes.</p></article></section>
    <footer><span>SFI · Fundação v0.1.0</span><span>Seus dados permanecem sob seu controle.</span></footer>
  </main>;
}
