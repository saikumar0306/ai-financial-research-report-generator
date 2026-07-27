/**
 * UploadForm.jsx — Main upload form with drag-and-drop, company name input,
 * and the Generate Report button.
 */

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  UploadCloud, FileText, FileSpreadsheet, X, Building2, ArrowRight, AlertCircle
} from 'lucide-react'

const ACCEPT = {
  'application/pdf':  ['.pdf'],
  'text/plain':       ['.txt'],
  'text/csv':         ['.csv'],
  'application/vnd.ms-excel': ['.csv'],
}

const FILE_ICONS = {
  pdf: <FileText className="w-5 h-5 text-red-400" />,
  txt: <FileText className="w-5 h-5 text-blue-400" />,
  csv: <FileSpreadsheet className="w-5 h-5 text-green-400" />,
}

function getFileExt(name) {
  return name.split('.').pop()?.toLowerCase() || 'file'
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// ─────────────────────────────────────────────────────────────────────────────

export default function UploadForm({ onSubmit, isLoading }) {
  const [file, setFile]              = useState(null)
  const [companyName, setCompanyName] = useState('')
  const [fileError, setFileError]    = useState('')

  const onDrop = useCallback((accepted, rejected) => {
    setFileError('')
    if (rejected.length > 0) {
      const reason = rejected[0]?.errors?.[0]?.message || 'Invalid file'
      setFileError(`File rejected: ${reason}`)
      return
    }
    if (accepted.length > 0) {
      setFile(accepted[0])
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20 MB
    disabled: isLoading,
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) { setFileError('Please upload a document.'); return }
    if (!companyName.trim()) return
    onSubmit(file, companyName.trim())
  }

  const removeFile = (e) => {
    e.stopPropagation()
    setFile(null)
    setFileError('')
  }

  const ext = file ? getFileExt(file.name) : null
  const canSubmit = file && companyName.trim() && !isLoading

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* ── Company Name ──────────────────────────────────────────── */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Company Name
        </label>
        <div className="relative">
          <Building2
            className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
            strokeWidth={1.8}
          />
          <input
            id="company-name-input"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Reliance Industries Ltd."
            disabled={isLoading}
            required
            className="input-field pl-10"
          />
        </div>
      </div>

      {/* ── File Drop Zone ────────────────────────────────────────── */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Financial Document
        </label>

        <div
          {...getRootProps()}
          id="file-drop-zone"
          className={`drop-zone p-6 transition-all ${isDragActive ? 'dragging' : ''} ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} id="file-input" />

          {file ? (
            /* ── File preview chip ─── */
            <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
              <div className="p-2 rounded-lg bg-white/5">
                {FILE_ICONS[ext] || <FileText className="w-5 h-5 text-slate-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{file.name}</p>
                <p className="text-xs text-slate-500">
                  {ext?.toUpperCase()} · {formatBytes(file.size)}
                </p>
              </div>
              {!isLoading && (
                <button
                  type="button"
                  onClick={removeFile}
                  id="remove-file-btn"
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              )}
            </div>
          ) : (
            /* ── Empty drop zone ──── */
            <div className="text-center py-4">
              <UploadCloud
                className={`w-12 h-12 mx-auto mb-3 transition-colors ${
                  isDragActive ? 'text-gold-400' : 'text-slate-600'
                }`}
                strokeWidth={1.4}
              />
              <p className={`text-sm font-medium mb-1 ${isDragActive ? 'text-gold-400' : 'text-slate-400'}`}>
                {isDragActive ? 'Drop it here!' : 'Drag & drop your document'}
              </p>
              <p className="text-xs text-slate-600 mb-3">
                or click to browse your files
              </p>
              <div className="flex justify-center gap-2">
                {['PDF', 'TXT', 'CSV'].map((fmt) => (
                  <span
                    key={fmt}
                    className="px-2.5 py-0.5 rounded-full text-[10px] font-bold
                               bg-white/5 border border-white/10 text-slate-500
                               uppercase tracking-wider"
                  >
                    {fmt}
                  </span>
                ))}
              </div>
              <p className="text-[10px] text-slate-700 mt-2">Max 20 MB</p>
            </div>
          )}
        </div>

        {/* ── File error ─── */}
        {fileError && (
          <div className="flex items-center gap-2 mt-2 text-red-400 text-xs">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{fileError}</span>
          </div>
        )}
      </div>

      {/* ── Submit Button ─────────────────────────────────────────── */}
      <button
        type="submit"
        id="generate-report-btn"
        disabled={!canSubmit}
        className="btn-primary w-full flex items-center justify-center gap-3 text-sm"
      >
        {isLoading ? (
          <>
            <div
              className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white"
              style={{ animation: 'spinRing 0.8s linear infinite' }}
            />
            <span>Generating…</span>
          </>
        ) : (
          <>
            <span>Generate Report</span>
            <ArrowRight className="w-4 h-4" strokeWidth={2.5} />
          </>
        )}
      </button>

    </form>
  )
}
