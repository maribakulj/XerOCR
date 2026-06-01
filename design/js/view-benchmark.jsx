/* Benchmark view — v2 soft rounded */
const { Sec, Field, Dot, Tabs, Tag, Readout, Bar, Help, Surface, ViewHero, Icon } = window.PicaUI;

function BenchmarkView({ t, lang, state, setState }) {
  const {
    corpusPath, competitors, composeMode,
    composeOCR, composeOCRLang, composeLLMProv, composeLLM, composeMode2, composePrompt,
    benchPhase, benchProgress,
  } = state;

  const set = (patch) => setState((s) => ({ ...s, ...patch }));

  const ocrEngines = window.PicaData.OCR_ENGINES;
  const llms = window.PicaData.LLM_PROVIDERS;

  const corpusInfo = { pages: 240, gt: 240, script: "Caroline (11ᵉ s.)", lang: "lat" };

  return (
    <div className="view-enter">
      <window.PicaUI.WindowFrame
        title="PICARONES · BENCHMARK"
        meta={["/jobs/active", "rc4", benchPhase.toUpperCase()]}
      >
      <ViewHero
        eyebrow="VIEW · BENCHMARK"
        name={t("bench_title")}
        desc={t("bench_desc")}
        stats={[
          { v: corpusInfo.pages, k: "PAGES" },
          { v: competitors.length, k: "COMPETITORS" },
          { v: "med.lat", k: "NORM" },
          { v: benchPhase === "running" ? "RUN" : benchPhase === "done" ? "DONE" : "READY", k: "STATE" },
        ]}
      />

      {/* 01. CORPUS — compact, single-card */}
      <Sec
        num="01"
        tone="clay"
        title={t("bench_corpus")}
        sub={t("bench_corpus_desc")}
        aside={<>{corpusInfo.gt} / {corpusInfo.pages} GT PAIRS · {corpusInfo.script}</>}
      >
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
          <Surface variant="flat">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--g-600)" }}>~/heritage/{corpusPath}</div>
              <button className="btn btn-ghost btn-sm">change corpus</button>
            </div>
            <div className="file-list" style={{ background: "var(--paper)" }}>
              {[
                { n: "psaumes_001.jpg", t: "img", s: "2.1 MB" },
                { n: "psaumes_001.gt.txt", t: "gt", s: "1.2 KB", sel: true },
                { n: "psaumes_002.jpg", t: "img", s: "2.0 MB" },
                { n: "psaumes_002.gt.txt", t: "gt", s: "1.4 KB" },
                { n: "psaumes_002.alto.xml", t: "xml", s: "8.4 KB" },
                { n: "psaumes_003.jpg", t: "img", s: "1.9 MB" },
              ].map((f, i) => (
                <div key={i} className={"file-row" + (f.sel ? " selected" : "")}>
                  <span className="icon">{f.t === "img" ? "◐" : f.t === "xml" ? "⟨⟩" : "≡"}</span>
                  <span>{f.n}</span>
                  <span className="meta">{f.t.toUpperCase()}</span>
                  <span className="meta">{f.s}</span>
                </div>
              ))}
            </div>
          </Surface>
          <div className="stack">
            <Surface variant="flat">
              <div className="label" style={{ marginBottom: 12 }}>SAMPLE — psaumes_001.gt.txt</div>
              <div className="diff" style={{ background: "var(--paper)", fontSize: 14 }}>
                Beatus uir qui non abiit in consilio impiorum<br/>
                et in uia peccatorum non stetit<br/>
                et in cathedra pestilentiæ non sedit.
              </div>
            </Surface>
            <Help>
              Without ground truth, no benchmark. Picarones measures agreement with a known reference,
              not absolute transcription quality.
            </Help>
          </div>
        </div>
      </Sec>

      {/* 02. COMPETITORS — composer === */}
      <Sec
        num="02"
        tone="slate"
        title={t("bench_competitors")}
        sub={t("bench_competitors_desc")}
        aside={<>{competitors.length} QUEUED</>}
      >
        <div className="compose-modes">
          {[
            { v: "ocr", l: "OCR only" },
            { v: "pipeline", l: "OCR → LLM" },
            { v: "postcorr", l: "Post-correction" },
            { v: "zeroshot", l: "VLM zero-shot" },
          ].map((m) => (
            <button key={m.v} className={composeMode === m.v ? "on" : ""} onClick={() => set({ composeMode: m.v })}>
              {m.l}
            </button>
          ))}
        </div>

        {composeMode === "ocr" && (
          <div className="grid-3">
            <Field label="OCR engine">
              <select value={composeOCR} onChange={(e) => set({ composeOCR: e.target.value })}>
                {ocrEngines.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </Field>
            <Field label="Model / lang">
              <select value={composeOCRLang} onChange={(e) => set({ composeOCRLang: e.target.value })}>
                <option>fra+lat</option><option>fra</option><option>lat</option><option>eng+fra</option>
              </select>
            </Field>
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button
                className="btn btn-primary btn-block"
                onClick={() => set({
                  competitors: [...competitors, {
                    id: "C" + String(competitors.length + 1).padStart(2, "0"),
                    kind: "OCR",
                    name: ocrEngines.find(e => e.id === composeOCR)?.name + " (" + composeOCRLang + ")",
                    chain: [ocrEngines.find(e => e.id === composeOCR)?.name],
                    color: "ink",
                  }]
                })}
              ><Icon name="plus" /> {t("add_competitor")}</button>
            </div>
          </div>
        )}

        {composeMode === "pipeline" && (
          <div className="stack">
            <div className="grid-2">
              <Field label="OCR engine">
                <select value={composeOCR} onChange={(e) => set({ composeOCR: e.target.value })}>
                  {ocrEngines.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
              </Field>
              <Field label="Lang / model">
                <select value={composeOCRLang} onChange={(e) => set({ composeOCRLang: e.target.value })}>
                  <option>fra+lat</option><option>medieval_latin</option><option>fra</option>
                </select>
              </Field>
            </div>
            <div className="grid-3">
              <Field label="LLM provider">
                <select value={composeLLMProv} onChange={(e) => set({ composeLLMProv: e.target.value })}>
                  {llms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </Field>
              <Field label="LLM model">
                <select value={composeLLM} onChange={(e) => set({ composeLLM: e.target.value })}>
                  {llms.find(p => p.id === composeLLMProv)?.models.map((m) => <option key={m}>{m}</option>)}
                </select>
              </Field>
              <Field label="Mode">
                <select value={composeMode2} onChange={(e) => set({ composeMode2: e.target.value })}>
                  <option value="text_only">Post-correction (text)</option>
                  <option value="text_and_image">Post-correction (text + image)</option>
                </select>
              </Field>
            </div>
            <div className="grid-2">
              <Field label="Prompt">
                <select value={composePrompt} onChange={(e) => set({ composePrompt: e.target.value })}>
                  <option>medieval_latin_v3</option>
                  <option>preserve_orthography</option>
                  <option>diplomatic_edition</option>
                </select>
              </Field>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button
                  className="btn btn-primary btn-block"
                  onClick={() => set({
                    competitors: [...competitors, {
                      id: "C" + String(competitors.length + 1).padStart(2, "0"),
                      kind: "OCR→LLM",
                      name: (ocrEngines.find(e => e.id === composeOCR)?.name) + " → " + composeLLM,
                      chain: [ocrEngines.find(e => e.id === composeOCR)?.name, composeLLM],
                      color: "slate",
                    }]
                  })}
                ><Icon name="plus" /> {t("add_competitor")}</button>
              </div>
            </div>
          </div>
        )}

        {composeMode === "zeroshot" && (
          <div className="grid-3">
            <Field label="VLM provider"><select><option>OpenAI</option><option>Anthropic</option><option>Mistral</option></select></Field>
            <Field label="VLM model"><select><option>gpt-4o</option><option>claude-opus-4</option><option>pixtral-large</option></select></Field>
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button
                className="btn btn-primary btn-block"
                onClick={() => set({
                  competitors: [...competitors, {
                    id: "C" + String(competitors.length + 1).padStart(2, "0"),
                    kind: "ZERO-SHOT",
                    name: "claude-opus-4 (zero-shot)",
                    chain: ["claude-opus-4"],
                    color: "fern",
                  }]
                })}
              ><Icon name="plus" /> {t("add_competitor")}</button>
            </div>
          </div>
        )}

        {composeMode === "postcorr" && (
          <div className="grid-3">
            <Field label="OCR corpus" hint="pre-computed .ocr.txt"><select><option>psaumes_240_pero_baseline</option></select></Field>
            <Field label="LLM"><select><option>claude-sonnet-4.5</option><option>gpt-4o</option></select></Field>
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button className="btn btn-primary btn-block"><Icon name="plus" /> {t("add_competitor")}</button>
            </div>
          </div>
        )}

        <hr className="hr" />

        <div className="label" style={{ marginBottom: 10 }}>QUEUE · {competitors.length} competitor(s)</div>
        {competitors.length === 0 && <div className="empty">{t("no_competitors")}</div>}
        <div className="stack-sm">
          {competitors.map((c, i) => (
            <div key={c.id} className="competitor">
              <span className={"c-id " + c.color}>{c.id}</span>
              <div>
                <div className="c-name">{c.name}</div>
                <div className="c-chain">
                  <Tag>{c.kind}</Tag>
                  {c.chain.map((step, idx) => (
                    <span key={idx} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      {idx > 0 && <span className="arrow">→</span>}
                      {step}
                    </span>
                  ))}
                </div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => set({ competitors: competitors.filter((_, j) => j !== i) })}>
                <Icon name="x" size={13} />
              </button>
            </div>
          ))}
        </div>
      </Sec>

      {/* 03. OPTIONS */}
      <Sec num="03" tone="butter" title={t("bench_options")} sub={t("bench_options_desc")}>
        <div className="grid-4">
          <Field label={t("norm_profile")} hint="MUFI v4.0 · TEI P5">
            <select defaultValue="medieval_latin">
              {window.PicaData.NORM_PROFILES.map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>
          <Field label={t("char_exclude")} hint="comma-separated">
            <input type="text" defaultValue="', -, –, ." />
          </Field>
          <Field label={t("output_dir")}>
            <input type="text" defaultValue="./rapports/" />
          </Field>
          <Field label={t("report_name")} opt="optional">
            <input type="text" placeholder="rapport_2026_05_20" />
          </Field>
        </div>
      </Sec>

      {/* 04. RUN */}
      <Sec num="04" tone="fern" title="Execute" sub="Run the benchmark on the queued competitors"
        aside={<>
          <button className="btn btn-ghost btn-sm">{t("save_config")}</button>
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: 6 }}>{t("load_config")}</button>
        </>}
      >
        {benchPhase === "idle" && (
          <div className="row">
            <button
              className="btn btn-primary"
              style={{ fontSize: 14, padding: "12px 24px" }}
              disabled={competitors.length === 0}
              onClick={() => set({ benchPhase: "running", benchProgress: 0 })}
            >
              <Icon name="play" /> {t("bench_run")}
            </button>
            <Help>
              {competitors.length === 0
                ? "Add at least one competitor in section 02 to begin."
                : `Will run ${competitors.length} competitor(s) on ${corpusInfo.pages} pages. Est. ~${competitors.length * 4} min.`}
            </Help>
          </div>
        )}

        {benchPhase === "running" && (
          <div className="stack">
            <div className="bench-grid">
              <Surface>
                <div className="label" style={{ marginBottom: 6 }}>{t("progress")}</div>
                <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em" }} className="num">
                  {benchProgress.toFixed(0)}<span style={{ color: "var(--g-300)", fontSize: 16 }}> / 240 pages</span>
                </div>
                <div className="progress thick" style={{ marginTop: 12 }}>
                  <div className="progress-bar" style={{ width: (benchProgress / 240 * 100) + "%" }} />
                </div>
              </Surface>
              <Surface>
                <div className="label" style={{ marginBottom: 6 }}>{t("elapsed")} / {t("eta")}</div>
                <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em" }} className="num">
                  {Math.floor(benchProgress * 0.6)}s<span style={{ color: "var(--g-300)", fontSize: 16 }}> / ~{Math.max(0, Math.floor((240 - benchProgress) * 0.6))}s</span>
                </div>
                <div className="foot" style={{ marginTop: 12 }}>Phase: OCR · pero, mistral_ocr, tesseract</div>
              </Surface>
              <Surface style={{ gridColumn: "1 / -1" }}>
                <div className="label" style={{ marginBottom: 10 }}>PER COMPETITOR</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {competitors.map((c, i) => {
                    const pct = Math.max(0, Math.min(100, (benchProgress / 240 * 100) - i * 6));
                    return (
                      <div key={c.id} style={{ display: "grid", gridTemplateColumns: "60px 1fr 1fr 60px", gap: 14, alignItems: "center", fontSize: 12.5 }}>
                        <span className="mono" style={{ color: "var(--g-500)" }}>{c.id}</span>
                        <span>{c.name}</span>
                        <span className={"progress " + c.color}><span className="progress-bar" style={{ width: pct + "%" }} /></span>
                        <span className="num" style={{ textAlign: "right", color: "var(--g-500)" }}>{pct.toFixed(0)}%</span>
                      </div>
                    );
                  })}
                </div>
              </Surface>
            </div>

            <Surface variant="tinted">
              <div className="label" style={{ marginBottom: 8 }}>{t("log")} · live</div>
              <div className="log">
                {window.PicaData.LOG_LINES.slice(0, Math.min(window.PicaData.LOG_LINES.length, Math.floor(benchProgress / 24) + 3)).map((l, i) => (
                  <div key={i}>
                    <span className="ts">{l.ts}</span>
                    <span className={l.lvl}>{l.text}</span>
                  </div>
                ))}
              </div>
            </Surface>

            <div className="row">
              <button className="btn btn-danger" onClick={() => set({ benchPhase: "idle", benchProgress: 0 })}>
                <Icon name="x" /> {t("bench_cancel")}
              </button>
              <button className="btn btn-ghost" onClick={() => set({ benchPhase: "done", benchProgress: 240 })}>
                Fast-forward <Icon name="arrow-right" />
              </button>
            </div>
          </div>
        )}

        {benchPhase === "done" && (
          <div className="stack">
            <div className="grid-4">
              <Readout label="Best CER" value="4.82" unit="%" delta={{ dir: "up", text: "−1.4 vs baseline" }} variant="fern" />
              <Readout label="Duration" value="14:32" unit="min" variant="slate" />
              <Readout label="Pages processed" value="240" variant="clay" />
              <Readout label="Total cost" value="$9.84" delta={{ dir: "up", text: "within budget" }} variant="ink" />
            </div>

            <Surface>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div className="label label-strong">Ranking · CER (lower is better)</div>
                <div className="label">5 competitors · 240 pages · medieval_latin</div>
              </div>
              <table className="data">
                <thead>
                  <tr>
                    <th style={{ width: 60 }}>#</th>
                    <th>{t("engine")}</th>
                    <th>{t("model")}</th>
                    <th className="num-cell">{t("cer")} %</th>
                    <th className="num-cell">{t("wer")} %</th>
                    <th className="num-cell">{t("speed")}</th>
                    <th className="num-cell">{t("cost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {window.PicaData.RESULTS.map((r) => (
                    <tr key={r.rank}>
                      <td><span className={"rank-pill" + (r.rank === 1 ? " first" : "")}>#{r.rank}</span></td>
                      <td style={{ fontWeight: 500 }}>{r.engine}</td>
                      <td className="mono" style={{ color: "var(--g-500)", fontSize: 12 }}>{r.model}</td>
                      <td className="num-cell">{r.cer.toFixed(2)}</td>
                      <td className="num-cell">{r.wer.toFixed(1)}</td>
                      <td className="num-cell">{r.speed}</td>
                      <td className="num-cell">{r.cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Surface>

            <div className="grid-2">
              <Surface>
                <div className="label" style={{ marginBottom: 12 }}>CER distribution</div>
                {window.PicaData.RESULTS.map((r) => (
                  <Bar key={r.rank} label={r.engine} value={r.cer} max={12} unit="%" color={r.rank === 1 ? "fern" : r.rank === 2 ? "slate" : "ink"} />
                ))}
              </Surface>
              <Surface>
                <div className="label" style={{ marginBottom: 12 }}>{t("synthesis")}</div>
                <ol style={{ paddingLeft: 18, fontFamily: "var(--serif)", fontSize: 13.5, lineHeight: 1.6, color: "var(--g-600)" }}>
                  {window.PicaData.SYNTHESIS_SENTENCES.map((s, i) => (
                    <li key={i} style={{ marginBottom: 10 }}>{s}</li>
                  ))}
                </ol>
              </Surface>
            </div>

            <div className="row">
              <button className="btn btn-primary"><Icon name="arrow-right" /> {t("open_report")}</button>
              <button className="btn"><Icon name="download" /> Download JSON</button>
              <button className="btn btn-ghost" onClick={() => set({ benchPhase: "idle", benchProgress: 0 })}>↺ New run</button>
            </div>
          </div>
        )}
      </Sec>
    </window.PicaUI.WindowFrame>
    </div>
  );
}

window.BenchmarkView = BenchmarkView;
