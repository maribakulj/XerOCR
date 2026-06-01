/* View 03 — Par document : galerie + drill-in.
   Vue par défaut = grille des 42 documents. Clic sur une vignette =
   détail plein écran (fac-similé + diff par moteur + signaux). */

/* -- Fac-similé placeholder ----------------------------------------- */
function FacsimilePlaceholder({ docId }) {
  return (
    <div style={{
      aspectRatio:'3/4',
      background:'var(--surface)',
      borderRadius:'var(--r-md)',
      position:'relative',
      overflow:'hidden',
      boxShadow:'var(--shadow-sm)',
      backgroundImage: `
        repeating-linear-gradient(0deg,
          transparent 0, transparent 32px,
          var(--g-100) 32px, var(--g-100) 33px,
          transparent 33px, transparent 40px,
          var(--g-150) 40px, var(--g-150) 41px),
        repeating-linear-gradient(91deg,
          var(--g-100) 0, var(--g-100) 2px,
          transparent 2px, transparent 7px)`,
    }}>
      <div style={{
        position:'absolute',top:0,right:0,width:'34px',height:'34px',
        background:'linear-gradient(225deg, var(--paper) 50%, var(--g-100) 50%)',
      }}></div>
      <div style={{
        position:'absolute',bottom:'14px',right:'14px',
        display:'flex',flexDirection:'column',gap:'4px',
      }}>
        <button className="btn btn-sm" style={{padding:'5px 9px',background:'rgba(251,250,246,0.95)'}}>+</button>
        <button className="btn btn-sm" style={{padding:'5px 9px',background:'rgba(251,250,246,0.95)'}}>−</button>
        <button className="btn btn-sm" style={{padding:'5px 9px',background:'rgba(251,250,246,0.95)'}}>↺</button>
      </div>
      <div style={{
        position:'absolute',top:'14px',left:'14px',
        background:'rgba(26,25,23,0.85)',color:'var(--paper)',
        padding:'4px 12px',borderRadius:'var(--r-pill)',
        fontFamily:'var(--mono)',fontSize:'10.5px',letterSpacing:'0.04em',
      }}>{docId}</div>
      <div style={{
        position:'absolute',inset:'40% 12% auto 12%',textAlign:'center',
      }}>
        <div style={{
          fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-400)',
          letterSpacing:'0.16em',textTransform:'uppercase',
          background:'rgba(251,250,246,0.85)',display:'inline-block',
          padding:'6px 14px',borderRadius:'var(--r-pill)',
        }}>fac-similé · 2412 × 3204 px</div>
      </div>
    </div>
  );
}

/* -- Doc card (clickable) ------------------------------------------- */
function DocCard({ doc, idx, onClick }) {
  const isManuscript = doc.strata === 'manuscrit';
  const stratumColor = doc.strata === 'presse' ? 'slate' : doc.strata === 'imprimé' ? 'fern' : 'clay';

  return (
    <button className="doc-card" onClick={onClick}>
      <div style={{
        position:'relative',
        aspectRatio: isManuscript ? '3/4' : '4/5',
        background:'var(--g-50)',
        backgroundImage: isManuscript
          ? `repeating-linear-gradient(${85 + (idx%5)*2}deg, var(--g-100) 0, var(--g-100) 1px, transparent 1px, transparent 14px),
             repeating-linear-gradient(0deg, var(--g-50) 0, var(--g-50) 6px, var(--surface) 6px, var(--surface) 22px)`
          : `repeating-linear-gradient(0deg, var(--g-100) 0, var(--g-100) 1px, transparent 1px, transparent ${5 + (idx%3)}px)`,
        borderBottom:'1px solid var(--g-50)',
      }}>
        <div style={{position:'absolute',top:'10px',left:'10px'}}>
          <span className={`tag tag-${stratumColor}`} style={{fontSize:'9.5px'}}>{doc.strata}</span>
        </div>
        <div style={{position:'absolute',top:'10px',right:'10px',background:'rgba(251,250,246,0.85)',padding:'3px 8px',borderRadius:'var(--r-pill)',fontFamily:'var(--mono)',fontSize:'9.5px',color:'var(--g-500)',letterSpacing:'0.04em'}}>
          ouvrir →
        </div>
        <div style={{
          position:'absolute',inset:0,display:'flex',
          alignItems:'center',justifyContent:'center',
        }}>
          <div style={{
            background:'rgba(251,250,246,0.92)',
            padding:'8px 14px',borderRadius:'var(--r-pill)',
            fontFamily:'var(--mono)',fontSize:'10px',
            color:'var(--g-500)',letterSpacing:'0.06em',
          }}>{doc.id}</div>
        </div>
      </div>

      <div style={{padding:'12px 14px 14px',display:'flex',flexDirection:'column',gap:'10px'}}>
        <div style={{
          fontFamily:'var(--serif)',fontSize:'13.5px',lineHeight:1.35,
          color:'var(--ink)',minHeight:'34px',
        }}>{doc.label}</div>

        {/* Per-engine CER row — neutral, all rendered identically */}
        <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:'3px'}}>
          {doc.cers.map((c, i) => (
            <div key={i} style={{
              display:'flex',flexDirection:'column',alignItems:'center',
              gap:'2px',padding:'5px 0 6px',
              background:'var(--surface)',
              borderRadius:'6px',
              borderTop:`2px solid var(--${ENGINES[i].color})`,
            }}>
              <span style={{fontFamily:'var(--mono)',fontSize:'9px',color:'var(--g-400)',letterSpacing:'0.04em'}}>{ENGINES[i].id}</span>
              <span style={{fontFamily:'var(--mono)',fontVariantNumeric:'tabular-nums',fontSize:'11px',color:'var(--g-700)'}}>
                {(c*100).toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </button>
  );
}

/* -- Drill-in : document detail panel ------------------------------- */
function DocDetail({ doc, idx, onBack, onPrev, onNext }) {
  const [selectedEngine, setSelectedEngine] = React.useState(2);

  return (
    <React.Fragment>

      {/* Drill-in header */}
      <div className="view-hero">
        <div style={{display:'flex',flexDirection:'column',gap:'4px',maxWidth:'70%'}}>
          <button className="drill-back" onClick={onBack} style={{alignSelf:'flex-start'}}>
            <span className="arrow">←</span> retour à la galerie
          </button>
          <div className="view-hero-eyebrow" style={{marginTop:'8px'}}>
            document #{String(idx+1).padStart(2,'0')} sur {DOCUMENTS.length} · {doc.strata}
          </div>
          <div className="view-hero-name" style={{fontSize:'30px'}}>{doc.label}</div>
          <div className="view-hero-desc">
            Identifiant <span style={{fontFamily:'var(--mono)',color:'var(--ink)'}}>{doc.id}</span> ·
            numérisation Gallica · fac-similé 2412 × 3204 px.
          </div>
        </div>
        <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
          <button className="btn btn-sm" onClick={onPrev}>← Précédent</button>
          <span style={{fontFamily:'var(--mono)',fontSize:'11px',color:'var(--g-400)'}}>{idx+1} / {DOCUMENTS.length}</span>
          <button className="btn btn-sm btn-primary" onClick={onNext}>Suivant →</button>
        </div>
      </div>

      {/* Main split */}
      <div className="grid-2" style={{gridTemplateColumns:'1fr 1.25fr',alignItems:'stretch'}}>
        {/* LEFT — facsimile + per-engine CER */}
        <div className="sec" style={{display:'flex',flexDirection:'column',gap:'14px'}}>
          <div className="sec-head" style={{marginBottom:0}}>
            <div className="sec-title">Fac-similé</div>
            <div className="sec-aside">cliquer pour zoomer</div>
          </div>
          <FacsimilePlaceholder docId={doc.id} />

          <div className="surface-flat" style={{padding:'14px 16px'}}>
            <div className="label" style={{marginBottom:'10px'}}>CER par moteur · ce document</div>
            <div className="stack-sm">
              {ENGINES.map((e, i) => (
                <div key={e.id} style={{
                  display:'grid',
                  gridTemplateColumns:'28px 1fr 80px 64px',
                  gap:'10px',
                  alignItems:'center',
                  padding:'4px 8px',
                  borderRadius:'var(--r-sm)',
                  background: i === selectedEngine ? `var(--${e.color}-soft)` : 'transparent',
                  cursor:'pointer',
                }} onClick={() => setSelectedEngine(i)}>
                  <span className={`eng-id ${e.color}`} style={{padding:'2px 8px',fontSize:'10px'}}>{e.id}</span>
                  <span style={{fontSize:'12.5px',fontWeight:500}}>{e.name}</span>
                  <div className="b-track" style={{height:'6px'}}>
                    <div className={`b-fill ${e.color}`} style={{width:Math.min(100, doc.cers[i]*100*4)+'%'}}></div>
                  </div>
                  <span className="num" style={{
                    justifySelf:'end',
                    fontFamily:'var(--mono)',
                    fontVariantNumeric:'tabular-nums',
                    fontSize:'12px',
                    color:'var(--ink)',
                  }}>{pct(doc.cers[i])}</span>
                </div>
              ))}
            </div>
            <div className="help" style={{marginTop:'10px',fontSize:'11.5px',paddingLeft:'10px'}}>
              Cliquer une ligne pour afficher le diff de ce moteur ci-contre.
            </div>
          </div>
        </div>

        {/* RIGHT — diff */}
        <div style={{display:'flex',flexDirection:'column',gap:'14px'}}>
          <div className="sec" style={{flex:1,display:'flex',flexDirection:'column',gap:'14px'}}>
            <div className="sec-head" style={{marginBottom:0}}>
              <div className="sec-title">Diff vérité-terrain / sortie OCR</div>
              <div className="sec-aside">profil diplomatique · niveau caractère</div>
            </div>

            <div className="segmented" style={{alignSelf:'flex-start',flexWrap:'wrap'}}>
              {ENGINES.map((e, i) => (
                <button key={e.id} className={i === selectedEngine ? 'on' : ''}
                        onClick={() => setSelectedEngine(i)}>
                  {e.id} · {e.name}
                </button>
              ))}
            </div>

            <div>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:'6px'}}>
                <span className="label">Vérité terrain</span>
                <span style={{fontFamily:'var(--mono)',fontSize:'10px',color:'var(--g-400)'}}>1284 caractères · 218 mots</span>
              </div>
              <div className="diff" style={{maxHeight:'130px',overflowY:'auto'}}>
                Le Moniteur Universel — édition du 7 juillet 1812.{' '}
                Les nouvelles parvenues hier soir de Smolensk
                annoncent que l'avant-garde de la Grande Armée
                a franchi le Dniepr ; les détachements de cosaques se
                retirent en désordre devant la cavalerie du maréchal Murat.
                Sa Majesté l'Empereur a passé en revue la division
                Friant ; les troupes sont en parfaite santé.
              </div>
            </div>

            <div>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:'6px'}}>
                <span className="label">Sortie · {ENGINES[selectedEngine].name}</span>
                <span style={{fontFamily:'var(--mono)',fontSize:'10px',color:'var(--g-500)'}}>
                  CER {pct(doc.cers[selectedEngine])} · diff niveau caractère
                </span>
              </div>
              <div className="diff" style={{maxHeight:'180px',overflowY:'auto'}}>
                Le Moniteur <span className="sub">Univerſel</span> — édition du 7 <span className="sub">juiḷlet</span> 1812.{' '}
                Les nouvelles parvenues hier soir de <span className="sub">Smolensk</span>
                <span className="add">'</span> annoncent que l'avant-<span className="del">garde</span><span className="add">gar de</span> de la Grande Armée
                a franchi le <span className="sub">Dnieper</span> ; les détachements de cosaques <span className="del">se</span>
                <span className="add">ſe</span> retirent en désordre devant la cavalerie du maréchal <span className="sub">Murat.</span>
                Sa Majesté l'<span className="sub">Empereur</span> a passé en revue la division
                <span className="sub">Friand</span> ; les troupes sont en parfaite <span className="sub">ſanté.</span>
              </div>
            </div>

            <div style={{display:'flex',gap:'14px',flexWrap:'wrap',paddingTop:'10px',borderTop:'1px solid var(--g-50)'}}>
              <span style={{display:'inline-flex',alignItems:'center',gap:'6px',fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-500)',letterSpacing:'0.04em'}}>
                <span className="diff" style={{padding:'2px 6px',background:'var(--fern-soft)',color:'var(--fern-deep)',fontFamily:'var(--mono)'}}>add</span> insertion OCR
              </span>
              <span style={{display:'inline-flex',alignItems:'center',gap:'6px',fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-500)',letterSpacing:'0.04em'}}>
                <span className="diff" style={{padding:'2px 6px',background:'oklch(0.95 0.03 28)',color:'var(--err)',fontFamily:'var(--mono)'}}>del</span> omission
              </span>
              <span style={{display:'inline-flex',alignItems:'center',gap:'6px',fontFamily:'var(--mono)',fontSize:'10.5px',color:'var(--g-500)',letterSpacing:'0.04em'}}>
                <span className="diff" style={{padding:'2px 6px',background:'var(--butter-soft)',color:'var(--butter-deep)',fontFamily:'var(--mono)'}}>sub</span> substitution
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Taxonomy + difficulty signals */}
      <div className="grid-2">
        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Taxonomie d'erreurs · ce document</div>
            <div className="sec-aside">moteur sélectionné · classes 1–9</div>
          </div>
          <div className="stack-sm">
            {[
              { label:'Ligature ſ → s',          v:0.42, c:'fern',   n:8 },
              { label:'Accent grave/aigu',       v:0.22, c:'slate',  n:5 },
              { label:'Capitalisation',          v:0.18, c:'clay',   n:4 },
              { label:'Espacement / césure',     v:0.10, c:'butter', n:2 },
              { label:'Substitution mot rare',   v:0.08, c:'ink',    n:1 },
            ].map(b => (
              <div key={b.label} className="bar-row">
                <span className="b-label">{b.label}</span>
                <div className="b-track">
                  <div className={`b-fill ${b.c}`} style={{width:(b.v*100*1.8)+'%'}}></div>
                </div>
                <span className="b-value">{b.n} / 20</span>
              </div>
            ))}
          </div>
        </div>

        <div className="sec">
          <div className="sec-head">
            <div className="sec-title">Signaux de difficulté</div>
            <div className="sec-aside">image · philologique</div>
          </div>
          <div className="grid-2">
            <div className="readout">
              <div className="r-label">qualité image</div>
              <div className="r-value">0.42<span className="r-unit">/1</span></div>
              <div className="r-delta">médiane corpus · 0.73</div>
            </div>
            <div className="readout">
              <div className="r-label">ancrage trigrammes</div>
              <div className="r-value">0.94</div>
              <div className="r-delta">échelle 0 – 1</div>
            </div>
            <div className="readout">
              <div className="r-label">script_type</div>
              <div className="r-value" style={{fontSize:'22px'}}>{doc.strata}</div>
              <div className="r-delta">stratification corpus</div>
            </div>
            <div className="readout">
              <div className="r-label">overlap MUFI</div>
              <div className="r-value">68<span className="r-unit">%</span></div>
              <div className="r-delta">ligatures + ſ longue</div>
            </div>
          </div>
        </div>
      </div>

    </React.Fragment>
  );
}

/* -- Gallery shell -------------------------------------------------- */
function GalleryShell() {
  return (
    <React.Fragment>

      <HeroBand
        eyebrow="vue 03 · par document"
        title="Par document"
        desc="42 documents dans l'ordre du manifeste, avec le CER calculé par chaque moteur sous chaque vignette. Cliquer une vignette pour ouvrir le fac-similé, la sortie de chaque moteur et le diff avec la vérité terrain."
        stats={[
          { v: '42', k: 'documents', u: '' },
          { v: '3',  k: 'strates',   u: '' },
          { v: '210', k: 'mesures CER', u: '' },
        ]}
      />

      <div className="sec" style={{padding:'14px 20px'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:'14px',flexWrap:'wrap'}}>
          <div style={{display:'flex',gap:'12px',alignItems:'center',flexWrap:'wrap'}}>
            <span className="label">strate</span>
            <div className="segmented">
              <button className="on">Toutes · 42</button>
              <button>Presse · 22</button>
              <button>Imprimés · 11</button>
              <button>Manuscrits · 9</button>
            </div>
            <span className="label" style={{marginLeft:'8px'}}>tri</span>
            <div className="segmented">
              <button className="on">Manifeste</button>
              <button>Date doc</button>
              <button>Identifiant</button>
            </div>
          </div>
          <div style={{display:'flex',gap:'8px'}}>
            <button className="btn btn-sm">⊞ Grille</button>
            <button className="btn btn-sm btn-ghost">≡ Liste</button>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

/* -- View shell with drill-in state --------------------------------- */
function ViewByDocument({ initialSelected }) {
  const [selected, setSelected] = React.useState(
    typeof initialSelected === 'number' ? initialSelected : null
  );

  return (
    <div className="report-board" data-screen-label={selected === null ? "03 Par document · galerie" : "03 Par document · détail"}>
      <ReportChrome active="documents" />
      <div className="report-main">

        {selected === null && (
          <React.Fragment>
            <GalleryShell />

            <div style={{
              display:'grid',
              gridTemplateColumns:'repeat(4, 1fr)',
              gap:'14px',
            }}>
              {DOCUMENTS.map((doc, i) => (
                <DocCard
                  key={doc.id}
                  doc={doc}
                  idx={i}
                  onClick={() => setSelected(i)}
                />
              ))}
            </div>

            <div className="sec">
              <div className="sec-head">
                <div className="sec-title">Distribution du CER · tous moteurs confondus</div>
                <div className="sec-aside">42 docs × 5 moteurs = 210 mesures</div>
              </div>
              <div style={{display:'flex',gap:'14px',alignItems:'flex-end',height:'140px',padding:'0 8px'}}>
                {[
                  { x:'0-2',   c:18 },
                  { x:'2-5',   c:42 },
                  { x:'5-10',  c:54 },
                  { x:'10-15', c:38 },
                  { x:'15-20', c:24 },
                  { x:'20-25', c:14 },
                  { x:'25-30', c:11 },
                  { x:'30+',   c: 9 },
                ].map((b, i) => (
                  <div key={i} style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',gap:'6px'}}>
                    <div style={{
                      width:'100%',
                      height: (b.c / 54) * 100 + '%',
                      background:'var(--ink)',
                      borderRadius:'6px 6px 0 0',
                      position:'relative',
                    }}>
                      <div style={{
                        position:'absolute',top:'-18px',left:0,right:0,
                        textAlign:'center',fontFamily:'var(--mono)',
                        fontVariantNumeric:'tabular-nums',fontSize:'10.5px',
                        color:'var(--g-500)',
                      }}>{b.c}</div>
                    </div>
                    <div style={{
                      fontFamily:'var(--mono)',fontSize:'9.5px',
                      color:'var(--g-400)',letterSpacing:'0.04em',
                    }}>{b.x}%</div>
                  </div>
                ))}
              </div>
              <div className="help" style={{marginTop:'14px'}}>
                Distribution brute des CER observés dans le run. Aucun seuil n'est posé par l'outil —
                l'interprétation des bornes appartient au lecteur, selon le type d'usage aval.
              </div>
            </div>
          </React.Fragment>
        )}

        {selected !== null && (
          <DocDetail
            doc={DOCUMENTS[selected]}
            idx={selected}
            onBack={() => setSelected(null)}
            onPrev={() => setSelected((selected - 1 + DOCUMENTS.length) % DOCUMENTS.length)}
            onNext={() => setSelected((selected + 1) % DOCUMENTS.length)}
          />
        )}

      </div>
    </div>
  );
}

/* Wrapper for canvas — forces the drill-in state. */
function ViewByDocumentDrilled() { return <ViewByDocument initialSelected={2} />; }

Object.assign(window, { ViewByDocument, ViewByDocumentDrilled });
