import { useEffect, useState } from "react";

type ApiHealth = { status: string; app: string; environment: string };
type Theme = "light" | "dark";
type Section = "inicio" | "movimentacoes" | "planejar" | "perfil";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const navigation: { id: Section; label: string; icon: string }[] = [
  { id: "inicio", label: "Início", icon: "⌂" },
  { id: "movimentacoes", label: "Movimentações", icon: "↕" },
  { id: "planejar", label: "Planejar", icon: "▤" },
  { id: "perfil", label: "Perfil", icon: "◎" },
];

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem("sfi-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [section, setSection] = useState<Section>("inicio");
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("sfi-theme", theme); } catch { /* armazenamento opcional */ }
  }, [theme]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(API_URL + "/api/v1/health/live", { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("API respondeu HTTP " + response.status);
        return await response.json() as ApiHealth;
      })
      .then(setHealth)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") setApiError(error.message);
      });
    return () => controller.abort();
  }, []);

  const sectionTitle = navigation.find(item => item.id === section)?.label ?? "Início";

  return (
    <div className="app-frame">
      <aside className="sidebar" aria-label="Navegação principal">
        <a className="brand" href="/" aria-label="SFI, página inicial">
          <span className="brand-mark">s</span><span>SFI</span>
        </a>
        <span className="nav-caption">MENU</span>
        <nav className="nav-list">
          {navigation.map(item => (
            <button key={item.id} className={section === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setSection(item.id)} aria-current={section === item.id ? "page" : undefined}>
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection"><span className={health ? "connection-dot online" : "connection-dot"} />
            <span>{health ? "Serviço conectado" : apiError ? "Serviço indisponível" : "Conectando ao serviço"}</span>
          </div>
          <button className="theme-button" onClick={() => setTheme(value => value === "light" ? "dark" : "light")}>
            <span aria-hidden="true">{theme === "light" ? "◐" : "☼"}</span>
            Tema {theme === "light" ? "escuro" : "claro"}
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">s</span><strong>SFI</strong></div>
          <div className="breadcrumb">Seu espaço financeiro <span>/</span> <strong>{sectionTitle}</strong></div>
          <button className="icon-button desktop-theme" aria-label={theme === "light" ? "Ativar tema escuro" : "Ativar tema claro"}
            onClick={() => setTheme(value => value === "light" ? "dark" : "light")}>
            {theme === "light" ? "◐" : "☼"}
          </button>
        </header>

        <div className="page-content">
          <section className="welcome">
            <div><span className="eyebrow">VISÃO GERAL</span><h1>{section === "inicio" ? "Bom ter você por aqui." : sectionTitle}</h1>
              <p>{section === "inicio" ? "Organize seu dinheiro com mais clareza, um passo de cada vez." : "Esta área está sendo preparada para reunir suas informações com clareza."}</p>
            </div>
            <span className="date-chip">SFI · EM CONSTRUÇÃO</span>
          </section>

          {section === "inicio" ? (
            <>
              <section className="balance-panel" aria-labelledby="balance-title">
                <div className="balance-copy"><span id="balance-title" className="panel-label">SEU DINHEIRO, EM UM SÓ LUGAR</span>
                  <h2>Uma visão clara começa aqui.</h2>
                  <p>Quando suas contas estiverem conectadas, você verá seu saldo e poderá acompanhar o que entra e sai.</p>
                </div>
                <div className="balance-art" aria-hidden="true"><span>R$</span><i>＋</i><b>−</b></div>
              </section>
              <div className="section-heading"><div><span className="eyebrow">COMECE POR AQUI</span><h2>O que você pode organizar</h2></div></div>
              <section className="feature-grid">
                <article className="feature-card"><span className="feature-icon green">↕</span><h3>Movimentações</h3><p>Registre entradas e gastos para entender para onde seu dinheiro vai.</p><button onClick={() => setSection("movimentacoes")}>Ver movimentações <span>→</span></button></article>
                <article className="feature-card"><span className="feature-icon sand">▤</span><h3>Planejamento</h3><p>Prepare seu mês com limites, recorrências e previsões.</p><button onClick={() => setSection("planejar")}>Ir para Planejar <span>→</span></button></article>
                <article className="feature-card"><span className="feature-icon blue">◎</span><h3>Suas preferências</h3><p>Cuide das suas contas, categorias e configurações de acesso.</p><button onClick={() => setSection("perfil")}>Abrir perfil <span>→</span></button></article>
              </section>
            </>
          ) : (
            <section className="empty-panel"><span className="empty-symbol" aria-hidden="true">{navigation.find(item => item.id === section)?.icon}</span>
              <h2>Estamos preparando esta área.</h2><p>As próximas etapas vão conectar esta tela aos recursos reais da API. Nenhum dado financeiro fictício será exibido.</p>
              <button className="primary-button" onClick={() => setSection("inicio")}>Voltar ao início</button>
            </section>
          )}

          <footer className="page-footer"><span>SFI · Sistema Financeiro Inteligente</span><span>{health ? health.app + " · " + health.environment : apiError ? "API não conectada" : "Verificando API…"}</span></footer>
        </div>
      </main>

      <nav className="mobile-nav" aria-label="Navegação principal">
        {navigation.map(item => <button key={item.id} className={section === item.id ? "mobile-nav-item active" : "mobile-nav-item"}
          onClick={() => setSection(item.id)} aria-current={section === item.id ? "page" : undefined}>
          <span aria-hidden="true">{item.icon}</span><small>{item.label}</small>
        </button>)}
      </nav>
    </div>
  );
}
