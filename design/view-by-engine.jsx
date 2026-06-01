/* View 02 — Par moteur : galerie + drill-in (motif symétrique à Par document).
   Default = tableau cliquable + agrégats comparatifs.
   Drill-in = profil complet d'un seul moteur. */

/* ==================================================================== */
/* Helpers                                                              */
/* ==================================================================== */

function ThEnriched({ acro, meta, title, gstart, numCell, sortKey, sort, onSort }) {
  const isActive = sortKey && sort?.key === sortKey;
  const isSortable = !!sortKey;
  const arrow = !isSortable ? null : !isActive ? '↕' : sort.dir === 'asc' ? '↑' : '↓';
  const cls = (numCell ? 'num-cell ' : '')
            + (gstart ? 'gstart ' : '')
            + (isSortable ? 'sortable ' : '')
            + (isActive ? 'sort-active' : '');
  return (
    <th className={cls.trim()} title={title}
        onClick={isSortable ? () => onSort(sortKey) : undefined}>
      <span className="th-acro">{acro}{arrow && <span className="th-sort">{arrow}</span>}</span>
      <span className="th-meta">{meta}</span>
    </th>
  );
}

function DataCell({ value, max, color, fmt, gstart, isSortCol }) {
  const rel = Math.max(0, Math.min(1, value / max));
  const intensity = rel < 0.33 ? 'is-low' : rel < 0.66 ? 'is-mid' : 'is-high';
  return (
    <td className={`databar ${intensity}` + (gstart ? ' gstart' : '') + (isSortCol ? ' sort-active' : '')}>
      <span className={`db-fill ${color}`} style={{width: `calc(${rel*100}% - 12px)`}}></span>
      <span className="db-num">{fmt(value)}</span>
    </td>
  );
}

function CellBar({ value, max, color, fmt }) {
  const w = Math.min(100, (value / max) * 100);
  return (
    <span className="cell-bar">
      <span className="cb-track">
        <span className={`cb-fill eng-${color}`} style={{width: w + '%'}}></span>
      </span>
      <span style={{minWidth:'48px',display:'inline-block'}}>{fmt(value)}</span>
    </span>
  );
}

/* ==================================================================== */
/* Overview state — table + comparative aggregates                      */
/* ==================================================================== */

function EngineOverview({ onSelect }) {
  const maxs = {
    cer: 0.10, cer_diplo: 0.10, wer: 0.25, mer: 0.25, wil: 0.40,
    ligature: 1.0, diacritic: 1.0, gini: 0.50, anchor: 1.0,
    ece: 0.10, f1_ner: 1.0, cost: 1.6, speed: 5.0,
  };

  const [sort, setSort] = React.useState({ key: null, dir: 'asc' });
  const handleSort = (key) => {
    setSort(prev => {
      if (prev.key !== key) return { key, dir: 'asc' };
      if (prev.dir === 'asc') return { key, dir: 'desc' };
      return { key: null, dir: 'asc' };
    });
  };
  const sortedEngines = React.useMemo(() => {
    if (!sort.key) return ENGINES;
    const k = sort.key;
    return [...ENGINES].sort((a, b) => {
      const va = a[k], vb = b[k];
      const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [sort]);

  return (
    <React.Fragment>

      {/* === Tableau cliquable (entrée principale) === */}
      <div className="sec" style={{padding:'20px 8px 22px'}}>
        <div style={{padding:'0 20px 14px',display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:'18px',flexWrap:'wrap'}}>
          <div style={{flex:1,minWidth:'320px'}}>
            <div className="sec-title" style={{fontSize:'18px',marginBottom:'4px'}}>Tableau des métriques</div>
            <div className="heritage" style={{fontSize:'12.5px'}}>
              Cliquer une ligne pour ouvrir le profil complet d'un moteur. Cliquer un en-tête pour trier ; survoler pour la définition.
            </div>
          </div>
          <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
            <span className="label">ordre actif</span>
            {sort.key === null
              ? <span className="tag tag-mono">manifeste</span>
              : <span className="tag tag-ink">{sort.key} {sort.dir === 'asc' ? '↑' : '↓'}</span>}
            <button className="btn btn-sm btn-ghost"
                    onClick={() => setSort({ key: null, dir: 'asc' })}
                    disabled={sort.key === null}
                    style={{opacity: sort.key === null ? 0.4 : 1}}>
              ↺ réinitialiser
            </button>
          </div>
        </div>

        <table className="data" style={{tableLayout:'fixed'}}>
          <colgroup>
            <col style={{width:'220px'}} />
            <col /><col />
            <col /><col /><col />
            <col /><col />
            <col /><col />
            <col /><col />
            <col /><col />
          </colgroup>
          <thead className="metric-table">
            <tr className="groups">
              <th></th>
              <th colSpan="2" className="gstart">Erreur · caractère</th>
              <th colSpan="3" className="gstart">Erreur · mot</th>
              <th colSpan="2" className="gstart">Philologique</th>
              <th colSpan="2" className="gstart">Fiabilité documentaire</th>
              <th colSpan="2" className="gstart">Calibration · aval</th>
              <th colSpan="2" className="gstart">Économique</th>
            </tr>
            <tr className="cols">
              <ThEnriched acro="Moteur" meta="cliquer une ligne pour ouvrir →" sortKey="name" sort={sort} onSort={handleSort}
                          title="Cliquer pour trier alphabétiquement par nom de moteur" />
              <ThEnriched numCell gstart acro="CER" meta="0 – 1 · ↓ erreurs"
                          sortKey="cer" sort={sort} onSort={handleSort}
                          title="Character Error Rate · part de caractères mal reconnus" />
              <ThEnriched numCell acro="CER diplo." meta="après normalisation"
                          sortKey="cer_diplo" sort={sort} onSort={handleSort}
                          title="CER après application du profil diplomatique" />
              <ThEnriched numCell gstart acro="WER" meta="0 – 1 · ↓ erreurs"
                          sortKey="wer" sort={sort} onSort={handleSort}
                          title="Word Error Rate" />
              <ThEnriched numCell acro="MER" meta="0 – 1 · ↓ erreurs"
                          sortKey="mer" sort={sort} onSort={handleSort}
                          title="Match Error Rate" />
              <ThEnriched numCell acro="WIL" meta="0 – 1 · ↓ info perdue"
                          sortKey="wil" sort={sort} onSort={handleSort}
                          title="Word Information Lost" />
              <ThEnriched numCell gstart acro="Ligatures" meta="0 – 1 · ↑ rappel"
                          sortKey="ligature" sort={sort} onSort={handleSort}
                          title="Part des ligatures MUFI préservées" />
              <ThEnriched numCell acro="Diacritiques" meta="0 – 1 · ↑ rappel"
                          sortKey="diacritic" sort={sort} onSort={handleSort}
                          title="Part des signes diacritiques restitués" />
              <ThEnriched numCell gstart acro="Gini" meta="0 – 1 · ↓ uniforme"
                          sortKey="gini" sort={sort} onSort={handleSort}
                          title="Gini sur les CER par document" />
              <ThEnriched numCell acro="Ancrage" meta="0 – 1 · ↑ ancré"
                          sortKey="anchor" sort={sort} onSort={handleSort}
                          title="Ancrage trigrammes — bas = hallucination probable" />
              <ThEnriched numCell gstart acro="ECE" meta="0 – 1 · ↓ honnête"
                          sortKey="ece" sort={sort} onSort={handleSort}
                          title="Expected Calibration Error" />
              <ThEnriched numCell acro="F1 NER" meta="0 – 1 · ↑ entités"
                          sortKey="f1_ner" sort={sort} onSort={handleSort}
                          title="F1 sur entités nommées" />
              <ThEnriched numCell gstart acro="€ / 1000 p" meta="€ · ↓ moins cher"
                          sortKey="cost" sort={sort} onSort={handleSort}
                          title="Coût indicatif pour 1000 pages" />
              <ThEnriched numCell acro="s / page" meta="sec. · ↓ rapide"
                          sortKey="speed" sort={sort} onSort={handleSort}
                          title="Temps d'inférence moyen par page" />
            </tr>
          </thead>
          <tbody>
            {sortedEngines.map(e => {
              const realIdx = ENGINES.findIndex(x => x.id === e.id);
              return (
                <tr key={e.id} className="row-clickable" onClick={() => onSelect(realIdx)}>
                  <td className={"eng-cell" + (sort.key === 'name' ? ' sort-active' : '')}>
                    <div style={{display:'flex',gap:'10px',alignItems:'center',justifyContent:'space-between'}}>
                      <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
                        <span className={`eng-id ${e.color}`}>{e.id}</span>
                        <span style={{fontWeight:500,fontSize:'13px'}}>{e.name}</span>
                      </div>
                      <span style={{fontFamily:'var(--mono)',fontSize:'10px',color:'var(--g-300)',letterSpacing:'0.04em'}}>→</span>
                    </div>
                  </td>
                  <DataCell gstart isSortCol={sort.key==='cer'}       value={e.cer}        max={maxs.cer}        color={e.color} fmt={v=>pct(v)} />
                  <DataCell        isSortCol={sort.key==='cer_diplo'} value={e.cer_diplo}  max={maxs.cer_diplo}  color={e.color} fmt={v=>pct(v)} />
                  <DataCell gstart isSortCol={sort.key==='wer'}       value={e.wer}        max={maxs.wer}        color={e.color} fmt={v=>pct(v)} />
                  <DataCell        isSortCol={sort.key==='mer'}       value={e.mer}        max={maxs.mer}        color={e.color} fmt={v=>pct(v)} />
                  <DataCell        isSortCol={sort.key==='wil'}       value={e.wil}        max={maxs.wil}        color={e.color} fmt={v=>pct(v)} />
                  <DataCell gstart isSortCol={sort.key==='ligature'}  value={e.ligature}   max={maxs.ligature}   color={e.color} fmt={v=>v.toFixed(3)} />
                  <DataCell        isSortCol={sort.key==='diacritic'} value={e.diacritic}  max={maxs.diacritic}  color={e.color} fmt={v=>v.toFixed(3)} />
                  <DataCell gstart isSortCol={sort.key==='gini'}      value={e.gini}       max={maxs.gini}       color={e.color} fmt={v=>v.toFixed(3)} />
                  <DataCell        isSortCol={sort.key==='anchor'}    value={e.anchor}     max={maxs.anchor}     color={e.color} fmt={v=>v.toFixed(3)} />
                  <DataCell gstart isSortCol={sort.key==='ece'}       value={e.ece}        max={maxs.ece}        color={e.color} fmt={v=>(v*100).toFixed(1)+' %'} />
                  <DataCell        isSortCol={sort.key==='f1_ner'}    value={e.f1_ner}     max={maxs.f1_ner}     color={e.color} fmt={v=>v.toFixed(3)} />
                  <DataCell gstart isSortCol={sort.key==='cost'}      value={e.cost}       max={maxs.cost}       color={e.color} fmt={v=>v.toFixed(2)+' €'} />
                  <DataCell        isSortCol={sort.key==='speed'}     value={e.speed}      max={maxs.speed}      color={e.color} fmt={v=>v.toFixed(1)+' s'} />
                </tr>
              );
            })}
          </tbody>
        </table>

        <div style={{
          margin:'18px 22px 0',
          display:'flex',
          gap:'20px',
          paddingTop:'14px',
          borderTop:'1px solid var(--g-50)',
          flexWrap:'wrap',
          fontSize:'11.5px',
          color:'var(--g-500)',
        }}>
          <span style={{display:'inline-flex',alignItems:'center',gap:'8px'}}>
            <span style={{position:'relative',width:'40px',height:'14px',background:'var(--surface)',borderRadius:'4px',overflow:'hidden'}}>
              <span style={{position:'absolute',top:0,bottom:0,left:0,width:'40%',background:'var(--ink)',opacity:0.2}}></span>
            </span>
            <span className="heritage" style={{fontSize:'12px'}}>la barre indique la position sur l'axe de la métrique — échelle commune par colonne</span>
          </span>
          <span style={{marginLeft:'auto',fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-400)',letterSpacing:'0.04em',textTransform:'uppercase'}}>
            clic ligne : ouvrir le profil · clic en-tête : trier
          </span>
        </div>
      </div>

      {/* === Agrégats comparatifs (sous le tableau, sans drill) === */}

      <div className="grid-2">
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Dispersion du CER</div>
            <div className="sec-aside">min · médiane · μ · max · sur 42 documents</div>
          </div>
          <div className="stack-sm">
            {ENGINES.map(e => {
              const max = 0.30;
              return (
                <div key={e.id} style={{
                  display:'grid',
                  gridTemplateColumns:'140px 1fr',
                  gap:'14px',
                  alignItems:'center',
                  padding:'10px 0',
                  borderBottom:'1px dotted var(--g-100)',
                }}>
                  <div style={{display:'flex',gap:'8px',alignItems:'center'}}>
                    <span className={`eng-id ${e.color}`}>{e.id}</span>
                    <span style={{fontSize:'12px',fontWeight:500}}>{e.name}</span>
                  </div>
                  <div style={{display:'flex',flexDirection:'column',gap:'4px'}}>
                    <div style={{position:'relative',height:'22px'}}>
                      <div style={{position:'absolute',top:'10px',left:0,right:0,height:'2px',background:'var(--g-50)'}}></div>
                      <div style={{
                        position:'absolute',top:'7px',
                        left:(e.cer_min/max*100)+'%',
                        width:((e.cer_max-e.cer_min)/max*100)+'%',
                        height:'8px',background:`var(--${e.color}-soft)`,borderRadius:'var(--r-pill)',
                      }}></div>
                      <div style={{
                        position:'absolute',top:'4px',
                        left:`calc(${e.cer_median/max*100}% - 1px)`,
                        width:'3px',height:'14px',background:`var(--${e.color}-deep)`,borderRadius:'2px',
                      }}></div>
                      <div style={{
                        position:'absolute',top:'2px',
                        left:`calc(${e.cer/max*100}% - 6px)`,
                        width:'12px',height:'18px',
                        border:`2px solid var(--${e.color})`,borderRadius:'50%',background:'var(--paper)',
                      }}></div>
                    </div>
                    <div style={{
                      display:'flex',justifyContent:'space-between',
                      fontFamily:'var(--mono)',fontVariantNumeric:'tabular-nums',
                      fontSize:'10.5px',color:'var(--g-500)',
                    }}>
                      <span>min {pct(e.cer_min)}</span>
                      <span>med {pct(e.cer_median)}</span>
                      <span style={{color:'var(--ink)'}}>μ {pct(e.cer)}</span>
                      <span>max {pct(e.cer_max)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Intervalles de confiance</div>
            <div className="sec-aside">bootstrap · 1000 itérations · 95 %</div>
          </div>
          <div className="stack-sm" style={{marginTop:'6px'}}>
            {ENGINES.map(e => {
              const lo = Math.max(0, e.cer - 0.014);
              const hi = e.cer + 0.014;
              const max = 0.10;
              return (
                <div key={e.id} style={{
                  display:'grid',
                  gridTemplateColumns:'auto 1fr 110px',
                  gap:'12px',
                  alignItems:'center',
                  padding:'10px 0',
                  borderBottom:'1px dotted var(--g-100)',
                }}>
                  <div style={{display:'flex',gap:'8px',alignItems:'center',minWidth:'180px'}}>
                    <span className={`eng-id ${e.color}`} style={{padding:'2px 8px',fontSize:'10px'}}>{e.id}</span>
                    <span style={{fontSize:'12px',fontWeight:500}}>{e.name}</span>
                  </div>
                  <div style={{position:'relative',height:'18px'}}>
                    <div style={{position:'absolute',top:'8px',left:0,right:0,height:'2px',background:'var(--g-50)'}}></div>
                    <div style={{
                      position:'absolute',top:'5px',
                      left: (lo/max*100)+'%',
                      width: ((hi-lo)/max*100)+'%',
                      height:'8px',background:`var(--${e.color}-soft)`,borderRadius:'var(--r-pill)',
                    }}></div>
                    <div style={{
                      position:'absolute',top:'3px',
                      left:`calc(${e.cer/max*100}% - 6px)`,
                      width:'12px',height:'12px',background:`var(--${e.color})`,borderRadius:'50%',border:'2px solid var(--paper)',
                    }}></div>
                  </div>
                  <span className="mono" style={{textAlign:'right',fontSize:'11px',color:'var(--g-500)',fontVariantNumeric:'tabular-nums'}}>
                    [{(lo*100).toFixed(1)}, {(hi*100).toFixed(1)}]
                  </span>
                </div>
              );
            })}
          </div>
          <div className="help" style={{marginTop:'12px',fontSize:'12px'}}>
            Les IC qui se chevauchent indiquent que la différence n'est pas séparable.
          </div>
        </div>
      </div>

      <div className="sec">
        <div className="sec-head">
          <div className="sec-title">CER moyen par strate</div>
          <div className="sec-aside">5 moteurs × 3 strates</div>
        </div>
        <table className="data">
          <thead className="metric-table">
            <tr className="cols">
              <th style={{width:'220px'}}>Moteur</th>
              {STRATA.map(s => (
                <th key={s.id} className="num-cell">
                  <span className="th-acro">{s.label}</span>
                  <span className="th-meta">n = {s.n}</span>
                </th>
              ))}
              <th className="num-cell" style={{borderLeft:'1px solid var(--g-50)'}}>
                <span className="th-acro">Toutes strates</span>
                <span className="th-meta">moyenne pondérée</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ENGINES.map((e, i) => (
              <tr key={e.id}>
                <td className="eng-cell">
                  <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
                    <span className={`eng-id ${e.color}`}>{e.id}</span>
                    <span style={{fontWeight:500,fontSize:'13px'}}>{e.name}</span>
                  </div>
                </td>
                {STRATA.map(s => (
                  <td key={s.id} className="num-cell">
                    <CellBar value={s.cers[i]} max={0.25} color={e.color} fmt={v=>pct(v)} />
                  </td>
                ))}
                <td className="num-cell" style={{borderLeft:'1px solid var(--g-50)'}}>
                  <CellBar value={e.cer} max={0.10} color={e.color} fmt={v=>pct(v)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </React.Fragment>
  );
}

/* ==================================================================== */
/* Drill-in : EngineDetail — full profile of one engine                 */
/* ==================================================================== */

function CalibrationLarge({ ece, color }) {
  const W = 360, H = 360, p = 30;
  const points = [];
  for (let i = 0; i <= 10; i++) {
    const conf = i / 10;
    const acc = conf - (Math.sin(conf * Math.PI) * ece * 1.4);
    points.push([p + conf * (W - 2*p), H - p - acc * (H - 2*p)]);
  }
  const path = points.map((pt, i) => (i === 0 ? 'M' : 'L') + pt.join(' ')).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',height:'auto',maxWidth:'380px'}}>
      <defs>
        <pattern id={`calgrid-${color}`} x="0" y="0" width="30" height="30" patternUnits="userSpaceOnUse">
          <circle cx="0.5" cy="0.5" r="0.5" fill="var(--g-200)" />
        </pattern>
      </defs>
      <rect x={p} y={p} width={W-2*p} height={H-2*p} fill={`url(#calgrid-${color})`} opacity="0.5" />
      <line x1={p} y1={H-p} x2={W-p} y2={H-p} stroke="var(--ink)" strokeWidth="1" />
      <line x1={p} y1={p} x2={p} y2={H-p} stroke="var(--ink)" strokeWidth="1" />
      <line x1={p} y1={H-p} x2={W-p} y2={p} stroke="var(--g-300)" strokeWidth="1" strokeDasharray="4 4" />
      <text x={W-p-4} y={p+18} textAnchor="end" fontFamily="var(--serif)" fontStyle="italic" fontSize="11" fill="var(--g-400)">
        calibration parfaite
      </text>
      <path d={path} fill="none" stroke={`var(--${color})`} strokeWidth="2.4" />
      {points.map((pt, i) => (
        <circle key={i} cx={pt[0]} cy={pt[1]} r="4" fill={`var(--${color})`} stroke="var(--paper)" strokeWidth="1.5" />
      ))}
      {[0, 0.25, 0.5, 0.75, 1.0].map(v => (
        <g key={v}>
          <text x={p + v*(W-2*p)} y={H-p+18} textAnchor="middle" fontFamily="var(--mono)" fontSize="10" fill="var(--g-500)">{v.toFixed(2)}</text>
          <text x={p-8} y={H-p - v*(H-2*p) + 3} textAnchor="end" fontFamily="var(--mono)" fontSize="10" fill="var(--g-500)">{v.toFixed(2)}</text>
        </g>
      ))}
      <text x={W/2} y={H-6} textAnchor="middle" fontFamily="var(--mono)" fontSize="10" fill="var(--g-400)" letterSpacing="0.08em">
        CONFIANCE PRÉDITE →
      </text>
      <text x={14} y={H/2} transform={`rotate(-90, 14, ${H/2})`} textAnchor="middle"
            fontFamily="var(--mono)" fontSize="10" fill="var(--g-400)" letterSpacing="0.08em">
        EXACTITUDE OBSERVÉE
      </text>
    </svg>
  );
}

function PerDocBars({ engineIdx, color }) {
  const sorted = DOCUMENTS.map(d => ({ id: d.id, label: d.label, cer: d.cers[engineIdx] }))
                          .sort((a, b) => a.cer - b.cer);
  const max = Math.max(...sorted.map(d => d.cer));
  return (
    <svg viewBox={`0 0 ${DOCUMENTS.length * 22 + 60} 130`} style={{width:'100%',height:'auto'}}>
      <line x1="30" y1="100" x2={DOCUMENTS.length * 22 + 30} y2="100" stroke="var(--ink)" strokeWidth="1" />
      {sorted.map((d, i) => (
        <g key={d.id}>
          <rect x={30 + i*22 + 2} y={100 - (d.cer/max)*80}
                width="16" height={(d.cer/max)*80}
                fill={`var(--${color})`} fillOpacity="0.75" rx="2" />
          <title>{d.label} · {pct(d.cer)}</title>
        </g>
      ))}
      {[0, max/2, max].map(v => (
        <text key={v} x="24" y={100 - (v/max)*80 + 3} textAnchor="end"
              fontFamily="var(--mono)" fontSize="9" fill="var(--g-500)">{pct(v, 1)}</text>
      ))}
      <text x={(DOCUMENTS.length * 22 + 60)/2} y="125" textAnchor="middle"
            fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-400)" letterSpacing="0.06em">
        DOCUMENTS · TRIÉS PAR CER CROISSANT (n = {DOCUMENTS.length})
      </text>
    </svg>
  );
}

function EngineDetail({ engine, idx, onBack, onPrev, onNext }) {
  const segs = [
    { c:'fern',   v:32, k:'Ligature' },
    { c:'slate',  v:22, k:'Diacritique' },
    { c:'clay',   v:18, k:'Substitution' },
    { c:'butter', v:14, k:'Espacement' },
    { c:'ink',    v: 8, k:'Autre' },
  ];
  const r = parseInt(engine.id, 36) % 5;
  segs[r].v += 6; segs[(r+1)%5].v -= 4;
  const total = segs.reduce((a, b) => a + b.v, 0);

  const docByCer = DOCUMENTS.map((d, i) => ({...d, cer: d.cers[idx], origIdx: i}))
                            .sort((a, b) => a.cer - b.cer);
  const bestDocs = docByCer.slice(0, 5);
  const worstDocs = docByCer.slice(-5).reverse();

  return (
    <React.Fragment>

      {/* Hero with back + identity + nav */}
      <div className="view-hero">
        <div style={{display:'flex',flexDirection:'column',gap:'4px',maxWidth:'70%'}}>
          <button className="drill-back" onClick={onBack} style={{alignSelf:'flex-start'}}>
            <span className="arrow">←</span> retour au tableau
          </button>
          <div className="view-hero-eyebrow" style={{marginTop:'8px'}}>
            moteur #{String(idx+1).padStart(2,'0')} sur {ENGINES.length} · {engine.kind.toLowerCase()}
          </div>
          <div style={{display:'flex',alignItems:'center',gap:'14px',marginTop:'2px'}}>
            <span className={`eng-id ${engine.color}`} style={{padding:'4px 12px',fontSize:'13px'}}>{engine.id}</span>
            <div className="view-hero-name" style={{fontSize:'34px'}}>{engine.name}</div>
          </div>
          <div className="view-hero-desc">
            Chaîne · <span style={{fontFamily:'var(--mono)',color:'var(--ink)',fontSize:'13px'}}>{engine.chain.join(' → ')}</span> ·
            exécuté sur {engine.docs} documents.
          </div>
        </div>
        <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
          <button className="btn btn-sm" onClick={onPrev}>← Précédent</button>
          <span style={{fontFamily:'var(--mono)',fontSize:'11px',color:'var(--g-400)'}}>{idx+1} / {ENGINES.length}</span>
          <button className="btn btn-sm btn-primary" onClick={onNext}>Suivant →</button>
        </div>
      </div>

      {/* Key readouts row */}
      <div className="grid-4">
        <div className="readout">
          <div className="r-label">CER · μ</div>
          <div className="r-value">{(engine.cer*100).toFixed(1)}<span className="r-unit">%</span></div>
          <div className="r-delta">médiane {pct(engine.cer_median)} · étendue {pct(engine.cer_min)} → {pct(engine.cer_max)}</div>
        </div>
        <div className="readout">
          <div className="r-label">WER</div>
          <div className="r-value">{(engine.wer*100).toFixed(1)}<span className="r-unit">%</span></div>
          <div className="r-delta">MER {pct(engine.mer)} · WIL {pct(engine.wil)}</div>
        </div>
        <div className="readout">
          <div className="r-label">ECE</div>
          <div className="r-value">{(engine.ece*100).toFixed(1)}<span className="r-unit">%</span></div>
          <div className="r-delta">calibration de la confiance</div>
        </div>
        <div className="readout">
          <div className="r-label">€ / 1000 p</div>
          <div className="r-value">{engine.cost.toFixed(2)}<span className="r-unit">€</span></div>
          <div className="r-delta">{engine.speed.toFixed(1)} s/page</div>
        </div>
      </div>

      {/* Per-doc CER bars */}
      <div className="sec">
        <div className="sec-head">
          <div className="sec-title">CER par document</div>
          <div className="sec-aside">{DOCUMENTS.length} documents · triés par CER croissant</div>
        </div>
        <div className="surface-flat" style={{padding:'18px 14px'}}>
          <PerDocBars engineIdx={idx} color={engine.color} />
        </div>
      </div>

      {/* Two-column : calibration + error composition */}
      <div className="grid-2" style={{gridTemplateColumns:'1fr 1fr',alignItems:'stretch'}}>
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Courbe de calibration</div>
            <div className="sec-aside">ECE {(engine.ece*100).toFixed(1)} %</div>
          </div>
          <div style={{display:'flex',justifyContent:'center',padding:'10px'}}>
            <CalibrationLarge ece={engine.ece} color={engine.color} />
          </div>
          <div className="help" style={{marginTop:'12px'}}>
            La courbe trace l'exactitude observée en fonction de la confiance prédite par le moteur.
            Plus elle colle à la diagonale, plus la confiance est honnête.
          </div>
        </div>

        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Composition des erreurs</div>
            <div className="sec-aside">{Math.round(total*4)} erreurs réparties en 5 classes</div>
          </div>
          <div style={{display:'flex',height:'22px',borderRadius:'var(--r-pill)',overflow:'hidden',marginBottom:'18px'}}>
            {segs.map(s => (
              <div key={s.k} style={{flex: s.v, background:`var(--${s.c})`}} title={`${s.k} · ${s.v}%`} />
            ))}
          </div>
          <div className="stack-sm">
            {segs.map(s => (
              <div key={s.k} className="bar-row">
                <span className="b-label" style={{display:'flex',gap:'8px',alignItems:'center'}}>
                  <span style={{width:'10px',height:'10px',borderRadius:'2px',background:`var(--${s.c})`}}></span>
                  {s.k}
                </span>
                <div className="b-track">
                  <div className="b-fill" style={{width:(s.v/Math.max(...segs.map(x=>x.v))*100)+'%',background:`var(--${s.c})`}}></div>
                </div>
                <span className="b-value">{s.v} %</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Per-stratum focus + IC for this engine */}
      <div className="grid-2">
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Performance par strate</div>
            <div className="sec-aside">CER moyen · 3 strates</div>
          </div>
          <div className="stack-sm">
            {STRATA.map(s => (
              <div key={s.id} style={{
                display:'grid',
                gridTemplateColumns:'1fr auto',
                gap:'14px',
                alignItems:'center',
                padding:'14px 0',
                borderBottom:'1px dotted var(--g-100)',
              }}>
                <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
                  <div style={{display:'flex',gap:'10px',alignItems:'baseline'}}>
                    <span style={{
                      fontFamily:'var(--display)',
                      fontVariationSettings:'"opsz" 32, "wght" 600',
                      fontSize:'17px',letterSpacing:'-0.02em',
                    }}>{s.label}</span>
                    <span className="tag tag-mono">n = {s.n}</span>
                  </div>
                  <div className="b-track" style={{height:'8px'}}>
                    <div className="b-fill" style={{
                      width: (s.cers[idx]/0.25*100)+'%',
                      background:`var(--${engine.color})`,
                    }}></div>
                  </div>
                </div>
                <span className="num" style={{
                  fontFamily:'var(--display)',
                  fontVariationSettings:'"opsz" 96, "wght" 600',
                  fontSize:'24px',letterSpacing:'-0.025em',
                  color:`var(--${engine.color}-deep)`,
                }}>{pct(s.cers[idx])}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Stabilité statistique</div>
            <div className="sec-aside">bootstrap · 1000 itérations</div>
          </div>
          <div className="stack" style={{padding:'14px 0'}}>
            <div>
              <div className="label" style={{marginBottom:'8px'}}>Intervalle de confiance · CER · 95 %</div>
              <div style={{position:'relative',height:'32px'}}>
                {(() => {
                  const lo = Math.max(0, engine.cer - 0.014);
                  const hi = engine.cer + 0.014;
                  const max = 0.10;
                  return (
                    <React.Fragment>
                      <div style={{position:'absolute',top:'15px',left:0,right:0,height:'2px',background:'var(--g-50)'}}></div>
                      <div style={{
                        position:'absolute',top:'11px',
                        left:(lo/max*100)+'%',
                        width:((hi-lo)/max*100)+'%',
                        height:'10px',background:`var(--${engine.color}-soft)`,borderRadius:'var(--r-pill)',
                      }}></div>
                      <div style={{
                        position:'absolute',top:'7px',
                        left:`calc(${engine.cer/max*100}% - 9px)`,
                        width:'18px',height:'18px',background:`var(--${engine.color})`,
                        borderRadius:'50%',border:'3px solid var(--paper)',
                      }}></div>
                      <div style={{position:'absolute',bottom:0,left:0,right:0,display:'flex',justifyContent:'space-between',fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-500)',fontVariantNumeric:'tabular-nums'}}>
                        <span>0 %</span>
                        <span style={{color:'var(--ink)'}}>μ {pct(engine.cer)}</span>
                        <span>{pct(max)}</span>
                      </div>
                    </React.Fragment>
                  );
                })()}
              </div>
            </div>
            <div className="hr"></div>
            <div className="grid-2">
              <div>
                <div className="label">Gini · inégalité</div>
                <div style={{fontFamily:'var(--display)',fontVariationSettings:'"opsz" 96, "wght" 600',fontSize:'26px',letterSpacing:'-0.025em',marginTop:'4px'}}>
                  {engine.gini.toFixed(3)}
                </div>
                <div className="heritage" style={{fontSize:'12px',marginTop:'2px'}}>
                  {engine.gini < 0.3 ? 'erreurs réparties' : engine.gini < 0.4 ? 'concentration modérée' : 'erreurs concentrées'} sur le corpus
                </div>
              </div>
              <div>
                <div className="label">Ancrage trigrammes</div>
                <div style={{fontFamily:'var(--display)',fontVariationSettings:'"opsz" 96, "wght" 600',fontSize:'26px',letterSpacing:'-0.025em',marginTop:'4px'}}>
                  {engine.anchor.toFixed(3)}
                </div>
                <div className="heritage" style={{fontSize:'12px',marginTop:'2px'}}>
                  {engine.anchor > 0.92 ? 'sortie ancrée dans l\u2019image' : engine.anchor > 0.85 ? 'ancrage moyen' : 'hallucination probable'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top / Bottom docs */}
      <div className="grid-2">
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Documents les mieux reconnus</div>
            <div className="sec-aside">5 plus faibles CER</div>
          </div>
          <div className="stack-sm">
            {bestDocs.map(d => (
              <div key={d.id} style={{
                display:'grid',
                gridTemplateColumns:'1fr auto',
                gap:'10px',
                padding:'9px 0',
                borderBottom:'1px dotted var(--g-100)',
                alignItems:'center',
              }}>
                <div>
                  <div style={{fontSize:'12.5px',fontWeight:500}}>{d.label}</div>
                  <div style={{fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-400)'}}>{d.id} · {d.strata}</div>
                </div>
                <span className="num" style={{fontFamily:'var(--mono)',fontSize:'12.5px',color:`var(--${engine.color}-deep)`,fontWeight:500}}>
                  {pct(d.cer)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Documents les plus difficiles</div>
            <div className="sec-aside">5 plus hauts CER</div>
          </div>
          <div className="stack-sm">
            {worstDocs.map(d => (
              <div key={d.id} style={{
                display:'grid',
                gridTemplateColumns:'1fr auto',
                gap:'10px',
                padding:'9px 0',
                borderBottom:'1px dotted var(--g-100)',
                alignItems:'center',
              }}>
                <div>
                  <div style={{fontSize:'12.5px',fontWeight:500}}>{d.label}</div>
                  <div style={{fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-400)'}}>{d.id} · {d.strata}</div>
                </div>
                <span className="num" style={{fontFamily:'var(--mono)',fontSize:'12.5px',color:`var(--${engine.color}-deep)`,fontWeight:500}}>
                  {pct(d.cer)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

    </React.Fragment>
  );
}

/* ==================================================================== */
/* Main view shell                                                       */
/* ==================================================================== */

function ViewByEngine({ initialSelected }) {
  const [selected, setSelected] = React.useState(
    typeof initialSelected === 'number' ? initialSelected : null
  );

  return (
    <div className="report-board"
         data-screen-label={selected === null ? '02 Par moteur · tableau' : '02 Par moteur · détail'}>
      <ReportChrome active="engines" />
      <div className="report-main">

        {selected === null && (
          <React.Fragment>
            <HeroBand
              eyebrow="vue 02 · par moteur"
              title="Par moteur"
              desc="Tableau d'aperçu des 5 moteurs sur 14 métriques, suivi d'agrégats comparatifs. Cliquer une ligne pour ouvrir le profil complet d'un moteur."
              stats={[
                { v: '5',  k: 'moteurs',     u: '' },
                { v: '14', k: 'métriques',   u: '' },
                { v: '42', k: 'documents/moteur', u: '' },
              ]}
            />
            <EngineOverview onSelect={(i) => setSelected(i)} />
          </React.Fragment>
        )}

        {selected !== null && (
          <EngineDetail
            engine={ENGINES[selected]}
            idx={selected}
            onBack={() => setSelected(null)}
            onPrev={() => setSelected((selected - 1 + ENGINES.length) % ENGINES.length)}
            onNext={() => setSelected((selected + 1) % ENGINES.length)}
          />
        )}

      </div>
    </div>
  );
}

/* Wrappers for canvas */
function ViewByEngineDrilled() { return <ViewByEngine initialSelected={2} />; }

Object.assign(window, { ViewByEngine, ViewByEngineDrilled });
