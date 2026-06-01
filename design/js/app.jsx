/* Main app — XerOCR launcher, 3 main views + System modal.
   (Design-tweak overlay removed: it was Claude-Design editing tooling, not the
   product. Density/accent are fixed to the shipped defaults.) */
const { useState, useEffect } = React;
const { Icon } = window.PicaUI;

const VIEWS = [
  { id: "library",   icon: "library", labelKey: "nav_library",   meta: (s) => "4 corpora" },
  { id: "benchmark", icon: "bench",   labelKey: "nav_benchmark", meta: (s) => s.benchPhase === "running" ? null : `${s.competitors.length} queued` },
  { id: "reports",   icon: "reports", labelKey: "nav_reports",   meta: (s) => "4 reports" },
];

// Extend i18n strings for the new nav labels
if (window.I18N) {
  window.I18N.fr.nav_library = "Bibliothèque";
  window.I18N.en.nav_library = "Library";
}

function App() {
  const [view, setView] = useState("benchmark");
  const [systemOpen, setSystemOpen] = useState(false);
  const [lang, setLang] = useState("fr");
  const t = window.useT(lang);

  useEffect(() => {
    document.documentElement.dataset.density = "balanced";
    document.documentElement.dataset.accent = "fern";
  }, []);

  const [benchState, setBenchState] = useState({
    corpusPath: "corpus_psaumes_240/",
    competitors: [
      { id: "C01", kind: "OCR", name: "Tesseract 5 (fra+lat)", chain: ["Tesseract 5"], color: "ink" },
      { id: "C02", kind: "OCR→LLM", name: "Pero → claude-sonnet-4.5", chain: ["Pero OCR", "claude-sonnet-4.5"], color: "slate" },
      { id: "C03", kind: "OCR", name: "Mistral OCR", chain: ["Mistral OCR"], color: "fern" },
    ],
    composeMode: "ocr",
    composeOCR: "tesseract",
    composeOCRLang: "fra+lat",
    composeLLMProv: "anthropic",
    composeLLM: "claude-sonnet-4.5",
    composeMode2: "text_only",
    composePrompt: "medieval_latin_v3",
    benchPhase: "idle",
    benchProgress: 0,
  });

  useEffect(() => {
    if (benchState.benchPhase !== "running") return;
    const id = setInterval(() => {
      setBenchState((s) => {
        if (s.benchProgress >= 240) return { ...s, benchPhase: "done", benchProgress: 240 };
        return { ...s, benchProgress: Math.min(240, s.benchProgress + 4) };
      });
    }, 220);
    return () => clearInterval(id);
  }, [benchState.benchPhase]);

  return (
    <div className="app">
      <aside className="rail">
        <div className="wordmark-card">
          <div className="wordmark">
            <span className="mark">X</span>
            <span>XerOCR</span>
          </div>
          <div className="wordmark-sub">OCR · HTR · VLM benchmark</div>
        </div>

        <nav className="rail-nav rail-nav-window">
          {VIEWS.map((v) => (
            <div
              key={v.id}
              className={"nav-item" + (view === v.id ? " active" : "")}
              onClick={() => setView(v.id)}
            >
              <span className="nav-glyph"><Icon name={v.icon} size={16} /></span>
              <span className="nav-label">{t(v.labelKey)}</span>
              {v.id === "benchmark" && benchState.benchPhase === "running"
                ? <span className="pulse" title="running" />
                : <span className="nav-meta">{v.meta(benchState)}</span>}
            </div>
          ))}
        </nav>

        <div className="rail-system">
          <div className="sys-card">
            <div className="sys-card-title">
              <span>{t("sys_status")}</span>
              <span className="dot on" />
            </div>
            <div className="sys-row"><span className="k">{t("sys_version")}</span><span className="v">2.0.0-rc4</span></div>
            <div className="sys-row"><span className="k">{t("sys_mode")}</span><span className="v">institutional</span></div>
            <div className="sys-row"><span className="k">{t("sys_active_job")}</span>
              <span className={"v " + (benchState.benchPhase === "running" ? "on" : "off")}>
                {benchState.benchPhase === "running" ? t("sys_running") : t("sys_idle")}
              </span>
            </div>
          </div>

          <div className="sys-card">
            <div className="sys-card-title">
              <span>Pipeline</span>
              <span className="foot">5/7 · 3/4</span>
            </div>
            <div className="sys-row"><span className="k">{t("sys_engines_online")}</span><span className="v">5 / 7</span></div>
            <div className="sys-row"><span className="k">LLM providers</span><span className="v">3 / 4</span></div>
          </div>

          <button className="system-trigger" onClick={() => setSystemOpen(true)}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <Icon name="system" size={14} />
              <span>{lang === "fr" ? "Système · détails" : "System · details"}</span>
            </span>
            <Icon name="arrow-right" size={12} />
          </button>
        </div>

        <div className="rail-foot">
          <span className="foot-meta">{t("sys_lang")}</span>
          <span className="lang-toggle">
            <button className={lang === "fr" ? "on" : ""} onClick={() => setLang("fr")}>FR</button>
            <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>EN</button>
          </span>
        </div>
      </aside>

      <main className="main">
        {view === "library" && <window.LibraryView t={t} lang={lang} />}
        {view === "benchmark" && <window.BenchmarkView t={t} lang={lang} state={benchState} setState={setBenchState} />}
        {view === "reports" && <window.ReportsView t={t} lang={lang} />}
      </main>

      <window.SystemPanel open={systemOpen} onClose={() => setSystemOpen(false)} t={t} lang={lang} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
