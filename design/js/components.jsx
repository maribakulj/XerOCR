/* Shared components — v2 soft rounded */
const { useState, useEffect, useRef, useMemo } = React;

/* === Tiny SVG icons — Xerox-Star pictographic flavor === */
function Icon({ name, size = 16 }) {
  const s = size;
  const c = "currentColor";
  const props = { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: 1.4, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "library":
      // Stack of folders with tab
      return (
        <svg {...props}>
          <path d="M3 8h6l1.5 2H21v10H3z" />
          <path d="M3 8V6h5.5L10 8" />
          <path d="M7 14h10M7 17h7" />
        </svg>
      );
    case "bench":
      // Dial gauge — like a meter
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="1.4" fill={c} stroke="none" />
          <path d="M12 12l4-4" />
          <path d="M5 12h2M17 12h2M12 5v2" />
        </svg>
      );
    case "reports":
      // Document with lines + corner fold
      return (
        <svg {...props}>
          <path d="M6 3h9l4 4v14H6z" />
          <path d="M15 3v4h4" />
          <path d="M9 12h7M9 15h7M9 18h5" />
        </svg>
      );
    case "system":
      // Concentric mark
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="5" />
          <circle cx="12" cy="12" r="1.5" fill={c} stroke="none" />
        </svg>
      );
    case "play":
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" fill={c}>
          <path d="M7 5v14l12-7z" />
        </svg>
      );
    case "plus":
      return (
        <svg {...props}><path d="M12 5v14M5 12h14" strokeWidth="1.8" /></svg>
      );
    case "x":
      return (
        <svg {...props}><path d="M6 6l12 12M18 6L6 18" strokeWidth="1.8" /></svg>
      );
    case "arrow-right":
      return (
        <svg {...props}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      );
    case "download":
      return (
        <svg {...props}><path d="M12 4v12M6 11l6 6 6-6M4 20h16" /></svg>
      );
    case "upload":
      return (
        <svg {...props}><path d="M12 20V8M6 13l6-6 6 6M4 4h16" /></svg>
      );
    case "refresh":
      return (
        <svg {...props}><path d="M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5" /></svg>
      );
    case "search":
      return (
        <svg {...props}><circle cx="11" cy="11" r="6" /><path d="M20 20l-4.3-4.3" /></svg>
      );
    case "folder":
      return (
        <svg {...props}>
          <path d="M3 8h6l1.5 2H21v10H3z" />
          <path d="M3 8V6h5.5L10 8" />
        </svg>
      );
    case "doc":
      return (
        <svg {...props}>
          <path d="M6 3h9l4 4v14H6z" />
          <path d="M15 3v4h4" />
        </svg>
      );
    case "img":
      return (
        <svg {...props}>
          <rect x="4" y="5" width="16" height="14" rx="1" />
          <circle cx="9" cy="10" r="1.4" />
          <path d="M4 17l5-5 5 4 4-3 2 2" />
        </svg>
      );
    case "people":
      // Like the Xerox "Design" folder icon
      return (
        <svg {...props}>
          <circle cx="8" cy="9" r="2.2" />
          <circle cx="16" cy="9" r="2.2" />
          <path d="M3 19c0-3 2.5-5 5-5s5 2 5 5M11 19c0-3 2.5-5 5-5s5 2 5 5" />
        </svg>
      );
    default:
      return null;
  }
}

/* === Numbered section block === */
function Sec({ num, title, sub, aside, children, tone }) {
  return (
    <section className="sec" data-tone={tone || undefined}>
      <header className="sec-head">
        {num && <div className="sec-num">{num}</div>}
        <div style={{ flex: 1 }}>
          <div className="sec-title">{title}</div>
          {sub && <div className="sec-sub">{sub}</div>}
        </div>
        {aside && <div className="sec-aside">{aside}</div>}
      </header>
      <div className="sec-body">{children}</div>
    </section>
  );
}

/* === Field === */
function Field({ label, hint, children, opt }) {
  return (
    <label className="field">
      <span className="field-label">
        <span>{label}</span>
        {opt && <span className="opt">{opt}</span>}
      </span>
      {children}
      {hint && <span className="foot" style={{ marginTop: 2 }}>{hint}</span>}
    </label>
  );
}

/* === Status dot === */
function Dot({ state = "off" }) {
  return <span className={`dot ${state}`} />;
}

/* === Tabs (segmented, pill) === */
function Tabs({ value, onChange, options }) {
  return (
    <div className="tabs">
      {options.map((opt) => (
        <button key={opt.value} className={value === opt.value ? "on" : ""} onClick={() => onChange(opt.value)}>
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* === Tag === */
function Tag({ children, variant, mono }) {
  const cls = ["tag", variant ? "tag-" + variant : "", mono ? "tag-mono" : ""].filter(Boolean).join(" ");
  return <span className={cls}>{children}</span>;
}

/* === Readout === */
function Readout({ label, value, unit, delta, variant }) {
  return (
    <div className={`readout ${variant || ""}`}>
      <div className="r-label">{label}</div>
      <div>
        <span className="r-value">{value}</span>
        {unit && <span className="r-unit">{unit}</span>}
      </div>
      {delta && <div className={`r-delta ${delta.dir}`}>{delta.text}</div>}
    </div>
  );
}

/* === Bar === */
function Bar({ label, value, max = 100, unit = "", color = "ink" }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="bar-row">
      <div className="b-label">{label}</div>
      <div className="b-track"><div className={`b-fill ${color}`} style={{ width: pct + "%" }} /></div>
      <div className="b-value">{typeof value === "number" ? value.toFixed(2) : value}{unit && " " + unit}</div>
    </div>
  );
}

/* === Help (serif italic) === */
function Help({ children }) {
  return <div className="help">{children}</div>;
}

/* === Surface (rounded card) === */
function Surface({ children, variant, style }) {
  const cls = ["surface", variant === "flat" && "surface-flat", variant === "tinted" && "surface-tinted"].filter(Boolean).join(" ");
  return <div className={cls} style={style}>{children}</div>;
}

/* === View hero (plain) === */
function ViewHero({ eyebrow, name, desc, stats }) {
  return (
    <div className="view-hero">
      <div className="view-hero-title">
        <span className="view-hero-eyebrow">{eyebrow}</span>
        <div className="view-hero-name">{name}</div>
        {desc && <div className="view-hero-desc">{desc}</div>}
      </div>
      {stats && (
        <div className="view-hero-stats">
          {stats.map((s, i) => (
            <div key={i} className="hero-stat">
              <div className="v">{s.v}</div>
              <div className="k">{s.k}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* === Numbered section with titlebar text (overrides default "○ ○ ○") === */
/* Already styled in CSS — Sec just renders the chrome via ::before/::after */

/* === Window frame — pass-through, no extra surface === */
function WindowFrame({ children }) {
  return <div className="stack">{children}</div>;
}

/* === Pipeline fig.1 — clarified schematic === */
function PipelineFig() {
  return (
    <div className="fig fig-large">
      <div className="fig-caption">
        <span className="num">fig.1</span> — XerOCR evaluation pipeline · how a competitor is benchmarked
      </div>
      <div className="fig-meta">SCHEMA · v2.0</div>
      <svg viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="hatch-clay" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="5" stroke="oklch(0.58 0.10 45)" strokeWidth="1" opacity="0.5" />
          </pattern>
          <pattern id="dots" patternUnits="userSpaceOnUse" width="4" height="4">
            <circle cx="1" cy="1" r="0.7" fill="#1a1917" opacity="0.2" />
          </pattern>
          <marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L10 5L0 10z" fill="#1a1917" />
          </marker>
          <marker id="ar2-fern" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L10 5L0 10z" fill="oklch(0.50 0.07 145)" />
          </marker>
          <marker id="ar2-clay" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L10 5L0 10z" fill="oklch(0.58 0.10 45)" />
          </marker>
        </defs>

        {/* Lane labels — vertical strip on left */}
        <g>
          <text x="14" y="124" className="lane">INPUT</text>
          <text x="14" y="186" className="lane">PROCESS</text>
          <text x="14" y="260" className="lane">OUTPUT</text>
          <line x1="60" y1="80" x2="60" y2="290" className="stroke-soft" strokeDasharray="2 4" />
        </g>

        {/* === Step 1 — Image === */}
        <g transform="translate(86, 88)">
          <text x="0" y="-8" className="step-num">[1]</text>
          <rect width="118" height="80" rx="8" className="stroke-clay" />
          <rect width="118" height="80" rx="8" fill="url(#hatch-clay)" opacity="0.4" />
          <text x="59" y="20" textAnchor="middle" className="box-title">IMAGE</text>
          <line x1="14" y1="28" x2="104" y2="28" className="stroke-soft" />
          {/* Mini page icon */}
          <rect x="36" y="38" width="34" height="28" className="stroke" fill="#fff" />
          <line x1="42" y1="46" x2="64" y2="46" className="stroke" strokeWidth="0.6" />
          <line x1="42" y1="50" x2="60" y2="50" className="stroke" strokeWidth="0.6" />
          <line x1="42" y1="54" x2="63" y2="54" className="stroke" strokeWidth="0.6" />
          <line x1="42" y1="58" x2="58" y2="58" className="stroke" strokeWidth="0.6" />
          <text x="59" y="78" textAnchor="middle" className="caption">psaumes_001.jpg</text>
        </g>

        {/* === Step 2 — Ground truth === */}
        <g transform="translate(86, 224)">
          <text x="0" y="-8" className="step-num">[2]</text>
          <rect width="118" height="56" rx="8" className="stroke-clay" />
          <text x="59" y="18" textAnchor="middle" className="box-title">GROUND TRUTH</text>
          <line x1="14" y1="24" x2="104" y2="24" className="stroke-soft" />
          <text x="59" y="40" textAnchor="middle" className="fig-label">Beatus uir qui …</text>
          <text x="59" y="51" textAnchor="middle" className="caption">.gt.txt · alto · page</text>
        </g>

        {/* Down brace from [1] to engines */}
        <line x1="204" y1="128" x2="244" y2="128" className="stroke" markerEnd="url(#ar2)" />

        {/* === Step 3 — OCR / HTR engines === */}
        <g transform="translate(248, 88)">
          <text x="0" y="-8" className="step-num">[3]</text>
          <rect width="170" height="80" rx="8" className="stroke" />
          <text x="85" y="20" textAnchor="middle" className="box-title">OCR · HTR · VLM</text>
          <line x1="14" y1="28" x2="156" y2="28" className="stroke-soft" />
          {/* Engine pills */}
          <rect x="14" y="38" width="44" height="14" rx="7" className="stroke" />
          <text x="36" y="48" textAnchor="middle" className="pill-text">pero</text>
          <rect x="62" y="38" width="56" height="14" rx="7" className="stroke" />
          <text x="90" y="48" textAnchor="middle" className="pill-text">tesseract</text>
          <rect x="14" y="58" width="60" height="14" rx="7" className="stroke" />
          <text x="44" y="68" textAnchor="middle" className="pill-text">mistral_ocr</text>
          <rect x="78" y="58" width="40" height="14" rx="7" className="stroke" />
          <text x="98" y="68" textAnchor="middle" className="pill-text">+ N</text>
        </g>

        {/* OCR text intermediate */}
        <g transform="translate(248, 188)">
          <rect width="170" height="38" rx="6" className="stroke-soft" fill="url(#dots)" />
          <text x="85" y="16" textAnchor="middle" className="caption">→ raw transcription</text>
          <text x="85" y="30" textAnchor="middle" className="fig-label">Beatus uir qi non abit…</text>
        </g>

        {/* === Step 4 — LLM (optional branch, above) === */}
        <g transform="translate(454, 50)">
          <text x="0" y="-8" className="step-num step-opt">[4 — optional]</text>
          <rect width="170" height="80" rx="8" className="stroke-fern" strokeDasharray="4 3" />
          <text x="85" y="20" textAnchor="middle" className="box-title fern">LLM · VLM</text>
          <line x1="14" y1="28" x2="156" y2="28" className="stroke-soft" />
          <text x="85" y="44" textAnchor="middle" className="fig-label">post-correction</text>
          <text x="14" y="60" className="caption">prompt</text>
          <text x="156" y="60" textAnchor="end" className="caption">medieval_latin_v3</text>
          <text x="14" y="72" className="caption">model</text>
          <text x="156" y="72" textAnchor="end" className="caption">claude-sonnet-4.5</text>
        </g>

        {/* OCR → LLM (up) */}
        <path d="M418 128 Q 440 128 454 100 L 454 90" className="stroke-fern" markerEnd="url(#ar2-fern)" />
        <text x="438" y="86" className="caption fern">post-correct</text>

        {/* LLM → Compare (down to step 5) */}
        <path d="M624 90 Q 660 90 660 140 L 660 148" className="stroke-fern" markerEnd="url(#ar2-fern)" />

        {/* Direct OCR → Compare */}
        <line x1="418" y1="128" x2="664" y2="128" className="stroke" strokeDasharray="0" />
        <line x1="664" y1="128" x2="664" y2="148" className="stroke" />

        {/* === Step 5 — Compare === */}
        <g transform="translate(572, 152)">
          <text x="0" y="-8" className="step-num">[5]</text>
          <rect width="184" height="80" rx="8" className="stroke" />
          <text x="92" y="20" textAnchor="middle" className="box-title">COMPARE · METRICS</text>
          <line x1="14" y1="28" x2="170" y2="28" className="stroke-soft" />
          <text x="14" y="44" className="caption">CER</text>
          <text x="170" y="44" textAnchor="end" className="fig-num">4.82</text>
          <text x="14" y="58" className="caption">WER</text>
          <text x="170" y="58" textAnchor="end" className="fig-num">11.4</text>
          <text x="14" y="72" className="caption">κ · α · MUFI · NER</text>
          <text x="170" y="72" textAnchor="end" className="caption">+ stat. tests</text>
        </g>

        {/* GT feeds into Compare (curved up from below) */}
        <path d="M204 252 Q 380 252 580 200" className="stroke-clay" markerEnd="url(#ar2-clay)" />
        <text x="350" y="246" className="caption clay">paired against</text>

        {/* Compare → Report */}
        <line x1="756" y1="192" x2="794" y2="192" className="stroke" markerEnd="url(#ar2)" />

        {/* === Step 6 — Report === */}
        <g transform="translate(800, 152)">
          <text x="0" y="-8" className="step-num">[6]</text>
          <rect width="64" height="80" rx="8" className="stroke" fill={"oklch(0.97 0.005 90)"} />
          <text x="32" y="20" textAnchor="middle" className="box-title">REPORT</text>
          <line x1="8" y1="28" x2="56" y2="28" className="stroke-soft" />
          <line x1="10" y1="38" x2="54" y2="38" className="stroke-soft" />
          <line x1="10" y1="46" x2="48" y2="46" className="stroke-soft" />
          <line x1="10" y1="54" x2="52" y2="54" className="stroke-soft" />
          <line x1="10" y1="62" x2="42" y2="62" className="stroke-soft" />
          <text x="32" y="74" textAnchor="middle" className="caption">.html</text>
        </g>

        {/* Legend at bottom */}
        <g transform="translate(60, 300)">
          <circle cx="0" cy="0" r="3" fill="oklch(0.58 0.10 45)" />
          <text x="10" y="3" className="caption">corpus input</text>
          <circle cx="120" cy="0" r="3" fill="#1a1917" />
          <text x="130" y="3" className="caption">deterministic path</text>
          <circle cx="280" cy="0" r="3" fill="oklch(0.50 0.07 145)" />
          <text x="290" y="3" className="caption">optional LLM branch</text>
          <text x="780" y="3" textAnchor="end" className="caption">N competitors · ranked</text>
        </g>
      </svg>
    </div>
  );
}

/* === Modal === */
function Modal({ open, onClose, title, subtitle, children }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="close">
            <Icon name="x" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

window.PicaUI = {
  Icon, Sec, Field, Dot, Tabs, Tag, Readout, Bar, Help, Surface, ViewHero, Modal, PipelineFig, WindowFrame,
};
