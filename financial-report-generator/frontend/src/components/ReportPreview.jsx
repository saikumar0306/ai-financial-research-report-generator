/**
 * ReportPreview.jsx — PDF report preview panel with download button.
 *
 * Uses <object> tag for PDF inline rendering (most reliable cross-browser),
 * falls back to <iframe> for HTML content (legacy reports).
 */

import React, { useState } from 'react'
import { Download, Eye, ExternalLink, RefreshCw, BarChart3, CheckCircle, FileWarning } from 'lucide-react'

export default function ReportPreview({
  previewUrl,
  downloadUrl,
  filename,
  mode,
  companyName,
  chartsGenerated = [],
  onReset,
}) {
  const [objectLoaded, setObjectLoaded] = useState(false)
  const [objectError, setObjectError] = useState(false)

  const isPdf = mode === 'pdf'

  return (
    <div className="animate-fade-in-up space-y-4">

      {/* ── Success header ──────────────────────────────────────── */}
      <div className="glass-card p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-green-500/10 border border-green-500/20
                          flex items-center justify-center flex-shrink-0">
            <CheckCircle className="w-5 h-5 text-green-400" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-white truncate">
              {companyName} — Research Report
            </p>
            <p className="text-xs text-slate-500">
              PDF report · {chartsGenerated.length} charts generated
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 flex-shrink-0 flex-wrap">
          <a
            id="open-preview-link"
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold
                       bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300
                       transition-all duration-200"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open
          </a>

          <a
            id="download-report-btn"
            href={downloadUrl}
            download={filename}
            className="btn-gold flex items-center gap-1.5 !px-4 !py-2 text-xs"
          >
            <Download className="w-3.5 h-3.5" />
            Download PDF
          </a>

          <button
            id="generate-new-btn"
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold
                       bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400
                       transition-all duration-200"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            New
          </button>
        </div>
      </div>

      {/* ── Charts summary chips ────────────────────────────────── */}
      {chartsGenerated.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {chartsGenerated.map((c) => (
            <span
              key={c}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full
                         bg-navy-600/20 border border-navy-500/20 text-xs text-navy-200"
            >
              <BarChart3 className="w-3 h-3" />
              {c.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())} Chart
            </span>
          ))}
        </div>
      )}

      {/* ── PDF / HTML Preview ──────────────────────────────────── */}
      <div className="glass-card overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
          <Eye className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-400">Report Preview (PDF)</span>
          {!objectLoaded && !objectError && (
            <span className="text-xs text-slate-600 ml-auto">Loading preview…</span>
          )}
        </div>

        <div className="relative" style={{ height: '650px' }}>
          {/* Loading overlay */}
          {!objectLoaded && !objectError && (
            <div className="absolute inset-0 flex items-center justify-center bg-navy-800/50 z-10">
              <div className="text-center">
                <div
                  className="w-8 h-8 rounded-full border-2 border-navy-600/30 border-t-gold-500 mx-auto mb-2"
                  style={{ animation: 'spinRing 1s linear infinite' }}
                />
                <p className="text-xs text-slate-500">Loading PDF report…</p>
              </div>
            </div>
          )}

          {/* Error fallback – open in new tab */}
          {objectError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-navy-900/80 z-10 p-6">
              <FileWarning className="w-10 h-10 text-gold-400 opacity-80" />
              <p className="text-sm text-slate-300 text-center max-w-xs">
                Your browser blocked inline PDF rendering. Click <strong>Open</strong> to view it in a new tab, or use <strong>Download PDF</strong>.
              </p>
              <div className="flex gap-3">
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-gold flex items-center gap-2 text-xs !px-4 !py-2"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open PDF in new tab
                </a>
                <a
                  href={downloadUrl}
                  download={filename}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold
                             bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300
                             transition-all duration-200"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </a>
              </div>
            </div>
          )}

          {/* PDF embed via object tag */}
          <object
            id="report-preview-object"
            data={previewUrl}
            type="application/pdf"
            width="100%"
            height="100%"
            onLoad={() => { setObjectLoaded(true); setObjectError(false) }}
            onError={() => setObjectError(true)}
            style={{ display: 'block', border: 'none', background: '#0f172a' }}
          >
            {/* Fallback: iframe for HTML reports or browsers with no PDF plugin */}
            <iframe
              id="report-preview-iframe"
              src={previewUrl}
              title={`${companyName} Financial Research Report`}
              style={{ width: '100%', height: '100%', border: 'none', background: '#0f172a' }}
              onLoad={() => { setObjectLoaded(true); setObjectError(false) }}
              onError={() => setObjectError(true)}
            />
          </object>
        </div>
      </div>

    </div>
  )
}

