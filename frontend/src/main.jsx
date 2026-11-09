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
  const [openTypeDetail, setOpenTypeDetail] = useState(null)
  const [openTypeBusy, setOpenTypeBusy] = useState(false)
  const [diagnostics, setDiagnostics] = useState(null)
  const [quality, setQuality] = useState(null)
  const [qualityBusy, setQualityBusy] = useState(false)
  const [variableData, setVariableData] = useState(null)
  const [variableBusy, setVariableBusy] = useState(false)
  const [variableValidation, setVariableValidation] = useState(null)
  const [variableValidationBusy, setVariableValidationBusy] = useState(false)
  const [axisValues, setAxisValues] = useState({})
  const [diagnosticsBusy, setDiagnosticsBusy] = useState(false)
  const [pairPages, setPairPages] = useState({})
  const [detailBusy, setDetailBusy] = useState(false)
  const [previewText, setPreviewText] = useState('Hamburgefontsiv 0123456789')
  const [previewSize, setPreviewSize] = useState(54)
  const [copied, setCopied] = useState(false)
  const [showPoints, setShowPoints] = useState(true)
  const [showControls, setShowControls] = useState(true)
  const [showMetrics, setShowMetrics] = useState(true)
  const [showBezier, setShowBezier] = useState(true)
  const [showControlPolygon, setShowControlPolygon] = useState(true)
  const [showContourStarts, setShowContourStarts] = useState(true)

  const fontUrl = font ? `${API}/api/fonts/${font.id}/file` : ''
  const variationSettings = useMemo(() => Object.entries(axisValues).map(([tag, value]) => `'${tag}' ${value}`).join(', '), [axisValues])
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
      setFont(data); setOpenTypeDetail(null); setDiagnostics(null); setQuality(null); setVariableData(null); setVariableValidation(null); setAxisValues({}); setPairPages({}); setSearch(''); setBlock('All Unicode blocks'); setTab('glyphs')
    } catch (e) { setError(`${e.message} Check that the Python API is running at ${API}.`) }
    finally { setBusy(false) }
  }

  async function loadOpenType() {
    if (!font || openTypeDetail || openTypeBusy) return
    setOpenTypeBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/opentype`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not inspect OpenType layout tables.')
      setOpenTypeDetail(data)
    } catch (e) { setError(e.message) }
    finally { setOpenTypeBusy(false) }
  }

  async function loadDiagnostics() {
    if (!font || diagnostics || diagnosticsBusy) return
    setDiagnosticsBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/diagnostics`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not inspect font structure.')
      setDiagnostics(data)
    } catch (e) { setError(e.message) }
    finally { setDiagnosticsBusy(false) }
  }

  async function loadVariable() {
    if (!font || variableData || variableBusy) return
    setVariableBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/variable`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not inspect variable-font data.')
      setVariableData(data)
      setAxisValues(Object.fromEntries((data.axes || []).map(axis => [axis.tag, axis.default])))
    } catch (e) { setError(e.message) }
    finally { setVariableBusy(false) }
  }

  async function loadVariableValidation() {
    if (!font || variableValidation || variableValidationBusy) return
    setVariableValidationBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/variable-validation`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not validate variable-font interpolation.')
      setVariableValidation(data)
    } catch (e) { setError(e.message) }
    finally { setVariableValidationBusy(false) }
  }

  function applyInstance(instance) {
    if (!instance || !variableData) return
    setAxisValues(Object.fromEntries(variableData.axes.map(axis => [axis.tag, instance.coordinates?.[axis.tag] ?? axis.default])))
  }

  async function loadQuality() {
    if (!font || quality || qualityBusy) return
    setQualityBusy(true)
    try {
      const response = await fetch(`${API}/api/fonts/${font.id}/quality`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not analyze font completeness.')
      setQuality(data)
    } catch (e) { setError(e.message) }
    finally { setQualityBusy(false) }
  }

  function exportQuality() {
    if (!quality || !font) return
    const blob = new Blob([JSON.stringify({font: font.filename, ...quality}, null, 2)], {type:'application/json'})
    const url = URL.createObjectURL(blob); const a = document.createElement('a')
    a.href = url; a.download = `${font.metadata?.family || 'font'}-quality-report.json`; a.click(); URL.revokeObjectURL(url)
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
      <div className="top-right"><span className="version">EARLY ACCESS · v0.8.0</span><a href="https://github.com/anghstudio/font-glyph-inspector" target="_blank" rel="noreferrer">GITHUB ↗</a></div>
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
          <div className="tabs">{[['glyphs','Glyph map'],['variable','Variable Lab'],['varvalidation','VF Validation'],['opentype','OpenType Deep'],['diagnostics','Diagnostics'],['quality','Quality'],['tables','Font tables'],['unmapped','Unmapped']].map(([id,label]) => <button key={id} className={tab===id?'active':''} onClick={()=>{setTab(id); if(id==='variable') loadVariable(); if(id==='varvalidation') loadVariableValidation(); if(id==='opentype') loadOpenType(); if(id==='diagnostics') loadDiagnostics(); if(id==='quality') loadQuality()}}>{label}{id==='glyphs' && <span>{fmt(font.glyphs.length)}</span>}</button>)}</div>
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
                      {glyphDetail.contourAnalysis && <g className="bezier-overlay" transform="scale(1,-1)">
                        {showControlPolygon && glyphDetail.contourAnalysis.contours.flatMap(c => c.segments.map((seg, i) => seg.controls.length ? <g key={`cp-${c.index}-${i}`} className="control-polygon">
                          <polyline points={[seg.start,...seg.controls,seg.end].map(pt=>`${pt[0]},${pt[1]}`).join(' ')}/>
                          {seg.controls.map((pt,j)=><circle key={j} cx={pt[0]} cy={pt[1]} r="13"/>)}
                        </g> : null))}
                        {showBezier && glyphDetail.contourAnalysis.contours.flatMap(c => c.segments.map((seg,i)=><path key={`seg-${c.index}-${i}`} className={`bezier-segment ${seg.type}`} d={segmentPath(seg)}><title>{`Contour ${c.index + 1}, segment ${i + 1}: ${seg.type}`}</title></path>))}
                        {showContourStarts && glyphDetail.contourAnalysis.contours.map(c=><g key={`start-${c.index}`}><circle className="contour-start" cx={c.start?.[0] ?? c.segments[0]?.start[0] ?? 0} cy={c.start?.[1] ?? c.segments[0]?.start[1] ?? 0} r="24"/><title>{`Contour ${c.index + 1} start`}</title></g>)}
                      </g>}
                    </svg> : <span className="muted">No visible outline for this glyph.</span>}</div>
                    <div className="engineering-metrics">
                      <span>ADVANCE WIDTH <b>{glyphDetail.advanceWidth ?? '—'}</b></span><span>LEFT SIDE BEARING <b>{glyphDetail.leftSideBearing ?? '—'}</b></span>
                      <span>UNITS PER EM <b>{glyphDetail.unitsPerEm ?? '—'}</b></span><span>BOUNDING BOX <b>{glyphDetail.bounds ? `${Math.round(glyphDetail.bounds.width)} × ${Math.round(glyphDetail.bounds.height)}` : '—'}</b></span>
                      <span>CONTOURS <b>{glyphDetail.contourCount ?? 'N/A'}</b></span><span>POINTS <b>{glyphDetail.pointCount ?? 'N/A'}</b></span>
                      <span>COMPONENTS <b>{glyphDetail.componentCount ?? 'N/A'}</b></span><span>ADVANCE HEIGHT <b>{glyphDetail.advanceHeight ?? '—'}</b></span>
                      <span>POINT DATA <b>{glyphDetail.pointSource || '—'}</b></span><span>CONTOUR ENDS <b>{glyphDetail.contourEnds?.length ?? '—'}</b></span>
                    </div>
                  </div>
                  {glyphDetail.contourAnalysis && <section className="contour-lab">
                    <div className="contour-lab-heading"><div><span>V0.4 / BÉZIER & CONTOUR LAB</span><small>{glyphDetail.contourAnalysis.segmentCount} segments · {glyphDetail.contourAnalysis.contourCount} contours</small></div><div className="contour-toggles">
                      <button className={showBezier ? 'tool-active' : ''} onClick={()=>setShowBezier(v=>!v)}>Bezier segments</button>
                      <button className={showControlPolygon ? 'tool-active' : ''} onClick={()=>setShowControlPolygon(v=>!v)}>Control polygon</button>
                      <button className={showContourStarts ? 'tool-active' : ''} onClick={()=>setShowContourStarts(v=>!v)}>Contour starts</button>
                    </div></div>
                    <div className="segment-summary"><span>LINE <b>{glyphDetail.contourAnalysis.segmentTypeTotals.line}</b></span><span>QUADRATIC <b>{glyphDetail.contourAnalysis.segmentTypeTotals.quadratic}</b></span><span>CUBIC <b>{glyphDetail.contourAnalysis.segmentTypeTotals.cubic}</b></span></div>
                    <div className="contour-list">{glyphDetail.contourAnalysis.contours.map(c=><div className="contour-row" key={c.index}><b>Contour {c.index+1}</b><span>{c.closed ? 'CLOSED' : 'OPEN'}</span><span>{c.direction || 'UNDEFINED'}</span><span>{c.segmentCount} segments</span><span>Area ≈ {c.signedArea == null ? '—' : Math.round(c.signedArea).toLocaleString('en-US')}</span></div>)}</div>
                    <div className="diagnostics-heading">OUTLINE DIAGNOSTICS <small>{glyphDetail.contourAnalysis.diagnostics.length} finding(s)</small></div>
                    {glyphDetail.contourAnalysis.diagnostics.length ? <div className="diagnostics-list">{glyphDetail.contourAnalysis.diagnostics.map((d,i)=><div className="diagnostic-row" key={`${d.code}-${i}`}><b>{d.code.replaceAll('_',' ')}</b><span>{d.message}</span></div>)}</div> : <div className="diagnostics-clean">No contour structure warnings detected.</div>}
                    <small className="muted">Direction and area use font coordinates (Y-up). Curve area and boundary intersections are sampled approximations; intersection findings do not imply filled-area overlap.</small>
                    {glyphDetail.contourAnalysis.intersectionScanTruncated && <small className="muted">Intersection scan reached its safety limit; results may be incomplete.</small>}
                  </section>}
                  <div className="point-table-wrap"><div className="point-table-heading">OUTLINE POINTS <small>{glyphDetail.outlinePoints?.length || 0} records · coordinates in font units</small></div><div className="point-table">{(glyphDetail.outlinePoints || []).slice(0, 160).map(p => <div className="point-row" key={`${p.contour}-${p.index}`}><b>{p.index}</b><span>C{p.contour + 1}</span><span>{p.kind}</span><span>{Math.round(p.x)}</span><span>{Math.round(p.y)}</span></div>)}</div>{(glyphDetail.outlinePoints || []).length > 160 && <small className="muted">Showing first 160 points in the table. All points remain visible in the outline view.</small>}</div>
                </>}
              </div>
            </div>}
            <div className="result-count">SHOWING {fmt(filtered.length)} OF {fmt(font.glyphs.length)} MAPPED CHARACTERS</div>
          </>}
          {tab==='varvalidation' && <div className="variable-panel">
            <div className="ot-intro"><span>VARIABLE FONT VALIDATION / INTERPOLATION ANALYSIS</span><small>Structural checks + real static instance generation · read-only</small></div>
            {variableValidationBusy && <div className="empty">Validating axis metadata and generating representative static instances…</div>}
            {!variableValidationBusy && variableValidation && <>
              {!variableValidation.isVariable ? <div className="variable-empty"><b>STATIC FONT DETECTED</b><p>This file does not contain variable-font axes. Interpolation tests are not applicable.</p></div> : <>
                <div className="variable-summary">
                  <div><strong>{variableValidation.summary.errors}</strong><span>ERRORS</span></div>
                  <div><strong>{variableValidation.summary.warnings}</strong><span>WARNINGS</span></div>
                  <div><strong>{variableValidation.summary.locationsPassed}/{variableValidation.summary.locationsTested}</strong><span>INSTANCES PASSED</span></div>
                  <div><strong>{variableValidation.summary.locationsFailed}</strong><span>INSTANCES FAILED</span></div>
                </div>
                <div className="variable-section-heading"><div><b>VALIDATION FINDINGS</b><small>Errors indicate detected structural problems; warnings require designer review.</small></div></div>
                <div className="diagnostic-findings">{variableValidation.findings.map((f,i)=><article className={`diagnostic-finding ${f.severity}`} key={`${f.code}-${i}`}>
                  <div><b>{f.code.replaceAll('_',' ')}</b><span>{f.severity.toUpperCase()}</span></div><code>{f.location}</code><p>{f.message}</p>{f.recommendation&&<small>Recommendation: {f.recommendation}</small>}
                </article>)}</div>
                <div className="variable-section-heading"><div><b>MULTI-LOCATION INSTANCE TESTS</b><small>Generated with fontTools instancer at representative design-space coordinates.</small></div></div>
                <div className="vf-test-list">{variableValidation.tests.map((test,i)=><article className={`vf-test ${test.status}`} key={`${test.name}-${i}`}>
                  <div><b>{test.name}</b><span>{test.status.toUpperCase()}</span></div>
                  <code>{Object.entries(test.coordinates).map(([tag,value])=>`${tag} ${value}`).join(' · ')}</code>
                  <small>{test.status==='passed'?`${fmt(test.glyphCount)} glyphs in generated instance`:test.message}</small>
                </article>)}</div>
                <div className="variable-section-heading"><div><b>TEST SCOPE</b><small>{variableValidation.scope.join(' · ')}</small></div></div>
                <div className="vf-limitations"><b>IMPORTANT LIMITATIONS</b>{variableValidation.limitations.map((item,i)=><p key={i}>{item}</p>)}</div>
              </>}
            </>}
          </div>}
          {tab==='opentype' && <div className="ot-deep">
            {openTypeBusy && <div className="empty">Reading GSUB and GPOS lookup structures…</div>}
            {!openTypeBusy && openTypeDetail && <>
              <div className="ot-intro"><span>OPENTYPE LAYOUT ANALYSIS</span><small>Decoded from the uploaded font · read-only</small></div>
              {['GSUB','GPOS'].map(tag=>{const data=openTypeDetail[tag] || {}; const lookups=data.lookups||[]; const features=data.features||[]; return <section className="ot-section" key={tag}>
                <div className="ot-section-head"><div><b>{tag}</b><small>{tag==='GSUB'?'Glyph substitution':'Glyph positioning'}</small></div><span>{data.present?`${lookups.length} LOOKUPS`:'TABLE NOT FOUND'}</span></div>
                <div className="ot-feature-block"><h4>FEATURE → LOOKUP MAPPING</h4>{features.length ? <div className="ot-feature-grid">{features.map((f,i)=><div className="ot-feature-row" key={`${f.tag}-${i}`}><code>{f.tag}</code><span>{featureName(f.tag)}</span><b>{f.lookupIndices.length?f.lookupIndices.map(n=>`#${n}`).join(', '):'—'}</b></div>)}</div>:<p className="muted">No feature records found.</p>}</div>
                <h4>LOOKUP DETAILS</h4>
                {lookups.map(l=><details className="ot-lookup" key={l.index}><summary><b>Lookup #{l.index}</b><span>{l.typeName}</span><code>TYPE {l.type}</code><code>FLAG 0x{Number(l.flag||0).toString(16).padStart(4,'0').toUpperCase()}</code><small>{l.subtableCount} subtable(s)</small></summary>
                  <div className="ot-lookup-body"><div className="ot-meta"><span>Lookup flag: <b>{lookupFlags(l.flag)}</b></span>{l.markFilteringSet!==null&&l.markFilteringSet!==undefined&&<span>Mark filtering set: <b>{l.markFilteringSet}</b></span>}</div>
                    {(l.subtables||[]).map(st=><div className="ot-subtable" key={st.subtableIndex}><h5>SUBTABLE {st.subtableIndex+1}</h5>{st.warning&&<p className="muted">{st.warning}</p>}
                      {st.substitutions?.length>0&&<div className="ot-data-list">{st.substitutions.map((r,i)=><div key={i}><code>{r.from}</code><span>→</span><b>{Array.isArray(r.to)?r.to.join(' + '):r.to??(r.alternates||[]).join(', ')}</b></div>)}</div>}
                      {st.ligatures?.length>0&&<div className="ot-data-list">{st.ligatures.map((r,i)=><div key={i}><code>{r.input}</code><span>→</span><b>{r.result}</b></div>)}</div>}
                      {st.positioning?.length>0&&<div className="ot-data-list">{st.positioning.map((r,i)=><div key={i}><code>{r.glyph}</code><span>adjust</span><b>{valueSummary(r.value)}</b></div>)}</div>}
                      {st.kerningPairs?.length>0&&<>
                        <div className="ot-pair-table"><div className="ot-pair-row head"><span>LEFT</span><span>RIGHT</span><span>VALUE 1 (X/Y PLACE · ADV)</span><span>VALUE 2</span></div>{st.kerningPairs.slice((pairPages[`${l.index}-${st.subtableIndex}`]||0)*100,(pairPages[`${l.index}-${st.subtableIndex}`]||0)*100+100).map((r,i)=><div className="ot-pair-row" key={`${r.left}-${r.right}-${i}`}><code>{r.left}</code><code>{r.right}</code><span>{valueSummary(r.value1)}</span><span>{valueSummary(r.value2)}</span></div>)}</div>
                        {st.kerningPairs.length>100&&<div className="ot-pair-pagination"><span>Showing {fmt((pairPages[`${l.index}-${st.subtableIndex}`]||0)*100+1)}–{fmt(Math.min(((pairPages[`${l.index}-${st.subtableIndex}`]||0)+1)*100,st.kerningPairs.length))} of {fmt(st.totalPairCount||st.kerningPairs.length)} pairs</span><button disabled={!pairPages[`${l.index}-${st.subtableIndex}`]} onClick={()=>setPairPages(p=>({...p,[`${l.index}-${st.subtableIndex}`]:Math.max(0,(p[`${l.index}-${st.subtableIndex}`]||0)-1)}))}>Previous</button><button disabled={(pairPages[`${l.index}-${st.subtableIndex}`]||0)>=Math.ceil(st.kerningPairs.length/100)-1} onClick={()=>setPairPages(p=>({...p,[`${l.index}-${st.subtableIndex}`]:(p[`${l.index}-${st.subtableIndex}`]||0)+1}))}>Next</button></div>}
                      </>}
                      {st.classPairMatrix&&<p className="muted">{st.classPairMatrix} · Class 1: {fmt(st.class1GlyphCount||0)} covered glyphs · Class 2 glyph universe: {fmt(st.class2GlyphCount||0)} · {fmt(st.totalPairCount||0)} expanded pairs{st.expansionTruncated?` (display capped at ${fmt(st.expansionLimit)})`:''}.</p>}
                      {!st.substitutions?.length&&!st.ligatures?.length&&!st.positioning?.length&&!st.kerningPairs?.length&&<p className="muted">{st.description||`Coverage: ${(st.coverage||[]).slice(0,30).join(', ')||'No simple records decoded'}`}</p>}
                    </div>)}
                  </div>
                </details>)}
                {!lookups.length&&data.present&&<p className="muted">No lookup records found.</p>}
              </section>})}
              <section className="ot-section"><div className="ot-section-head"><div><b>GDEF</b><small>Glyph Definition Table</small></div><span>{font.opentype.GDEF.present?'PRESENT':'NOT FOUND'}</span></div><p className="muted">GDEF classification and attachment metadata is not decoded in this release; presence is reported for reference.</p></section>
            </>}
          </div>}
          {tab==='variable' && <div className="variable-panel">
            <div className="ot-intro"><span>VARIABLE FONT LAB / AXIS INSPECTOR</span><small>Read-only font analysis · live browser specimen</small></div>
            {variableBusy && <div className="empty">Reading fvar, avar and STAT variation metadata…</div>}
            {!variableBusy && variableData && !variableData.isVariable && <div className="variable-empty"><b>STATIC FONT DETECTED</b><p>{variableData.message}</p><small>Variable fonts normally contain an fvar table defining one or more design axes.</small></div>}
            {!variableBusy && variableData?.isVariable && <>
              <div className="variable-summary">
                <div><strong>{variableData.axisCount}</strong><span>DESIGN AXES</span></div>
                <div><strong>{variableData.instanceCount}</strong><span>NAMED INSTANCES</span></div>
                <div><strong>{variableData.tables.gvar || variableData.tables.CFF2 ? 'YES' : '—'}</strong><span>GLYPH VARIATIONS</span></div>
                <div><strong>{variableData.tables.avar ? 'YES' : 'NO'}</strong><span>AVAR MAPPING</span></div>
              </div>
              <div className="variable-specimen">
                <div className="variable-section-heading"><div><b>LIVE AXIS PREVIEW</b><small>Move the sliders to test interpolation in the uploaded font.</small></div><button className="quality-export" onClick={()=>setAxisValues(Object.fromEntries(variableData.axes.map(a=>[a.tag,a.default])))}>RESET TO DEFAULT</button></div>
                <textarea className="variable-specimen-text" aria-label="Variable font specimen" value={previewText} onChange={e=>setPreviewText(e.target.value)} style={{fontFamily:'UploadedSpecimen, sans-serif',fontSize:`${previewSize}px`,fontVariationSettings:variationSettings || 'normal'}} />
                <div className="preview-controls"><span>SIZE</span><input type="range" min="20" max="120" value={previewSize} onChange={e=>setPreviewSize(Number(e.target.value))}/><b>{previewSize}px</b></div>
              </div>
              <div className="variable-section-heading"><div><b>DESIGN AXES</b><small>Values are expressed in the font's design-space coordinates.</small></div></div>
              <div className="variable-axis-list">{variableData.axes.map(axis=><article className="variable-axis" key={axis.tag}>
                <div className="variable-axis-title"><div><b>{axis.name}</b><code>{axis.tag}{axis.hidden?' · HIDDEN':''}</code></div><strong>{Number(axisValues[axis.tag] ?? axis.default).toLocaleString('en-US',{maximumFractionDigits:3})}</strong></div>
                <input type="range" min={axis.min} max={axis.max} step={(axis.max-axis.min)/1000 || 1} value={axisValues[axis.tag] ?? axis.default} onChange={e=>setAxisValues(v=>({...v,[axis.tag]:Number(e.target.value)}))}/>
                <div className="variable-axis-scale"><span>{axis.min}</span><span>DEFAULT {axis.default}</span><span>{axis.max}</span></div>
              </article>)}</div>
              <div className="variable-section-heading"><div><b>NAMED INSTANCES</b><small>Apply stored design-space coordinates from fvar.</small></div></div>
              {variableData.instances.length ? <div className="variable-instance-grid">{variableData.instances.map(instance=><button key={instance.index} onClick={()=>applyInstance(instance)} className="variable-instance"><b>{instance.name}</b><small>{variableData.axes.map(a=>`${a.tag} ${instance.coordinates?.[a.tag] ?? a.default}`).join(' · ')}</small></button>)}</div> : <p className="muted">No named instances are stored in this font.</p>}
              <div className="variable-section-heading"><div><b>VARIATION TABLES</b><small>Table presence and metadata inventory.</small></div></div>
              <div className="variable-table-grid">{Object.entries(variableData.tables).map(([tag,present])=><div key={tag}><code>{tag}</code><span className={present?'present':'absent'}>{present?'PRESENT':'NOT FOUND'}</span></div>)}</div>
              {variableData.statAxes?.length>0&&<div className="variable-stat"><b>STAT DESIGN AXES</b>{variableData.statAxes.map((axis,i)=><span key={`${axis.tag}-${i}`}>{axis.tag} — {axis.name} <small>ORDER {axis.ordering}</small></span>)}</div>}
              {Object.keys(variableData.avar || {}).length>0&&<div className="variable-avar"><b>AVAR NORMALIZATION MAP</b>{Object.entries(variableData.avar).map(([tag,points])=><div key={tag}><code>{tag}</code><span>{points.map(p=>`${p.from} → ${p.to}`).join('  ·  ')}</span></div>)}</div>}
              <p className="muted">{variableData.note} The preview depends on browser support for the font format and variation tables. This inspector does not modify or save axis values into the font file.</p>
            </>}
          </div>}
          {tab==='diagnostics' && <div className="diagnostics-panel">
            <div className="ot-intro"><span>FONT STRUCTURE & INTEGRITY</span><small>Read-only checks · original font is never modified</small></div>
            {diagnosticsBusy && <div className="empty">Checking table structure, checksums, encoding and glyph references…</div>}
            {!diagnosticsBusy && diagnostics && <>
              <div className="diagnostic-summary">
                <div><strong>{fmt(diagnostics.summary.passed)}</strong><span>Passed</span></div>
                <div><strong>{fmt(diagnostics.summary.warnings)}</strong><span>Warnings</span></div>
                <div><strong>{fmt(diagnostics.summary.errors)}</strong><span>Errors</span></div>
                <div><strong>{fmt(diagnostics.summary.info)}</strong><span>Info</span></div>
              </div>
              <div className="diagnostic-findings">{diagnostics.findings.map((f,i)=><article className={`diagnostic-finding ${f.severity}`} key={`${f.code}-${i}`}>
                <div><b>{f.code.replaceAll('_',' ')}</b><span>{f.severity.toUpperCase()}</span></div>
                <code>{f.location}</code><p>{f.message}</p>{f.recommendation&&<small>Recommendation: {f.recommendation}</small>}
              </article>)}</div>
              <p className="muted">Checks currently cover: {diagnostics.scope.join(' · ')}. A clean report means no issues were detected by these checks; it is not a certification of full OpenType conformance.</p>
            </>}
          </div>}
          {tab==='quality' && <div className="quality-panel">
            <div className="ot-intro"><span>FONT COMPLETENESS & QUALITY</span><button className="quality-export" onClick={exportQuality} disabled={!quality}>EXPORT JSON REPORT ↓</button></div>
            {qualityBusy && <div className="empty">Analyzing Unicode coverage and glyph metrics…</div>}
            {!qualityBusy && quality && <>
              <div className="quality-profile"><div><b>{quality.profile}</b><small>{quality.profileNote}</small></div><span>READ-ONLY ANALYSIS</span></div>
              <div className="quality-summary">
                <div><strong>{quality.summary.overallCoverage}%</strong><span>Overall profile coverage</span></div>
                <div><strong>{quality.summary.requiredPresent}/{quality.summary.requiredTotal}</strong><span>Core characters</span></div>
                <div><strong>{quality.summary.recommendedMissing}</strong><span>Recommended missing</span></div>
                <div><strong>{quality.summary.missingMetrics}</strong><span>Missing metrics</span></div>
              </div>
              <div className="quality-progress"><div style={{width:`${quality.summary.overallCoverage}%`}}/></div>
              <div className="quality-groups">{quality.groups.map(group=><article className="quality-group" key={group.name}>
                <div className="quality-group-head"><div><b>{group.name}</b><small>{group.priority==='required'?'CORE / REQUIRED PROFILE':'EXTENDED / RECOMMENDED'}</small></div><strong>{group.present}/{group.total}</strong></div>
                <div className="quality-group-bar"><div style={{width:`${group.coverage}%`}}/></div>
                <div className="quality-character-grid">{group.presentCharacters.map(ch=><span className="present" title={`U+${ch.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')} · ${ch}`} key={`${group.name}-${ch}`}>{ch}</span>)}{group.missingCharacters.map(ch=><span className="missing" title={`Missing · U+${ch.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')}`} key={`${group.name}-${ch}`}>{ch}</span>)}</div>
                {group.missingCount>0&&<p className="quality-missing">Missing: {group.missingCharacters.map(ch=>`U+${ch.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')} ${ch}`).join(' · ')}</p>}
              </article>)}</div>
              <div className="quality-findings"><h3>QUALITY FINDINGS</h3>{quality.findings.length?quality.findings.map((f,i)=><article className={`diagnostic-finding ${f.severity}`} key={`${f.code}-${i}`}><div><b>{f.code.replaceAll('_',' ')}</b><span>{f.severity.toUpperCase()}</span></div><code>{f.location}</code><p>{f.message}</p>{f.recommendation&&<small>Recommendation: {f.recommendation}</small>}</article>):<div className="diagnostics-clean">No missing characters or metric issues were found in this profile.</div>}</div>
              <p className="muted">Coverage is based on Unicode cmap mappings, not glyph appearance. A mapped character can still have an incorrect or unfinished outline. The profile is a practical Latin baseline, not an official marketplace approval test.</p>
            </>}
          </div>}
          {tab==='tables' && <div className="table-list"><div className="table-row table-header"><span>TABLE TAG</span><span>DATA SIZE</span></div>{font.tables.map(t=><div className="table-row" key={t.tag}><code>{t.tag}</code><span>{fmt(t.length)} bytes</span></div>)}</div>}
          {tab==='unmapped' && <div className="unmapped-list"><p className="muted">Glyphs in the glyph order that are not mapped to a Unicode character in the best cmap.</p>{font.unmappedGlyphs.length ? font.unmappedGlyphs.map((g,i)=><code key={`${g}-${i}`}>{g}</code>) : <div className="empty">All glyphs in the glyph order are mapped in the best cmap.</div>}</div>}
        </section>
        <button className="close-font" onClick={()=>{setFont(null);setSelected(null);setGlyphDetail(null)}}>Close font session <X size={14}/></button>
      </>}

      <footer><span>© 2026 ANGHSTUDIO</span><span>OPEN SOURCE / MIT LICENSE</span><span>MADE FOR TYPE PEOPLE.</span></footer>
    </main>
  </div>
}

function segmentPath(segment) { const [x,y] = segment.start; const [ex,ey] = segment.end; if (segment.type === 'line') return `M${x} ${y} L${ex} ${ey}`; if (segment.type === 'quadratic') { const [c] = segment.controls; return `M${x} ${y} Q${c[0]} ${c[1]} ${ex} ${ey}` } const [c1,c2] = segment.controls; return `M${x} ${y} C${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${ex} ${ey}` }

function lookupFlags(flag) { const bits=[[1,'RightToLeft'],[2,'IgnoreBaseGlyphs'],[4,'IgnoreLigatures'],[8,'IgnoreMarks'],[16,'UseMarkFilteringSet']]; const names=bits.filter(([bit])=>flag&bit).map(([,name])=>name); return names.length?names.join(' · '):'None' }
function valueSummary(v) { if(!v) return '—'; return `XPlace ${v.XPlacement||0} · YPlace ${v.YPlacement||0} · XAdv ${v.XAdvance||0} · YAdv ${v.YAdvance||0}` }
function Stat({icon,label,value}) { return <div className="stat"><div className="stat-icon">{icon}</div><span>{label}</span><strong>{value}</strong></div> }
function featureName(tag) { return ({liga:'Standard ligatures',clig:'Contextual ligatures',calt:'Contextual alternates',kern:'Kerning',mark:'Mark-to-base positioning',mkmk:'Mark-to-mark positioning',curs:'Cursive attachment',ccmp:'Glyph composition / decomposition',locl:'Localized forms',salt:'Stylistic alternates',swsh:'Swash',frac:'Fractions',ordn:'Ordinals',numr:'Numerators',dnom:'Denominators',sups:'Superscripts',subs:'Subscripts'})[tag] || 'OpenType layout feature' }

createRoot(document.getElementById('root')).render(<App />)
