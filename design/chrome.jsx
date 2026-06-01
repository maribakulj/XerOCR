/* Shared chrome — top bar with brand + tabs + meta, used by every view.
   Tabs sont câblées via React Context (ReportContext). */

const ReportContext = React.createContext(null);

function ReportChrome({ active }) {
  const ctx = React.useContext(ReportContext);
  // Si on est dans un ReportApp (avec Provider), on prend le tab actif du
  // contexte ; sinon on retombe sur le prop `active` (vue isolée).
  const tab = ctx ? ctx.tab : active;
  const setTab = ctx ? ctx.setTab : () => {};
  const TABS = [
    { id: 'overview',  label: 'Vue d\u2019ensemble' },
    { id: 'engines',   label: 'Par moteur' },
    { id: 'documents', label: 'Par document' },
    { id: 'crosses',   label: 'Croisements' },
  ];
  return (
    <div className="report-chrome">
      <div className="wm">
        <span className="wm-mark">X</span>
        <span className="wm-name">XerOCR</span>
        <span className="wm-sep"></span>
        <span className="wm-sub">Rapport · benchmark</span>
      </div>
      <div className="report-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={t.id === tab ? 'on' : ''}
            onClick={() => setTab(t.id)}
          >{t.label}</button>
        ))}
      </div>
      <div className="chrome-meta">
        <span><span className="v">42</span> docs</span>
        <span><span className="v">5</span> moteurs</span>
        <span className="v">2026-05-21</span>
        <div className="chrome-actions">
          <button className="chrome-btn">⬇ CSV</button>
          <button className="chrome-btn">⬇ JSON</button>
        </div>
      </div>
    </div>
  );
}

function HeroBand({ eyebrow, title, desc, stats }) {
  return (
    <div className="view-hero">
      <div>
        <div className="view-hero-eyebrow">{eyebrow}</div>
        <div className="view-hero-name">{title}</div>
        {desc && <div className="view-hero-desc">{desc}</div>}
      </div>
      {stats && (
        <div className="view-hero-stats">
          {stats.map((s, i) => (
            <div key={i} className="hero-stat">
              <div className="v">{s.v}<span style={{fontSize:'14px',color:'var(--g-300)',marginLeft:'2px'}}>{s.u}</span></div>
              <div className="k">{s.k}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* CER tier helper — kept for backward compat (no longer used for color). */
function cerTier(v) {
  if (v < 0.05) return 't1';
  if (v < 0.15) return 't2';
  if (v < 0.30) return 't3';
  return 't4';
}
function pct(v, dec = 1) {
  return (v * 100).toFixed(dec) + ' %';
}

/* ---------------------------------------------------------------- */
/* ReportApp — stateful shell that wires chrome tabs to view swap   */
/* ---------------------------------------------------------------- */

function ReportApp({ initialTab, initialSelected, initialSelectedEngine }) {
  const [tab, setTab] = React.useState(initialTab || 'overview');

  return (
    <ReportContext.Provider value={{ tab, setTab }}>
      {tab === 'overview'  && <ViewOverview />}
      {tab === 'engines'   && <ViewByEngine   initialSelected={initialSelectedEngine} />}
      {tab === 'documents' && <ViewByDocument initialSelected={initialSelected} />}
      {tab === 'crosses'   && <ViewCrosses />}
    </ReportContext.Provider>
  );
}

Object.assign(window, { ReportChrome, HeroBand, cerTier, pct, ReportContext, ReportApp });
