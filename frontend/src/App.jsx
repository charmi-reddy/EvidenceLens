import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, ArrowDown, ArrowRight, BadgeCheck, CheckCircle2, ChevronRight,
  CircleHelp, Clock3, Eye, FileImage, ImagePlus, LoaderCircle, LockKeyhole,
  RefreshCw, ShieldCheck, Sparkles, X,
} from 'lucide-react';

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const MAX_BYTES = 10 * 1024 * 1024;
const MAX_CAPTION = 5000;
const VALID_STATUSES = ['supported', 'contradicted', 'insufficient_evidence'];
const STATUS_META = {
  supported: { label: 'Supported', icon: CheckCircle2, tone: 'supported', short: 'Visible evidence aligns' },
  contradicted: { label: 'Contradicted', icon: AlertCircle, tone: 'contradicted', short: 'Visible evidence conflicts' },
  insufficient_evidence: { label: 'Insufficient evidence', icon: CircleHelp, tone: 'insufficient', short: 'Image cannot establish this' },
};

function formatBytes(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function validateResult(data) {
  if (!data || typeof data !== 'object' || !VALID_STATUSES.includes(data.overall_status) || !Array.isArray(data.claims) || !Array.isArray(data.limitations)) {
    throw new Error('The server returned a response we could not read. Please try again.');
  }
  for (const claim of data.claims) {
    if (!claim || typeof claim.text !== 'string' || !VALID_STATUSES.includes(claim.status) || typeof claim.evidence !== 'string' || typeof claim.explanation !== 'string' || typeof claim.confidence !== 'string') {
      throw new Error('The server returned an incomplete claim result. Please try again.');
    }
  }
  return data;
}

function BrandMark() {
  return <div className="brand-mark" aria-hidden="true"><Eye size={20} strokeWidth={2.3} /><span /></div>;
}

function Pill({ status, children }) {
  const meta = STATUS_META[status];
  if (!meta) return null;
  const Icon = meta.icon;
  return <span className={`status-pill ${meta.tone}`}><Icon size={15} strokeWidth={2.2} />{children || meta.label}</span>;
}

function App() {
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState('');
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);
  const controller = useRef(null);

  useEffect(() => () => {
    if (controller.current) controller.current.abort();
  }, []);

  useEffect(() => {
    if (!file) { setPreview(''); return undefined; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const counts = useMemo(() => {
    if (!result) return null;
    return result.claims.reduce((acc, claim) => ({ ...acc, [claim.status]: acc[claim.status] + 1 }), {
      supported: 0, contradicted: 0, insufficient_evidence: 0,
    });
  }, [result]);

  function clearAnalysis() { setResult(null); setError(''); }

  function acceptFile(candidate) {
    if (!candidate) return;
    setError('');
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) {
      setError('Choose a JPEG, PNG, or WEBP image.');
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setError('This image is larger than 10 MB. Choose a smaller file.');
      return;
    }
    if (candidate.size === 0) {
      setError('That file is empty. Choose another image.');
      return;
    }
    setFile(candidate);
    clearAnalysis();
  }

  function removeImage() {
    setFile(null);
    if (fileInput.current) fileInput.current.value = '';
    clearAnalysis();
  }

  async function analyze(event) {
    event?.preventDefault();
    if (loading) return;
    if (!file) { setError('Add an image before analyzing.'); return; }
    if (!caption.trim()) { setError('Add a caption or a few claims to check.'); return; }
    if (caption.length > MAX_CAPTION) { setError('Your caption is over the 5,000 character limit.'); return; }

    setError('');
    setResult(null);
    setLoading(true);
    const aborter = new AbortController();
    controller.current = aborter;
    const timer = window.setTimeout(() => aborter.abort(), 70_000);
    try {
      const payload = new FormData();
      payload.append('image', file);
      payload.append('caption', caption.trim());
      const response = await fetch(`${API_ROOT}/analyze`, {
        method: 'POST', body: payload, signal: aborter.signal,
      });
      let body;
      try { body = await response.json(); }
      catch { throw new Error('The backend returned an unreadable response. Please try again.'); }
      if (!response.ok) {
        const message = body?.error?.message || `Analysis could not be completed (HTTP ${response.status}).`;
        if (response.status === 502 || response.status === 503) {
          throw new Error(`${message} Your image and caption are still here—retry in a moment.`);
        }
        throw new Error(message);
      }
      setResult(validateResult(body));
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Analysis took too long or was cancelled. Check your connection and retry.');
      } else if (err instanceof TypeError) {
        setError(`Could not reach the EvidenceLens API at ${API_ROOT}. Make sure the Flask backend is running, then retry.`);
      } else {
        setError(err.message || 'Something went wrong. Please try again.');
      }
    } finally {
      window.clearTimeout(timer);
      controller.current = null;
      setLoading(false);
    }
  }

  const overall = result ? STATUS_META[result.overall_status] : null;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="EvidenceLens home">
          <BrandMark /><span>evidence<span className="brand-accent">lens</span></span>
        </a>
        <div className="topbar-right">
          <span className="topbar-tag"><span className="live-dot" />Multimodal claim check</span>
          <span className="topbar-divider" />
          <span className="club-label">Women in AI Research Club</span>
        </div>
      </header>

      <main id="top" className="main-wrap">
        <section className="intro-row" aria-labelledby="page-title">
          <div className="intro-copy">
            <div className="eyebrow"><span className="eyebrow-line" />A clearer look at what’s shown</div>
            <h1 id="page-title">Does the image<br className="desktop-break" /> support the story?</h1>
            <p className="intro-description">Pair a picture with its caption. EvidenceLens checks each claim against visible details—and tells you when an image can’t give us the answer.</p>
          </div>
          <div className="principle-card">
            <div className="principle-icon"><ShieldCheck size={20} /></div>
            <div><strong>Evidence, not assumptions</strong><p>A match is not proof of authenticity.</p></div>
          </div>
        </section>

        <div className="workspace-grid">
          <section className="input-panel panel" aria-labelledby="input-heading">
            <div className="panel-heading">
              <div><span className="step-label">01 <span /> INPUT</span><h2 id="input-heading">Add your image &amp; text</h2></div>
              <span className="private-note"><LockKeyhole size={13} />Private to this check</span>
            </div>

            <div className="field-label-row"><label htmlFor="image-file">Image</label><span>JPEG, PNG, WEBP · up to 10 MB</span></div>
            <input ref={fileInput} id="image-file" className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={e => acceptFile(e.target.files?.[0])} />
            {!file ? (
              <button type="button" className={`upload-zone ${dragging ? 'is-dragging' : ''}`} onClick={() => fileInput.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => { e.preventDefault(); setDragging(false); acceptFile(e.dataTransfer.files?.[0]); }}
                aria-label="Choose or drop an image">
                <span className="upload-icon"><ImagePlus size={22} /></span>
                <span className="upload-title">Drop an image here, or <span>browse</span></span>
                <span className="upload-subtitle">A clear image helps us point to specific evidence</span>
              </button>
            ) : (
              <div className="preview-card">
                <img src={preview} alt="Preview of the image you selected" />
                <div className="preview-overlay"><span className="preview-file"><FileImage size={15} />{file.name}<small>{formatBytes(file.size)}</small></span>
                  <button type="button" className="remove-image" onClick={removeImage} aria-label="Remove selected image"><X size={17} /></button></div>
              </div>
            )}

            <div className="field-label-row caption-label"><label htmlFor="caption">Caption or claims</label><span>We’ll separate it into checkable claims</span></div>
            <textarea id="caption" value={caption} maxLength={MAX_CAPTION} onChange={e => { setCaption(e.target.value); clearAnalysis(); }} placeholder="e.g. A red bicycle is parked beside a café in Paris on a rainy afternoon." rows={5} />
            <div className="textarea-footer"><span>Tip: include the exact wording you want checked.</span><span className={caption.length > 4700 ? 'char-count near-limit' : 'char-count'}>{caption.length.toLocaleString()} / 5,000</span></div>

            {error && <div className="error-banner" role="alert"><AlertCircle size={18} /><div><strong>Couldn’t complete the check</strong><p>{error}</p>{!loading && file && caption.trim() && <button className="inline-retry" onClick={analyze}>Try again <ArrowRight size={13} /></button>}</div></div>}

            <button className="analyze-button" type="button" disabled={loading} onClick={analyze}>
              {loading ? <><LoaderCircle className="spin" size={18} />Comparing image &amp; claims…</> : <><Sparkles size={17} />Analyze consistency<ArrowRight size={16} className="button-arrow" /></>}
            </button>
            <div className="secure-footnote"><LockKeyhole size={12} />Your image is analyzed for this request and isn’t used to prove authenticity.</div>
          </section>

          <section className={`results-panel panel ${result ? 'has-results' : ''}`} aria-labelledby="results-heading" aria-live="polite">
            <div className="panel-heading results-heading">
              <div><span className="step-label">02 <span /> FINDINGS</span><h2 id="results-heading">Claim-by-claim results</h2></div>
              {result && <span className="result-count">{result.claims.length} {result.claims.length === 1 ? 'claim' : 'claims'}</span>}
            </div>
            {!result && !loading ? (
              <div className="empty-state">
                <div className="empty-illustration" aria-hidden="true"><span className="empty-picture"><span className="sun" /><span className="hill hill-a" /><span className="hill hill-b" /></span><span className="empty-check"><ArrowDown size={16} /></span></div>
                <h3>Your evidence will appear here</h3>
                <p>Upload an image and add a caption to see each claim evaluated with visual evidence.</p>
                <div className="empty-steps"><span><i>1</i> Add image</span><ChevronRight size={14} /><span><i>2</i> Add caption</span><ChevronRight size={14} /><span><i>3</i> Review</span></div>
              </div>
            ) : loading ? (
              <div className="loading-state" role="status"><div className="loading-art"><span className="loading-ring" /><Eye size={26} /></div><h3>Looking closely…</h3><p>Separating claims and comparing them with what’s visible.</p><div className="loading-track"><span /></div><small>This can take a few moments</small></div>
            ) : (
              <div className="results-content">
                <div className={`overall-card ${STATUS_META[result.overall_status]?.tone || 'insufficient'}`}>
                  <div className="overall-main"><span className="overall-icon"><BadgeCheck size={19} /></span><div><span className="overall-kicker">OVERALL ASSESSMENT</span><strong>{overall?.label || 'Review results'}</strong></div></div>
                  <div className="summary-counts" aria-label="Verdict counts">
                    <span className="count-supported"><i />{counts.supported} supported</span>
                    <span className="count-contradicted"><i />{counts.contradicted} contradicted</span>
                    <span className="count-insufficient"><i />{counts.insufficient_evidence} unclear</span>
                  </div>
                </div>

                <div className="claims-list">
                  {result.claims.map((claim, index) => {
                    const meta = STATUS_META[claim.status];
                    return <article className={`claim-card ${meta?.tone || ''}`} key={`${index}-${claim.text}`}>
                      <div className="claim-topline"><span className="claim-index">CLAIM {String(index + 1).padStart(2, '0')}</span><Pill status={claim.status} /></div>
                      <h3>“{claim.text}”</h3>
                      <div className="claim-detail evidence-detail"><span className="detail-icon"><Eye size={15} /></span><div><span className="detail-label">WHAT’S VISIBLE</span><p>{claim.evidence}</p></div></div>
                      <div className="claim-detail explanation-detail"><span className="detail-icon"><ArrowRight size={14} /></span><div><span className="detail-label">WHY THIS VERDICT</span><p>{claim.explanation}</p></div></div>
                      <div className="claim-footer"><span className="confidence"><span className={`confidence-dot confidence-${['low','medium','high'].includes(claim.confidence.toLowerCase()) ? claim.confidence.toLowerCase() : 'low'}`} />{['low','medium','high'].includes(claim.confidence.toLowerCase()) ? claim.confidence[0].toUpperCase() + claim.confidence.slice(1) : 'Unrated'} confidence</span><span className="confidence-note">visual judgment</span></div>
                    </article>;
                  })}
                </div>

                {result.limitations.length > 0 && <div className="limitations-card"><div className="limitations-heading"><Clock3 size={15} /><strong>Limits of the image</strong></div><ul>{result.limitations.map((item, i) => <li key={`${i}-${item}`}>{item}</li>)}</ul><div className="authenticity-note"><ShieldCheck size={14} /><span>Visual consistency alone cannot prove a photo is authentic.</span></div></div>}
                <button type="button" className="reset-button" onClick={() => { setResult(null); setError(''); }}><RefreshCw size={14} />Start a new check</button>
              </div>
            )}
          </section>
        </div>

        <section className="legend-strip" aria-label="Verdict guide">
          <div className="legend-intro"><span className="legend-spark"><Sparkles size={15} /></span><span><strong>Three possible verdicts</strong><small>We keep uncertainty visible.</small></span></div>
          <div className="legend-item"><Pill status="supported" /><span>Visible details align</span></div>
          <div className="legend-item"><Pill status="contradicted" /><span>Clear visual conflict</span></div>
          <div className="legend-item"><Pill status="insufficient_evidence" /><span>Image can’t tell us</span></div>
        </section>

        <footer className="page-footer"><span>EvidenceLens <i>·</i> Smooth Operatorsz</span><span><ShieldCheck size={13} />A consistency check, not an authenticity verdict</span></footer>
      </main>
    </div>
  );
}

export default App;
