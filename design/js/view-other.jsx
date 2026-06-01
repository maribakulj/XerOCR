/* Library + Reports + System views (v2) */
const { Sec: SecR, Field: FieldR, Dot: DotR, Tabs: TabsR, Tag: TagR, Readout: ReadoutR, Bar: BarR, Help: HelpR, Surface: SurfaceR, ViewHero: ViewHeroR, Icon: IconR, Modal: ModalR } = window.PicaUI;

/* ===== LIBRARY VIEW =====
   Replaces the old Import view + corpus management.
   Two main panes: "My corpora" and "Discover" (HTR-United / HuggingFace / IIIF / eScriptorium).
*/
function LibraryView({ t, lang }) {
  const [pane, setPane] = React.useState("local");
  const [source, setSource] = React.useState("htr-united");
  const corpora = window.PicaData.HTR_CORPORA;
  const hf = window.PicaData.HF_DATASETS;

  const LOCAL = [
    { name: "corpus_psaumes_240", lang: "lat", script: "Caroline", pages: 240, src: "Upload · 2026-05-18", used: "3 benchmarks" },
    { name: "rimes_test_sample", lang: "fra", script: "Modern cursive", pages: 84, src: "HF · RIMES-2011", used: "1 benchmark" },
    { name: "press_1900_subset", lang: "fra", script: "Modern print", pages: 1240, src: "Gallica IIIF", used: "2 benchmarks" },
    { name: "bullinger_letters_28", lang: "lat", script: "Secretary", pages: 28, src: "HTR-United", used: "—" },
  ];

  return (
    <div className="view-enter">
      <window.PicaUI.WindowFrame
        title="PICARONES · LIBRARY"
        meta={["/corpora", LOCAL.length + " local", corpora.length + " remote"]}
      >
      <ViewHeroR
        eyebrow="VIEW · LIBRARY"
        name={lang === "fr" ? "Bibliothèque de corpus" : "Corpus library"}
        desc={lang === "fr" ? "Corpus locaux et catalogues distants — toute la matière en un seul endroit." : "Local corpora and remote catalogues — all material in one place."}
        stats={[
          { v: LOCAL.length, k: "LOCAL" },
          { v: corpora.length, k: "HTR-UNITED" },
          { v: hf.length, k: "HUGGINGFACE" },
          { v: LOCAL.reduce((s, c) => s + c.pages, 0).toLocaleString(), k: "PAGES" },
        ]}
      />

      <div className="tabs" style={{ alignSelf: "flex-start" }}>
        <button className={pane === "local" ? "on" : ""} onClick={() => setPane("local")}>
          {lang === "fr" ? "Mes corpus" : "My corpora"}
        </button>
        <button className={pane === "discover" ? "on" : ""} onClick={() => setPane("discover")}>
          {lang === "fr" ? "Découvrir" : "Discover"}
        </button>
      </div>

      {pane === "local" && (
        <SecR num="01" title={lang === "fr" ? "Corpus locaux" : "Local corpora"}
          sub={lang === "fr" ? "Téléversés, importés ou pointés depuis le système de fichiers" : "Uploaded, imported, or pointed at from the filesystem"}
          aside={<>{LOCAL.length} CORPORA · {LOCAL.reduce((s, c) => s + c.pages, 0).toLocaleString()} PAGES TOTAL</>}
        >
          <div className="grid-2">
            <div
              className="dropzone"
              onClick={() => {}}
              style={{ minHeight: 220, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}
            >
              <span className="dz-marker"><IconR name="upload" size={20} /></span>
              <div style={{ fontWeight: 500, fontSize: 14, color: "var(--ink)" }}>{t("drop_zip")}</div>
              <div className="foot" style={{ marginTop: 6 }}>ZIP · max 500 MB · pairs auto-detected</div>
              <button className="btn btn-sm" style={{ marginTop: 14 }}>Or browse a folder</button>
            </div>
            <div className="stack">
              {LOCAL.map((c, i) => (
                <div key={c.name} className="ds-card" style={{ padding: "14px 18px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div className="ds-name" style={{ fontSize: 14 }}>{c.name}</div>
                    <span className="foot">{c.src}</span>
                  </div>
                  <div className="ds-meta">
                    <span>LANG · <b>{c.lang}</b></span>
                    <span>SCRIPT · <b>{c.script}</b></span>
                    <span>PAGES · <b className="num">{c.pages.toLocaleString()}</b></span>
                    <span>USED · <b>{c.used}</b></span>
                  </div>
                  <div className="row" style={{ marginTop: 6 }}>
                    <button className="btn btn-sm btn-primary"><IconR name="play" size={12} /> Use in benchmark</button>
                    <button className="btn btn-sm btn-ghost">Inspect</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SecR>
      )}

      {pane === "discover" && (
        <>
          <SecR num="01" title={lang === "fr" ? "Sources distantes" : "Remote sources"} sub={lang === "fr" ? "Catalogues, datasets, manifestes" : "Catalogues, datasets, manifests"}>
            <div className="source-switch">
              {[
                { v: "htr-united", l: "HTR-United", n: "23 catalogues", g: "HU" },
                { v: "huggingface", l: "HuggingFace", n: "~840 datasets", g: "HF" },
                { v: "iiif", l: "IIIF manifest", n: "any institution", g: "II" },
                { v: "escriptorium", l: "eScriptorium", n: "self-hosted", g: "eS" },
              ].map((s) => (
                <button key={s.v} className={"source-chip" + (source === s.v ? " on" : "")} onClick={() => setSource(s.v)}>
                  <span className="src-glyph">{s.g}</span>
                  <span>{s.l}</span>
                  <span className="src-count">{s.n}</span>
                </button>
              ))}
            </div>
          </SecR>

          {source === "htr-united" && (
            <SecR num="02" title={t("import_htr")} sub={t("import_htr_desc")}>
              <div className="grid-4" style={{ marginBottom: 18 }}>
                <FieldR label="Search"><input type="search" placeholder="médiéval, latin, manuscrits…" /></FieldR>
                <FieldR label={t("language")}>
                  <select><option>All</option><option>Latin</option><option>French</option><option>English</option><option>Spanish</option></select>
                </FieldR>
                <FieldR label={t("script")}>
                  <select><option>All</option><option>Caroline</option><option>Gothic</option><option>Cursive</option><option>Procesal</option></select>
                </FieldR>
                <div style={{ display: "flex", alignItems: "flex-end" }}>
                  <button className="btn btn-primary btn-block"><IconR name="search" /> {t("search")}</button>
                </div>
              </div>
              <div className="grid-2">
                {corpora.map((c) => (
                  <div key={c.name} className="ds-card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <div className="ds-name">{c.name}</div>
                      <TagR>{c.license}</TagR>
                    </div>
                    <div className="ds-desc">{c.desc}</div>
                    <div className="ds-meta">
                      <span>LANG · <b>{c.lang}</b></span>
                      <span>SCRIPT · <b>{c.script}</b></span>
                      <span>PAGES · <b className="num">{c.pages.toLocaleString()}</b></span>
                    </div>
                    <div className="row" style={{ marginTop: 8 }}>
                      <button className="btn btn-sm btn-primary"><IconR name="download" size={13} /> Import</button>
                      <button className="btn btn-sm btn-ghost">Preview</button>
                    </div>
                  </div>
                ))}
              </div>
            </SecR>
          )}

          {source === "huggingface" && (
            <SecR num="02" title={t("import_hf")} sub={t("import_hf_desc")}>
              <div className="grid-4" style={{ marginBottom: 18 }}>
                <FieldR label="Search"><input type="search" placeholder="medieval OCR, IAM, RIMES…" /></FieldR>
                <FieldR label={t("language")}><input type="text" placeholder="French, Latin…" /></FieldR>
                <FieldR label={t("tags")}><input type="text" placeholder="ocr, htr, historical" /></FieldR>
                <div style={{ display: "flex", alignItems: "flex-end" }}>
                  <button className="btn btn-primary btn-block"><IconR name="search" /> {t("search")}</button>
                </div>
              </div>
              <div className="grid-2">
                {hf.map((d) => (
                  <div key={d.name} className="ds-card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <div className="ds-name">{d.name}</div>
                      <span className="foot">⤓ {d.downloads} · ♥ {d.likes}</span>
                    </div>
                    <div className="ds-desc">{d.desc}</div>
                    <div className="ds-tags">
                      {d.tags.map((tg) => <TagR key={tg}>{tg}</TagR>)}
                    </div>
                    <div className="row" style={{ marginTop: 8 }}>
                      <button className="btn btn-sm btn-primary"><IconR name="download" size={13} /> Import</button>
                      <button className="btn btn-sm btn-ghost">View on HF</button>
                    </div>
                  </div>
                ))}
              </div>
            </SecR>
          )}

          {source === "iiif" && (
            <SecR num="02" title="IIIF Manifest" sub="Any institutional repository exposing a IIIF Presentation API">
              <div className="grid-2">
                <div className="stack">
                  <FieldR label="Manifest URL" hint="https://gallica.bnf.fr/iiif/.../manifest.json">
                    <input type="text" placeholder="https://" />
                  </FieldR>
                  <FieldR label="Local name" opt="optional">
                    <input type="text" placeholder="my_iiif_corpus" />
                  </FieldR>
                  <div className="row">
                    <button className="btn btn-primary"><IconR name="download" size={13} /> Pull manifest</button>
                    <button className="btn">Inspect</button>
                  </div>
                </div>
                <HelpR>
                  IIIF manifests describe digitised objects (canvases, ranges, annotations). XerOCR pulls images + textual
                  annotations (if present) and writes them into a local corpus folder.
                </HelpR>
              </div>
            </SecR>
          )}

          {source === "escriptorium" && (
            <SecR num="02" title="eScriptorium" sub="Pull from a self-hosted eScriptorium instance">
              <div className="grid-3">
                <FieldR label="Endpoint"><input type="text" placeholder="https://escriptorium.example.org/api" /></FieldR>
                <FieldR label="Username"><input type="text" /></FieldR>
                <FieldR label="API token"><input type="text" placeholder="••••••••••••" /></FieldR>
              </div>
              <div style={{ marginTop: 14 }}><button className="btn btn-primary"><IconR name="refresh" size={13} /> List projects</button></div>
            </SecR>
          )}
        </>
      )}
    </window.PicaUI.WindowFrame>
    </div>
  );
}

/* ===== REPORTS VIEW ===== */
function ReportsView({ t, lang }) {
  const reports = window.PicaData.REPORTS;
  const [q, setQ] = React.useState("");
  const [selected, setSelected] = React.useState(0);
  const filtered = reports.filter(r => r.name.toLowerCase().includes(q.toLowerCase()));
  const sel = filtered[selected] || filtered[0];

  return (
    <div className="view-enter">
      <window.PicaUI.WindowFrame
        title="PICARONES · REPORTS"
        meta={["/rapports", reports.length + " files", "55.1 MB"]}
      >
      <ViewHeroR
        eyebrow="VIEW · REPORTS"
        name={t("reports_title")}
        desc={t("reports_desc")}
        stats={[
          { v: reports.length, k: "REPORTS" },
          { v: "55.1", k: "MB TOTAL" },
          { v: reports.reduce((s, r) => s + r.docs, 0).toLocaleString(), k: "DOCS" },
          { v: "May 18", k: "LATEST" },
        ]}
      />

      <SecR num="01" title={lang === "fr" ? "Historique des rapports" : "Report history"} sub={lang === "fr" ? "Cliquez un rapport pour prévisualiser" : "Click a report to preview"}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 14 }}>
          <div className="stack">
            <div className="row">
              <input type="search" placeholder="search reports…" value={q} onChange={(e) => setQ(e.target.value)} />
              <button className="btn btn-ghost btn-sm"><IconR name="refresh" size={13} /></button>
            </div>
            <div className="stack-sm">
              {filtered.map((r, i) => (
                <div
                  key={r.name}
                  onClick={() => setSelected(i)}
                  style={{
                    padding: "14px 16px",
                    background: selected === i ? "var(--ink)" : "var(--surface)",
                    color: selected === i ? "var(--paper)" : "var(--ink)",
                    borderRadius: "var(--r-md)",
                    cursor: "pointer",
                    transition: "background 0.15s, color 0.15s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, fontWeight: 500 }}>{r.name}</div>
                  </div>
                  <div style={{ display: "flex", gap: 8, fontFamily: "var(--mono)", fontSize: 10.5, color: selected === i ? "rgba(239,237,232,0.55)" : "var(--g-400)", letterSpacing: "0.04em" }}>
                    <span>{r.date}</span>
                    <span>·</span>
                    <span>{r.engines} ENGINES</span>
                    <span>·</span>
                    <span>{r.docs} DOCS</span>
                    <span>·</span>
                    <span>{r.size}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <SurfaceR>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div>
                <div className="label">PREVIEW</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 500, marginTop: 4 }}>{sel.name}</div>
              </div>
              <div className="row">
                <button className="btn btn-primary btn-sm"><IconR name="arrow-right" size={13} /> Open</button>
                <button className="btn btn-sm"><IconR name="download" size={13} /></button>
              </div>
            </div>
            <div className="grid-4" style={{ marginBottom: 18 }}>
              <ReadoutR label="Engines" value={sel.engines} />
              <ReadoutR label="Documents" value={sel.docs} />
              <ReadoutR label="Best CER" value={sel.best.cer.toFixed(2)} unit="%" />
              <ReadoutR label="Size" value={sel.size.split(" ")[0]} unit={sel.size.split(" ")[1]} />
            </div>
            <div className="label" style={{ marginBottom: 8 }}>Ranking snapshot</div>
            <table className="data">
              <thead><tr><th>#</th><th>{t("engine")}</th><th className="num-cell">{t("cer")} %</th><th className="num-cell">{t("wer")} %</th></tr></thead>
              <tbody>
                {window.PicaData.RESULTS.slice(0, sel.engines).map((r) => (
                  <tr key={r.rank}>
                    <td><span className={"rank-pill" + (r.rank === 1 ? " first" : "")}>#{r.rank}</span></td>
                    <td style={{ fontWeight: 500 }}>{r.engine}</td>
                    <td className="num-cell">{r.cer.toFixed(2)}</td>
                    <td className="num-cell">{r.wer.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <hr className="hr" />
            <div className="label" style={{ marginBottom: 8 }}>Sample diff — psaumes_004 · pero vs ground truth</div>
            <div className="diff">
              Beatus uir qui non <span className="del">abit</span><span className="add">abiit</span> in consilio impiorum{" "}
              et in uia peccato<span className="del">res</span><span className="add">rum</span> non stetit
            </div>
          </SurfaceR>
        </div>
      </SecR>
    </window.PicaUI.WindowFrame>
    </div>
  );
}

/* ===== SYSTEM MODAL — engines + LLMs all in one place ===== */
function SystemPanel({ open, onClose, t, lang }) {
  const [tab, setTab] = React.useState("ocr");
  const ocr = window.PicaData.OCR_ENGINES;
  const llms = window.PicaData.LLM_PROVIDERS;

  return (
    <ModalR
      open={open}
      onClose={onClose}
      title={lang === "fr" ? "Système" : "System"}
      subtitle={lang === "fr" ? "Moteurs, modèles, télémétrie, paramètres." : "Engines, models, telemetry, settings."}
    >
      <TabsR
        value={tab}
        onChange={setTab}
        options={[
          { value: "ocr", label: "OCR / HTR" },
          { value: "llm", label: "LLM / VLM" },
          { value: "telemetry", label: "Telemetry" },
          { value: "settings", label: "Settings" },
        ]}
      />

      <div style={{ marginTop: 18 }}>
        {tab === "ocr" && (
          <SurfaceR variant="flat">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <div className="label label-strong">{t("engines_ocr")}</div>
              <div className="label">{ocr.filter(e => e.status === "online").length}/{ocr.length} ONLINE</div>
            </div>
            {ocr.map((e) => (
              <div key={e.id} className="engine-row">
                <DotR state={e.status === "online" ? "on" : "off"} />
                <div>
                  <div className="e-name">{e.name}</div>
                  <div className="e-type">{e.type}</div>
                </div>
                <div className="e-detail">{e.detail}</div>
                <div style={{ color: "var(--g-400)", fontSize: 11, fontFamily: "var(--mono)" }}>
                  {e.status === "online" ? "—" : "pip install -e .[" + e.id + "]"}
                </div>
                <TagR variant={e.status === "online" ? "fern" : null}>
                  {e.status === "online" ? t("online") : t("offline")}
                </TagR>
              </div>
            ))}
          </SurfaceR>
        )}

        {tab === "llm" && (
          <div className="grid-2">
            {llms.map((p) => (
              <SurfaceR key={p.id} variant="flat">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <DotR state={p.status === "online" ? "on" : "off"} />
                    <span style={{ fontSize: 15, fontWeight: 600 }}>{p.name}</span>
                  </div>
                  <TagR variant={p.status === "online" ? "slate" : null}>
                    {p.status === "online" ? t("configured") : t("missing_key")}
                  </TagR>
                </div>
                <div className="label" style={{ marginBottom: 10 }}>{p.models.length} models</div>
                {p.models.map((m) => (
                  <div key={m} className="mono" style={{ fontSize: 12, display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--g-50)" }}>
                    <span>{m}</span>
                    <span style={{ color: "var(--g-400)" }}>{p.status === "online" ? "ready" : "—"}</span>
                  </div>
                ))}
              </SurfaceR>
            ))}
          </div>
        )}

        {tab === "telemetry" && (
          <div className="grid-2">
            <SurfaceR variant="flat">
              <div className="label" style={{ marginBottom: 10 }}>Process</div>
              <div className="stack-sm">
                {[
                  ["CPU", "14 %"], ["RAM", "2.1 / 16 GB"], ["GPU", "off"],
                  ["Active job", "—"], ["Queued runs", "0"],
                ].map(([k, v]) => (
                  <div key={k} className="sys-row"><span className="k">{k}</span><span className="v">{v}</span></div>
                ))}
              </div>
            </SurfaceR>
            <SurfaceR variant="flat">
              <div className="label" style={{ marginBottom: 10 }}>Web layer</div>
              <div className="stack-sm">
                {[
                  ["SSE", "live"], ["CSRF", "enforced"], ["Rate limit", "100 / min"],
                  ["Upload retention", "7 days"], ["Public mode", "off"],
                ].map(([k, v]) => (
                  <div key={k} className="sys-row"><span className="k">{k}</span><span className="v">{v}</span></div>
                ))}
              </div>
            </SurfaceR>
          </div>
        )}

        {tab === "settings" && (
          <div className="grid-2">
            <FieldR label="Default normalisation profile">
              <select defaultValue="medieval_latin">{window.PicaData.NORM_PROFILES.map(p => <option key={p}>{p}</option>)}</select>
            </FieldR>
            <FieldR label="Default output folder"><input type="text" defaultValue="./rapports/" /></FieldR>
            <FieldR label="Reports retention (days)"><input type="number" defaultValue="365" /></FieldR>
            <FieldR label="Upload retention (days)"><input type="number" defaultValue="7" /></FieldR>
          </div>
        )}
      </div>
    </ModalR>
  );
}

window.LibraryView = LibraryView;
window.ReportsView = ReportsView;
window.SystemPanel = SystemPanel;
