import React, { useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ArrowDownToLine, Check, FileType2, FileUp, Fingerprint, Grid3X3, Info, Search, ShieldCheck, Type, X, Crosshair, Download } from 'lucide-react'
import './style.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const fmt = (n) => Number(n || 0).toLocaleString('en-US')

function App() {
  const [font, setFont] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('glyphs')
  const [search, setSearch] = useState('')
  const [block, setBlock] = useState('All Unicode blocks')
  const [selected, setSelected] = useState(null)
  const [glyphDetail, setGlyphDetail] = useState(null)
  const [detailBusy, setDetailBusy] = useState(false)
  const [previewText, setPreviewText] = useState('Hamburgefontsiv 0123456789')
  const [previewSize, setPreviewSize] = useState(54)
  const [copied, setCopied] = useState(false)
  const [showPoints, setShowPoints] = useState(true)
  const [showControls, setShowControls] = useState(true)
  const [showMetrics, setShowMetrics] = useState(true)

  const fontUrl = font ? `${API}/api/fonts/${font.id}/file` : ''
  const blocks = useMemo(() => ['All Unicode blocks', ...new Set((font?.glyphs || []).map(g => g.block).sort())], [font])
  const filtered = useMemo(() => (font?.glyphs || []).filter(g => {
    const q = search.trim().toLowerCase()
    const matches = !q || [g.character, g.glyphName, g.unicode, g.unicodeName, g.block].some(v => String(v).toLowerCase().includes(q))
    return matches && (block === 'All Unicode blocks' || g.block === block)
  }), [font, search, block])

  async function upload(file) {
    if (!file) return
    setBusy(true); setError(''); setSelected(null); setGlyphDetail(null)
    const body = new FormData(); body.append('file', file)
    try {
      const response = await fetch(`${API}/api/fonts`, { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not inspect this font.')
      setFont(data); setSearch(''); setBlock('All Unicode blocks'); setTab('glyphs')
    } catch (e) { setError(`${e.message} Check that the Python API is running at ${API}.`) }
    finally { setBusy(false) }
  }

  async function selectGlyph(glyph) {
    setSelected(glyph); setGlyphDetail(null); setDetailBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/glyphs/${glyph.glyphId}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not inspect glyph details.')
      setGlyphDetail(data)
    } catch (e) { setError(e.message) }
    finally { setDetailBusy(false) }
  }

  function exportUnicode() {
    if (!font) return
    const rows = ['Character\tUnicode\tUnicode Name\tGlyph Name\tBlock', ...filtered.map(g => `${g.character}\t${g.unicode}\t${g.unicodeName}\t${g.glyphName}\t${g.block}`)]
    const blob = new Blob([rows.join('\n')], { type: 'text/tab-separated-values;charset=utf-8' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a')
    a.href = url; a.download = `${font.metadata?.family || 'font'}-unicode-map.tsv`; a.click(); URL.revokeObjectURL(url)
  }

  async function copyCharacters() {
    await navigator.clipboard.writeText(filtered.map(g => g.character).join(''))
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }

  function exportGlyphSvg(detail, glyph) {
    if (!detail?.outlinePath || !detail.bounds) return
    const b = detail.bounds
    const pad = Math.max(40, Math.round((b.width + b.height) * 0.04))
    const width = Math.max(1, b.width + pad * 2), height = Math.max(1, b.height + pad * 2)
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${b.xMin-pad} ${-b.yMax-pad} ${width} ${height}"><path d="${detail.outlinePath}" transform="scale(1,-1)" fill="#22231f"/></svg>`
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
    const a = document.createElement('a'); a.href = url; a.download = `${detail.glyphName || glyph?.glyphName || 'glyph'}.svg`; a.click(); URL.revokeObjectURL(url)
  }

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#top"><span className="brand-mark">A</span><span>ANGHSTUDIO <i>/</i> TYPE TOOLS</span></a>
      <div className="top-right"><span className="version">EARLY ACCESS · v0.3.0</span><a href="https://github.com/anghstudio/font-glyph-inspector" target="_blank" rel="noreferrer">GITHUB ↗</a></div>
    </header>

    <main id="top" className="main">
      <section className="intro">
        <div className="eyebrow"><span className="eyebrow-line"/> FONT ENGINEERING / 001</div>
        <h1>Font Glyph<br/><em>Inspector.</em></h1>
        <p className="lede">A closer look at the structure behind every typeface. Inspect glyphs, map Unicode coverage, and explore OpenType features in one workspace.</p>
        <div className="intro-meta"><span><ShieldCheck size={14}/> LOCAL FILE ANALYSIS</span><span><Fingerprint size={14}/> BUILT FOR TYPE DESIGNERS</span></div>
      </section>

      {!font ? <section className="upload-card">
        <div className="upload-heading"><div><span className="section-index">01 / START HERE</span><h2>Bring a typeface into focus.</h2></div><FileType2 size={25} strokeWidth={1.4}/></div>
        <label className={`dropzone ${busy ? 'is-busy' : ''}`} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); upload(e.dataTransfer.files?.[0]) }}>
          <input type="file" accept=".ttf,.otf,.woff,.woff2" onChange={e => upload(e.target.files?.[0])}/>
          <span className="upload-icon"><FileUp size={23}/></span>
          <strong>{busy ? 'Inspecting your font…' : 'Drop a font file here'}</strong>
          <span>or <u>browse files</u> from your computer</span>
          <small>TTF · OTF · WOFF · WOFF2 &nbsp; / &nbsp; MAX 30 MB</small>
        </label>
        {error && <div className="error"><Info size={16}/>{error}</div>}
        <div className="privacy-note"><ShieldCheck size={15}/> Your font is processed by the local API instance. Do not upload fonts you do not have permission to inspect.</div>
      </section> : <>
        <section className="loaded-heading">
          <div><span className="section-index">INSPECTING TYPEFACE</span><h2>{font.metadata?.family || font.filename}</h2><p>{font.metadata?.subfamily || 'Font file'} <span className="dot">·</span> {font.filename}</p></div>
          <label className="replace-button"> <FileUp size={15}/> Change font<input type="file" accept=".ttf,.otf,.woff,.woff2" onChange={e => upload(e.target.files?.[0])}/></label>
        </section>
        {error && <div className="error"><Info size={16}/>{error}</div>}
        <section className="stats-grid">
          <Stat icon={<Grid3X3/>} label="MAPPED UNICODE" value={fmt(font.statistics.mappedUnicode)}/>
          <Stat icon={<Type/>} label="TOTAL GLYPHS" value={fmt(font.statistics.totalGlyphs)}/>
          <Stat icon={<Activity/>} label="UNMAPPED GLYPHS" value={fmt(font.statistics.unmappedGlyphs)}/>
          <Stat icon={<FileType2/>} label="FONT TABLES" value={fmt(font.statistics.tableCount)}/>
        </section>
        <section className="preview-panel">
          <div className="panel-top"><div><span className="section-index">LIVE SPECIMEN</span><h3>Test your type.</h3></div><span className="font-label">{font.metadata?.fullName || font.filename}</span></div>
          <style>{`@font-face { font-family: 'UploadedSpecimen'; src: url('${fontUrl}'); }`}</style>
          <textarea className="specimen" style={{fontFamily:'UploadedSpecimen, sans-serif',fontSize:`${previewSize}px`}} value={previewText} onChange={e => setPreviewText(e.target.value)} aria-label="Live font specimen text" />
          <div className="preview-controls"><span>PREVIEW SIZE</span><input type="range" min="20" max="100" value={previewSize} onChange={e => setPreviewSize(Number(e.target.value))}/><b>{previewSize}px</b></div>
        </section>
        <section className="inspector-panel">
          <div className="tabs">{[['glyphs','Glyph map'],['opentype','OpenType'],['tables','Font tables'],['unmapped','Unmapped']].map(([id,label]) => <button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}{id==='glyphs' && <span>{fmt(font.glyphs.length)}</span>}</button>)}</div>
          {tab==='glyphs' && <>
            <div className="toolbar"><div className="searchbox"><Search size={16}/><input placeholder="Search character, glyph name, Unicode…" value={search} onChange={e=>setSearch(e.target.value)}/>{search && <button onClick={()=>setSearch('')}><X size={14}/></button>}</div><select value={block} onChange={e=>setBlock(e.target.value)}>{blocks.map(b=><option key={b}>{b}</option>)}</select><button className="text-action" onClick={copyCharacters}>{copied?<Check size={15}/>:<Type size={15}/>} {copied?'Copied':'Copy chars'}</button><button className="text-action" onClick={exportUnicode}><ArrowDownToLine size={15}/> Export TSV</button></div>
            <div className="glyph-grid">{filtered.map(g=><button key={g.codepoint} className={`glyph-cell ${selected?.codepoint===g.codepoint?'selected':''}`} onClick={()=>selectGlyph(g)}><span className="glyph-char" style={{fontFamily:'UploadedSpecimen, sans-serif'}}>{g.character}</span><span className="glyph-code">{g.unicode}</span><span className="glyph-name">{g.glyphName}</span></button>)}</div>
            {filtered.length===0 && <div className="empty">No glyphs match this filter.</div>}
            {selected && <div className="glyph-detail-wrap">
              <div className="glyph-detail"><div className="detail-symbol" style={{fontFamily:'UploadedSpecimen, sans-serif'}}>{selected.character}</div><div className="detail-fields"><span>GLYPH NAME <b>{selected.glyphName}</b></span><span>UNICODE <b>{selected.unicode} · {selected.unicodeName}</b></span><span>GLYPH ID <b>{selected.glyphId ?? '—'}</b></span><span>UNICODE BLOCK <b>{selected.block}</b></span><span>CATEGORY <b>{selected.category}</b></span></div><button onClick={()=>{setSelected(null);setGlyphDetail(null)}} aria-label="Close glyph details"><X size={17}/></button></div>
              <div className="glyph-engineering">
                <div className="engineering-heading"><span>GLYPH ENGINEERING</span><small>{detailBusy ? 'READING OUTLINE…' : glyphDetail ? 'DETAILS LOADED' : 'WAITING FOR DETAILS'}</small></div>
                {glyphDetail && <>
                  <div className="glyph-tools">
                    <button className={showPoints ? 'tool-active' : ''} onClick={() => setShowPoints(v => !v)}><Crosshair size={14}/> Points</button>
                    <button className={showControls ? 'tool-active' : ''} onClick={() => setShowControls(v => !v)}>Control handles</button>
                    <button className={showMetrics ? 'tool-active' : ''} onClick={() => setShowMetrics(v => !v)}>Metrics guides</button>
                    <button onClick={() => exportGlyphSvg(glyphDetail, selected)}><Download size={14}/> Export SVG</button>
                  </div>
                  <div className="engineering-grid">
                    <div className="outline-preview">{glyphDetail.outlineAvailable && glyphDetail.bounds ? <svg viewBox={`${glyphDetail.bounds.xMin - 100} ${-glyphDetail.bounds.yMax - 100} ${Math.max(glyphDetail.bounds.width + 200,1)} ${Math.max(glyphDetail.bounds.height + 200,1)}`} role="img" aria-label={`${glyphDetail.glyphName} outline`}>
                      {showMetrics && <g className="metric-guides" transform="scale(1,-1)"><line x1={glyphDetail.bounds.xMin-100} x2={glyphDetail.bounds.xMax+100} y1="0" y2="0"/><line x1={glyphDetail.bounds.xMin-100} x2={glyphDetail.bounds.xMax+100} y1={glyphDetail.bounds.yMin} y2={glyphDetail.bounds.yMin}/><line x1="0" x2="0" y1={glyphDetail.bounds.yMin-100} y2={glyphDetail.bounds.yMax+100}/></g>}
                      <path d={glyphDetail.outlinePath} transform="scale(1,-1)"/>
                      {showPoints && <g className="point-overlay" transform="scale(1,-1)">{(glyphDetail.outlinePoints || []).filter(p => p.kind === 'on-curve' || showControls).map(p => <g key={`${p.contour}-${p.index}`}><circle className={p.kind === 'control' ? 'control-point' : 'on-point'} cx={p.x} cy={p.y} r={p.kind === 'control' ? 16 : 23}/><title>{`Point ${p.index} · ${p.kind} · (${p.x}, ${p.y})`}</title></g>)}</g>}
                    </svg> : <span className="muted">No visible outline for this glyph.</span>}</div>
                    <div className="engineering-metrics">
                      <span>ADVANCE WIDTH <b>{glyphDetail.advanceWidth ?? '—'}</b></span><span>LEFT SIDE BEARING <b>{glyphDetail.leftSideBearing ?? '—'}</b></span>
                      <span>UNITS PER EM <b>{glyphDetail.unitsPerEm ?? '—'}</b></span><span>BOUNDING BOX <b>{glyphDetail.bounds ? `${Math.round(glyphDetail.bounds.width)} × ${Math.round(glyphDetail.bounds.height)}` : '—'}</b></span>
                      <span>CONTOURS <b>{glyphDetail.contourCount ?? 'N/A'}</b></span><span>POINTS <b>{glyphDetail.pointCount ?? 'N/A'}</b></span>
                      <span>COMPONENTS <b>{glyphDetail.componentCount ?? 'N/A'}</b></span><span>ADVANCE HEIGHT <b>{glyphDetail.advanceHeight ?? '—'}</b></span>
                      <span>POINT DATA <b>{glyphDetail.pointSource || '—'}</b></span><span>CONTOUR ENDS <b>{glyphDetail.contourEnds?.length ?? '—'}</b></span>
                    </div>
                  </div>
                  <div className="point-table-wrap"><div className="point-table-heading">OUTLINE POINTS <small>{glyphDetail.outlinePoints?.length || 0} records · coordinates in font units</small></div><div className="point-table">{(glyphDetail.outlinePoints || []).slice(0, 160).map(p => <div className="point-row" key={`${p.contour}-${p.index}`}><b>{p.index}</b><span>C{p.contour + 1}</span><span>{p.kind}</span><span>{Math.round(p.x)}</span><span>{Math.round(p.y)}</span></div>)}</div>{(glyphDetail.outlinePoints || []).length > 160 && <small className="muted">Showing first 160 points in the table. All points remain visible in the outline view.</small>}</div>
                </>}
              </div>
            </div>}
            <div className="result-count">SHOWING {fmt(filtered.length)} OF {fmt(font.glyphs.length)} MAPPED CHARACTERS</div>
          </>}
          {tab==='opentype' && <div className="structure-content">{['GSUB','GPOS','GDEF'].map(tag=>{const data=font.opentype[tag];return <div className="structure-card" key={tag}><div className="structure-head"><b>{tag}</b><span className={data.present?'present':'absent'}>{data.present?'PRESENT':'NOT FOUND'}</span></div>{data.features?.length ? <div className="feature-list">{data.features.map((f,i)=><div className="feature-row" key={`${f.tag}-${i}`}><code>{f.tag}</code><span>{featureName(f.tag)}</span><small>{f.lookups.length} lookup(s)</small></div>)}</div> : <p className="muted">{tag==='GDEF'?'Glyph definition table status.':'No feature records available in this table.'}</p>}{data.lookupCount!==undefined&&<small className="lookup-total">{data.lookupCount} lookup records</small>}</div>})}</div>}
          {tab==='tables' && <div className="table-list"><div className="table-row table-header"><span>TABLE TAG</span><span>DATA SIZE</span></div>{font.tables.map(t=><div className="table-row" key={t.tag}><code>{t.tag}</code><span>{fmt(t.length)} bytes</span></div>)}</div>}
          {tab==='unmapped' && <div className="unmapped-list"><p className="muted">Glyphs in the glyph order that are not mapped to a Unicode character in the best cmap.</p>{font.unmappedGlyphs.length ? font.unmappedGlyphs.map((g,i)=><code key={`${g}-${i}`}>{g}</code>) : <div className="empty">All glyphs in the glyph order are mapped in the best cmap.</div>}</div>}
        </section>
        <button className="close-font" onClick={()=>{setFont(null);setSelected(null);setGlyphDetail(null)}}>Close font session <X size={14}/></button>
      </>}

      <footer><span>© 2026 ANGHSTUDIO</span><span>OPEN SOURCE / MIT LICENSE</span><span>MADE FOR TYPE PEOPLE.</span></footer>
    </main>
  </div>
}

function Stat({icon,label,value}) { return <div className="stat"><div className="stat-icon">{icon}</div><span>{label}</span><strong>{value}</strong></div> }
function featureName(tag) { return ({liga:'Standard ligatures',clig:'Contextual ligatures',calt:'Contextual alternates',kern:'Kerning',mark:'Mark-to-base positioning',mkmk:'Mark-to-mark positioning',curs:'Cursive attachment',ccmp:'Glyph composition / decomposition',locl:'Localized forms',salt:'Stylistic alternates',swsh:'Swash',frac:'Fractions',ordn:'Ordinals',numr:'Numerators',dnom:'Denominators',sups:'Superscripts',subs:'Subscripts'})[tag] || 'OpenType layout feature' }

createRoot(document.getElementById('root')).render(<App />)
