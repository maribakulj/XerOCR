/* View 01 — Vue d'ensemble : corpus, moteurs, paramètres. Aucune
   évaluation, aucune comparaison. Le chercheur ouvre ici pour
   comprendre ce qui a été calculé, puis navigue. */

function ViewOverview() {
  return (
    <div className="report-board" data-screen-label="01 Vue d'ensemble">
      <ReportChrome active="overview" />
      <div className="report-main">

        <HeroBand
          eyebrow="vue 01 · vue d'ensemble"
          title="Vue d'ensemble du run"
          desc="Métadonnées du benchmark, composition du corpus, moteurs exécutés et paramètres de normalisation. Aucune analyse ici — les métriques sont dans les vues suivantes."
          stats={[
            { v: '42', k: 'documents', u: '' },
            { v: '5',  k: 'moteurs',   u: '' },
            { v: '3',  k: 'strates',   u: '' },
          ]}
        />

        {/* Row : run identity + corpus composition */}
        <div className="grid-2" style={{gridTemplateColumns:'1fr 1.2fr'}}>
          <div className="sec">
            <div className="sec-head">
              <div className="sec-title">Identité du run</div>
              <div className="sec-aside">snapshot embarqué</div>
            </div>
            <div className="stack-sm">
              {[
                ['nom du corpus',           'gallica_presse_xix_42'],
                ['date d\u2019exécution',   '2026-05-21 · 14:32 UTC'],
                ['picarones',               'v2.0.4 · sha 7f3a1c2'],
                ['python',                  '3.11.8 · linux-x86_64'],
                ['profil normalisation',    'diplomatic_modern_fr'],
                ['glossaire',               'fr · 184 entrées'],
                ['pricing table',           '2026-03-12 · 6 sources'],
                ['seed corpus',             '8192'],
                ['vues calculées',          'text_final · alto_doc · search'],
                ['durée totale',            '24 min 18 s'],
              ].map(([k, v]) => (
                <div key={k} style={{
                  display:'flex',
                  justifyContent:'space-between',
                  padding:'9px 0',
                  borderBottom:'1px dotted var(--g-100)',
                  fontSize:'12.5px',
                }}>
                  <span style={{color:'var(--g-400)',letterSpacing:'0.02em'}}>{k}</span>
                  <span style={{fontFamily:'var(--mono)',color:'var(--ink)',fontSize:'11.5px'}}>{v}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="sec">
            <div className="sec-head">
              <div className="sec-title">Composition du corpus</div>
              <div className="sec-aside">3 strates · n = 42</div>
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
                  <div style={{display:'flex',flexDirection:'column',gap:'6px'}}>
                    <div style={{display:'flex',gap:'10px',alignItems:'baseline'}}>
                      <span style={{
                        fontFamily:'var(--display)',
                        fontVariationSettings:'"opsz" 32, "wght" 600',
                        fontSize:'18px',
                        letterSpacing:'-0.02em',
                      }}>{s.label}</span>
                      <span className="tag tag-mono">n = {s.n}</span>
                    </div>
                    <div className="b-track" style={{height:'8px',width:'100%'}}>
                      <div className="b-fill" style={{
                        width: (s.n/42*100)+'%',
                        background: 'var(--ink)',
                      }}></div>
                    </div>
                  </div>
                  <span className="num" style={{
                    fontFamily:'var(--display)',
                    fontVariationSettings:'"opsz" 96, "wght" 600',
                    fontSize:'28px',
                    letterSpacing:'-0.025em',
                    color:'var(--ink)',
                  }}>{Math.round(s.n/42*100)}<span style={{fontSize:'14px',color:'var(--g-300)'}}>%</span></span>
                </div>
              ))}
            </div>
            <div className="help" style={{marginTop:'14px'}}>
              Strates issues du champ <code style={{fontFamily:'var(--mono)',fontSize:'12px'}}>script_type</code> du
              corpus Picarones. La répartition est figée à la création du run.
            </div>
          </div>
        </div>

        {/* Engines roster — listed in execution order, no ranking */}
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Moteurs exécutés</div>
            <div className="sec-aside">5 moteurs · ordre de configuration</div>
          </div>
          <div className="stack-sm">
            {ENGINES.map(e => (
              <div key={e.id} style={{
                display:'grid',
                gridTemplateColumns:'auto auto 1fr auto auto',
                gap:'18px',
                alignItems:'center',
                padding:'16px 18px',
                background:'var(--surface)',
                borderRadius:'var(--r-md)',
              }}>
                <span className={`eng-id ${e.color}`}>{e.id}</span>
                <div style={{display:'flex',flexDirection:'column',gap:'2px',minWidth:'180px'}}>
                  <span style={{fontWeight:500,fontSize:'14px'}}>{e.name}</span>
                  <span className="tag tag-mono" style={{alignSelf:'flex-start',background:'var(--g-50)'}}>{e.kind}</span>
                </div>
                <div style={{
                  fontFamily:'var(--mono)',
                  fontSize:'11.5px',
                  color:'var(--g-500)',
                  display:'flex',
                  alignItems:'center',
                  gap:'6px',
                  flexWrap:'wrap',
                }}>
                  {e.chain.map((c, i) => (
                    <React.Fragment key={i}>
                      <span style={{
                        background:'var(--raised-2)',
                        padding:'3px 8px',
                        borderRadius:'var(--r-pill)',
                      }}>{c}</span>
                      {i < e.chain.length-1 && <span style={{color:'var(--g-300)'}}>→</span>}
                    </React.Fragment>
                  ))}
                </div>
                <div style={{display:'flex',gap:'18px',fontFamily:'var(--mono)',fontSize:'11px',color:'var(--g-500)'}}>
                  <span><span style={{color:'var(--g-300)',letterSpacing:'0.06em',textTransform:'uppercase',marginRight:'4px'}}>tarif</span>{e.cost.toFixed(2)} €</span>
                  <span><span style={{color:'var(--g-300)',letterSpacing:'0.06em',textTransform:'uppercase',marginRight:'4px'}}>vitesse</span>{e.speed.toFixed(1)} s/p</span>
                  <span><span style={{color:'var(--g-300)',letterSpacing:'0.06em',textTransform:'uppercase',marginRight:'4px'}}>docs</span>{e.docs}</span>
                </div>
                <div style={{display:'flex',alignItems:'center',gap:'6px'}}>
                  <span className="dot on"></span>
                  <span style={{fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-500)',letterSpacing:'0.04em',textTransform:'uppercase'}}>terminé</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Methodology — what is calculated, what is not */}
        <div className="grid-2" style={{gridTemplateColumns:'1.3fr 1fr'}}>
          <div className="sec">
            <div className="sec-head">
              <div className="sec-title">Métriques calculées</div>
              <div className="sec-aside">14 métriques · 5 familles</div>
            </div>
            <div className="grid-2">
              {[
                { fam:'Caractère',     items:['CER exact', 'CER diplo.', 'CER médian / min / max', 'Gini'] },
                { fam:'Mot',           items:['WER', 'MER', 'WIL'] },
                { fam:'Philologique',  items:['Ligatures', 'Diacritiques', 'MUFI overlap', 'Sur-normalisation'] },
                { fam:'Fiabilité',     items:['Score d\u2019ancrage', 'ECE · MCE', 'Bootstrap CI 95 %'] },
                { fam:'Aval',          items:['F1 entités nommées', 'Recherchabilité fuzzy', 'Lisibilité Flesch'] },
                { fam:'Économique',    items:['€ / 1000 pages', 'Vitesse · s/page', 'CO₂ estimé'] },
              ].map(g => (
                <div key={g.fam} style={{
                  background:'var(--surface)',
                  borderRadius:'var(--r-md)',
                  padding:'14px 16px',
                  display:'flex',
                  flexDirection:'column',
                  gap:'8px',
                }}>
                  <div className="label">{g.fam}</div>
                  <ul style={{listStyle:'none',display:'flex',flexDirection:'column',gap:'4px'}}>
                    {g.items.map(it => (
                      <li key={it} style={{
                        fontFamily:'var(--mono)',
                        fontSize:'11.5px',
                        color:'var(--g-600)',
                        display:'flex',
                        alignItems:'center',
                        gap:'6px',
                      }}>
                        <span style={{color:'var(--g-300)'}}>·</span>{it}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          <div className="sec">
            <div className="sec-head">
              <div className="sec-title">Navigation du rapport</div>
              <div className="sec-aside">5 vues · données brutes</div>
            </div>
            <div className="stack-sm">
              {[
                ['Par moteur',     'Tableau des métriques, dispersion, stabilité (IC + strates), diagnostics (calibration + composition d\u2019erreurs).', '02'],
                ['Par document',   'Galerie des 42 documents — cliquer une vignette ouvre le fac-similé, le diff par moteur et les signaux de difficulté.', '03'],
                ['Croisements',    'Métrique × métrique, qualité d\u2019image × CER, divergence inter-moteurs.', '04'],
              ].map(([t, d, n]) => (
                <div key={t} style={{
                  display:'grid',
                  gridTemplateColumns:'auto 1fr',
                  gap:'14px',
                  alignItems:'flex-start',
                  padding:'12px 0',
                  borderBottom:'1px dotted var(--g-100)',
                }}>
                  <span style={{
                    fontFamily:'var(--mono)',
                    fontSize:'11px',
                    color:'var(--g-400)',
                    letterSpacing:'0.04em',
                    paddingTop:'2px',
                  }}>{n}</span>
                  <div>
                    <div style={{
                      fontFamily:'var(--display)',
                      fontVariationSettings:'"opsz" 32, "wght" 600',
                      fontSize:'15px',
                      letterSpacing:'-0.015em',
                      marginBottom:'3px',
                    }}>{t}</div>
                    <div className="heritage" style={{fontSize:'12.5px',color:'var(--g-500)'}}>{d}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="help" style={{marginTop:'14px'}}>
              Aucune vue ne classe ni n'évalue les moteurs. Toutes affichent
              les données calculées dans l'ordre de configuration ; le tri
              et les filtres sont à votre main.
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

Object.assign(window, { ViewOverview });
