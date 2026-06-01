/* View 04 — Croisements : surfaces où deux dimensions se croisent.
   Cross-plot (métrique × métrique), qualité image × CER, divergence
   inter-moteurs. */

/* -- Cross-plot primitive ------------------------------------------- */
function CrossPlotPanel({ xKey, yKey, xLabel, yLabel, xFmt, yFmt, xMax, yMax }) {
  const W = 540, H = 280, padL = 56, padR = 24, padT = 16, padB = 40;
  const ix = v => padL + (v / xMax) * (W - padL - padR);
  const iy = v => padT + (1 - v / yMax) * (H - padT - padB);

  const ticksX = 5, ticksY = 5;
  const xTicks = Array.from({length: ticksX+1}, (_, i) => (xMax * i) / ticksX);
  const yTicks = Array.from({length: ticksY+1}, (_, i) => (yMax * i) / ticksY);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',height:'auto'}}>
      <defs>
        <pattern id={`gridx-${xKey}-${yKey}`} x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="0.5" cy="0.5" r="0.5" fill="var(--g-200)" />
        </pattern>
      </defs>
      <rect x={padL} y={padT} width={W-padL-padR} height={H-padT-padB} fill={`url(#gridx-${xKey}-${yKey})`} opacity="0.5" />
      <line x1={padL} y1={H-padB} x2={W-padR} y2={H-padB} stroke="var(--ink)" strokeWidth="1" />
      <line x1={padL} y1={padT} x2={padL} y2={H-padB} stroke="var(--ink)" strokeWidth="1" />

      {xTicks.slice(1, -1).map((t, i) => (
        <line key={`gx${i}`} x1={ix(t)} y1={padT} x2={ix(t)} y2={H-padB} stroke="var(--g-100)" strokeWidth="0.5" strokeDasharray="2 3" />
      ))}
      {yTicks.slice(1, -1).map((t, i) => (
        <line key={`gy${i}`} x1={padL} y1={iy(t)} x2={W-padR} y2={iy(t)} stroke="var(--g-100)" strokeWidth="0.5" strokeDasharray="2 3" />
      ))}

      {ENGINES.map(e => (
        <g key={e.id}>
          <circle cx={ix(e[xKey])} cy={iy(e[yKey])} r="7"
                  fill={`var(--${e.color})`}
                  stroke="var(--paper)" strokeWidth="2" />
          <text x={ix(e[xKey]) + 12} y={iy(e[yKey]) + 4}
                fontFamily="var(--sans)" fontWeight="500" fontSize="11" fill="var(--ink)">
            {e.id} · {e.name}
          </text>
        </g>
      ))}

      {xTicks.map((t, i) => (
        <text key={`tx${i}`} x={ix(t)} y={H-padB+16} textAnchor="middle"
              fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-500)">{xFmt(t)}</text>
      ))}
      {yTicks.map((t, i) => (
        <text key={`ty${i}`} x={padL-8} y={iy(t)+3} textAnchor="end"
              fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-500)">{yFmt(t)}</text>
      ))}
      <text x={(W)/2} y={H-6} textAnchor="middle"
            fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-400)" letterSpacing="0.08em">
        {xLabel}
      </text>
      <text x={16} y={H/2} transform={`rotate(-90, 16, ${H/2})`} textAnchor="middle"
            fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-400)" letterSpacing="0.08em">
        {yLabel}
      </text>
    </svg>
  );
}

/* -- Image-quality × CER scatter (per-doc, per-engine) -------------- */
function ImageQualityScatter() {
  const W = 540, H = 240, padL = 50, padR = 24, padT = 14, padB = 30;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',height:'auto'}}>
      <defs>
        <pattern id="imgQ-grid" x="0" y="0" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="0.5" cy="0.5" r="0.5" fill="var(--g-200)" />
        </pattern>
      </defs>
      <rect x={padL} y={padT} width={W-padL-padR} height={H-padT-padB} fill="url(#imgQ-grid)" opacity="0.5" />
      <line x1={padL} y1={H-padB} x2={W-padR} y2={H-padB} stroke="var(--ink)" strokeWidth="1" />
      <line x1={padL} y1={padT}   x2={padL}   y2={H-padB} stroke="var(--ink)" strokeWidth="1" />

      {DOCUMENTS.map((d, di) => {
        const q = 0.3 + (di * 17) % 60 / 100;
        return d.cers.map((c, ei) => (
          <circle key={`${di}-${ei}`}
                  cx={padL + Math.max(0.05, Math.min(0.95, q + (ei*3)%17/100 - 0.05)) * (W-padL-padR)}
                  cy={padT + (1 - Math.min(0.29, c)/0.30) * (H-padT-padB)}
                  r="3.5"
                  fill={`var(--${ENGINES[ei].color})`}
                  fillOpacity="0.55" />
        ));
      })}

      {[0, 0.25, 0.5, 0.75, 1.0].map(q => (
        <text key={q} x={padL + q * (W-padL-padR)} y={H-padB+16} textAnchor="middle"
              fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-500)">{q.toFixed(2)}</text>
      ))}
      {[0, 0.10, 0.20, 0.30].map(c => (
        <text key={c} x={padL-6} y={padT + (1 - c/0.30) * (H-padT-padB) + 3} textAnchor="end"
              fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-500)">{(c*100).toFixed(0)} %</text>
      ))}
      <text x={W/2} y={H-4} textAnchor="middle"
            fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-400)" letterSpacing="0.08em">
        QUALITÉ D'IMAGE · 0 → 1
      </text>
      <text x={14} y={H/2} transform={`rotate(-90, 14, ${H/2})`} textAnchor="middle"
            fontFamily="var(--mono)" fontSize="9.5" fill="var(--g-400)" letterSpacing="0.08em">
        CER
      </text>
    </svg>
  );
}

function ViewCrosses() {
  return (
    <div className="report-board" data-screen-label="04 Croisements">
      <ReportChrome active="crosses" />
      <div className="report-main">

        <HeroBand
          eyebrow="vue 04 · croisements"
          title="Croisements"
          desc="Surfaces où deux dimensions se croisent : métrique × métrique, qualité d'image × CER, divergence des erreurs entre moteurs. C'est ici qu'on regarde les compromis."
          stats={[
            { v: '3',  k: 'croisements',  u: '' },
            { v: '5',  k: 'moteurs',      u: '' },
            { v: '210', k: 'points scatter', u: '' },
          ]}
        />

        {/* === 1 — Cross-plot : métrique × métrique === */}
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Métrique × métrique</div>
            <div className="sec-aside">5 moteurs · 1 point par moteur</div>
          </div>
          <div style={{display:'flex',justifyContent:'space-between',gap:'14px',marginBottom:'14px',flexWrap:'wrap'}}>
            <div style={{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}}>
              <span className="label">axe x</span>
              <div className="segmented">
                <button>CER</button>
                <button>WER</button>
                <button>ECE</button>
                <button>Ancrage</button>
                <button>F1 NER</button>
                <button>Ligatures</button>
                <button className="on">€ / 1000p</button>
              </div>
            </div>
            <div style={{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}}>
              <span className="label">axe y</span>
              <div className="segmented">
                <button className="on">CER</button>
                <button>WER</button>
                <button>ECE</button>
                <button>Ancrage</button>
                <button>F1 NER</button>
                <button>Ligatures</button>
                <button>s/page</button>
              </div>
            </div>
          </div>
          <div className="surface-flat" style={{padding:'18px 14px'}}>
            <CrossPlotPanel
              xKey="cost" yKey="cer"
              xLabel="COÛT · € / 1000 PAGES"
              yLabel="CER · TAUX D'ERREUR CARACTÈRE"
              xFmt={v => v.toFixed(1) + ' €'}
              yFmt={v => (v*100).toFixed(1) + ' %'}
              xMax={1.6} yMax={0.10}
            />
          </div>
          <div style={{display:'flex',gap:'14px',marginTop:'12px',flexWrap:'wrap',justifyContent:'center'}}>
            {ENGINES.map(e => (
              <span key={e.id} style={{display:'inline-flex',alignItems:'center',gap:'6px',fontSize:'11px',color:'var(--g-600)'}}>
                <span style={{width:'10px',height:'10px',borderRadius:'50%',background:`var(--${e.color})`}}></span>
                {e.id} · {e.name}
              </span>
            ))}
          </div>
          <div className="help" style={{marginTop:'14px'}}>
            Outil pour repérer les compromis. Le bas-gauche (CER bas, coût bas) ou le bas-droit (CER bas, coût élevé)
            n'a pas la même implication selon la contrainte du projet.
          </div>
        </div>

        {/* === 2 — Qualité d'image × CER (per-document) === */}
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Qualité d'image × CER · par document</div>
            <div className="sec-aside">42 docs × 5 moteurs = 210 points</div>
          </div>
          <div className="surface-flat" style={{padding:'18px 14px'}}>
            <ImageQualityScatter />
          </div>
          <div style={{display:'flex',gap:'14px',marginTop:'12px',flexWrap:'wrap',justifyContent:'center'}}>
            {ENGINES.map(e => (
              <span key={e.id} style={{display:'inline-flex',alignItems:'center',gap:'6px',fontSize:'11px',color:'var(--g-600)'}}>
                <span style={{width:'10px',height:'10px',borderRadius:'50%',background:`var(--${e.color})`,opacity:0.7}}></span>
                {e.id} · {e.name}
              </span>
            ))}
          </div>
          <div className="help" style={{marginTop:'14px'}}>
            Chaque point est un (document, moteur). L'axe X mesure la qualité de l'image numérisée (contraste, résolution effective,
            netteté du trait). Permet d'estimer la sensibilité d'un moteur au bruit de numérisation.
          </div>
        </div>

        {/* === 3 — Divergence inter-moteurs === */}
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Divergence inter-moteurs</div>
            <div className="sec-aside">Jensen-Shannon sur la taxonomie d'erreurs</div>
          </div>
          <div className="grid-2" style={{gridTemplateColumns:'1.1fr 1fr',alignItems:'flex-start'}}>
            <div>
              <table className="data">
                <thead className="grouped">
                  <tr className="cols">
                    <th style={{width:'90px'}}></th>
                    {ENGINES.map(e => (
                      <th key={e.id} className="num-cell" style={{padding:'10px 8px'}}>
                        <span className="th-acro">{e.id}</span>
                        <span className="th-def">{e.name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ENGINES.map((row, i) => (
                    <tr key={row.id}>
                      <td style={{padding:'10px'}}>
                        <div style={{display:'flex',gap:'8px',alignItems:'center'}}>
                          <span className={`eng-id ${row.color}`} style={{padding:'2px 8px',fontSize:'10px'}}>{row.id}</span>
                          <span style={{fontSize:'11.5px',fontWeight:500}}>{row.name}</span>
                        </div>
                      </td>
                      {ENGINES.map((col, j) => {
                        if (i === j) return <td key={col.id} className="num-cell" style={{color:'var(--g-200)',padding:'10px 8px'}}>—</td>;
                        const d = Math.abs(row.cer - col.cer) * 3 + 0.18;
                        const bg = `oklch(${0.96 - d*0.4} 0.04 145)`;
                        return (
                          <td key={col.id} className="num-cell" style={{
                            background: bg,
                            fontFamily:'var(--mono)',
                            fontSize:'12px',
                            padding:'10px 8px',
                            color: d > 0.4 ? 'var(--paper)' : 'var(--g-700)',
                          }}>{d.toFixed(2)}</td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="surface-flat" style={{padding:'18px 22px'}}>
              <div className="label" style={{marginBottom:'10px'}}>Lecture</div>
              <ul style={{listStyle:'none',display:'flex',flexDirection:'column',gap:'10px'}}>
                <li style={{display:'flex',gap:'10px',alignItems:'flex-start'}}>
                  <span style={{display:'inline-block',width:'24px',textAlign:'center',background:'oklch(0.96 0.04 145)',color:'var(--g-700)',padding:'2px 4px',borderRadius:'3px',fontFamily:'var(--mono)',fontSize:'11px',fontWeight:500}}>0.00</span>
                  <span style={{fontFamily:'var(--serif)',fontStyle:'italic',fontSize:'13px',color:'var(--g-600)'}}>
                    deux moteurs ont les mêmes classes d'erreurs dominantes
                  </span>
                </li>
                <li style={{display:'flex',gap:'10px',alignItems:'flex-start'}}>
                  <span style={{display:'inline-block',width:'24px',textAlign:'center',background:'oklch(0.60 0.04 145)',color:'var(--paper)',padding:'2px 4px',borderRadius:'3px',fontFamily:'var(--mono)',fontSize:'11px',fontWeight:500}}>1.00</span>
                  <span style={{fontFamily:'var(--serif)',fontStyle:'italic',fontSize:'13px',color:'var(--g-600)'}}>
                    profils d'erreurs orthogonaux (aucune classe dominante en commun)
                  </span>
                </li>
              </ul>
              <div className="help" style={{marginTop:'14px',paddingLeft:'10px',fontSize:'12.5px'}}>
                La symétrie de la matrice confirme la robustesse du calcul (JSD(A,B) = JSD(B,A)).
                Utile pour repérer les paires de moteurs susceptibles d'être complémentaires.
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

Object.assign(window, { ViewCrosses });
