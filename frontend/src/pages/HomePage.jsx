/**
 * HomePage.jsx — The main landing page assembling all components.
 *
 * Layout:
 *   - Animated header with logo + nav
 *   - Hero section with tagline
 *   - Upload form card (left)
 *   - Progress indicator + status (right/below during loading)
 *   - Report preview (full width, after generation)
 *   - Feature strip footer
 */

import React, { useState } from 'react'
import {
  TrendingUp, Zap, Shield, BarChart2, FileSearch, Bot,
  ChevronRight, Github, Star
} from 'lucide-react'
import UploadForm from '../components/UploadForm'
import ProgressIndicator from '../components/ProgressIndicator'
import LoadingSpinner from '../components/LoadingSpinner'
import ReportPreview from '../components/ReportPreview'
import { useReportGenerator } from '../hooks/useReportGenerator'

// ── Feature cards ─────────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: <Bot className="w-5 h-5" />,
    title: 'Gemini AI Extraction',
    desc: 'Structured financial JSON from any document',
    color: 'from-blue-500/10 to-purple-500/10 border-blue-500/15',
  },
  {
    icon: <BarChart2 className="w-5 h-5" />,
    title: 'Auto Chart Generation',
    desc: 'Revenue, EBITDA & Margin trend charts',
    color: 'from-gold-500/10 to-orange-500/10 border-gold-500/15',
  },
  {
    icon: <FileSearch className="w-5 h-5" />,
    title: 'Geojit-Style Reports',
    desc: 'Professional equity research layout',
    color: 'from-green-500/10 to-teal-500/10 border-green-500/15',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: 'PDF Export',
    desc: 'Download production-ready PDF reports',
    color: 'from-red-500/10 to-pink-500/10 border-red-500/15',
  },
]

// ── Step description messages ─────────────────────────────────────────────────
const STATUS_MESSAGES = {
  uploading:  'Reading and parsing your document…',
  extracting: 'Google Gemini is extracting financial data…',
  generating: 'Building charts and rendering report…',
}

// ─────────────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const {
    status, currentStep, uploadProgress, isLoading,
    reportFilename, reportMode, error, chartsGenerated,
    previewUrl, downloadUrl,
    generate, reset, STEPS,
    extractedData,
  } = useReportGenerator()

  const [submittedCompany, setSubmittedCompany] = useState('')

  const handleSubmit = async (file, companyName) => {
    setSubmittedCompany(companyName)
    await generate(file, companyName)
  }

  const handleReset = () => {
    setSubmittedCompany('')
    reset()
  }

  const isDone   = status === 'done'
  const isError  = status === 'error'
  const isIdle   = status === 'idle'

  // ── Recommendation badge class ────────────────────────────────────────────
  const rec = extractedData?.recommendation?.toUpperCase() || ''
  const recClass = {
    BUY:        'rec-buy',
    ACCUMULATE: 'rec-accumulate',
    HOLD:       'rec-hold',
    REDUCE:     'rec-reduce',
    SELL:       'rec-sell',
  }[rec] || 'rec-default'

  return (
    <div className="min-h-screen flex flex-col relative">

      {/* ── Background orbs ─── */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* ============================================================
          HEADER
      ============================================================ */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-navy-500 to-navy-700
                          flex items-center justify-center shadow-lg shadow-navy-900/50">
            <TrendingUp className="w-5 h-5 text-gold-400" strokeWidth={2.5} />
          </div>
          <div>
            <span className="text-base font-black text-white tracking-tight">Bull</span>
            <span className="text-base font-black text-gold-gradient tracking-tight"> AI</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
            <Zap className="w-3.5 h-3.5 text-gold-500" />
            Powered by Gemini
          </span>
          <div className="flex items-center gap-1 px-3 py-1.5 rounded-full
                          bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-semibold">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Live
          </div>
        </div>
      </header>

      {/* ============================================================
          MAIN CONTENT
      ============================================================ */}
      <main className="relative z-10 flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-10">

        {/* ── Hero ──────────────────────────────────────────────── */}
        <div className="text-center mb-10 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          bg-gold-500/10 border border-gold-500/20 text-gold-400
                          text-xs font-semibold mb-4">
            <Star className="w-3.5 h-3.5" />
            AI-Powered Equity Research
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white mb-4 leading-tight">
            Generate Professional
            <span className="block text-gold-gradient">Financial Reports</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto">
            Upload any financial document — PDF, CSV, or TXT — and let Google Gemini AI
            extract, analyse, and generate a Geojit-style equity research report instantly.
          </p>
        </div>

        {/* ── Upload Form + Status panel ─────────────────────────── */}
        {!isDone && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">

            {/* Upload form */}
            <div className="lg:col-span-3 glass-card p-6 animate-scale-in">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-5 flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-gold-400" />
                Upload Document
              </h2>
              <UploadForm onSubmit={handleSubmit} isLoading={isLoading} />
            </div>

            {/* Status / instructions panel */}
            <div className="lg:col-span-2 flex flex-col gap-4">

              {/* Progress (during loading) */}
              {isLoading && (
                <div className="glass-card p-6 animate-scale-in">
                  <ProgressIndicator
                    steps={STEPS}
                    currentStep={currentStep}
                    status={status}
                  />
                  <div className="mt-6">
                    <LoadingSpinner message={STATUS_MESSAGES[status] || 'Processing…'} />
                  </div>
                  {status === 'uploading' && uploadProgress > 0 && (
                    <div className="mt-4">
                      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                        <span>Upload Progress</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${uploadProgress}%`,
                            background: 'linear-gradient(90deg, #1E3A5F, #C8962A)',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error state */}
              {isError && (
                <div className="glass-card p-5 border border-red-500/20 animate-scale-in">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-red-400 text-sm">!</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-red-400 mb-1">Error</p>
                      <p className="text-xs text-slate-400 leading-relaxed">{error}</p>
                    </div>
                  </div>
                  <button
                    onClick={handleReset}
                    className="mt-4 text-xs text-slate-400 hover:text-white transition-colors underline"
                  >
                    Try again
                  </button>
                </div>
              )}

              {/* How it works (idle) */}
              {(isIdle || isError) && (
                <div className="glass-card p-5 animate-fade-in-up">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                    How it works
                  </p>
                  {[
                    ['1', 'Upload Document', 'PDF, TXT, or CSV financial report'],
                    ['2', 'AI Extraction',   'Gemini extracts structured JSON data'],
                    ['3', 'Chart Generation','Revenue, EBITDA & margin charts'],
                    ['4', 'Download PDF',    'Professional Geojit-style report'],
                  ].map(([num, title, desc]) => (
                    <div key={num} className="flex items-start gap-3 mb-3 last:mb-0">
                      <div className="w-6 h-6 rounded-full bg-navy-600/50 border border-navy-500/30
                                      flex items-center justify-center text-[10px] font-bold text-gold-400 flex-shrink-0">
                        {num}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">{title}</p>
                        <p className="text-[11px] text-slate-500">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Supported formats */}
              {(isIdle || isError) && (
                <div className="glass-card p-4 animate-fade-in-up">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                    Supported Formats
                  </p>
                  <div className="flex gap-2">
                    {[
                      ['PDF', 'text-red-400 bg-red-500/10 border-red-500/20'],
                      ['TXT', 'text-blue-400 bg-blue-500/10 border-blue-500/20'],
                      ['CSV', 'text-green-400 bg-green-500/10 border-green-500/20'],
                    ].map(([fmt, cls]) => (
                      <div key={fmt}
                        className={`flex-1 text-center py-2 rounded-lg border text-xs font-bold ${cls}`}>
                        {fmt}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </div>
        )}

        {/* ── Extracted data summary (shown during generation) ───── */}
        {extractedData && !isDone && (
          <div className="glass-card p-4 mb-6 animate-fade-in-up">
            <div className="flex flex-wrap gap-3 text-xs">
              <span className="text-slate-500">Extracted:</span>
              {extractedData.recommendation && extractedData.recommendation !== 'Not Available' && (
                <span className={`px-2.5 py-0.5 rounded-full font-bold ${recClass}`}>
                  {extractedData.recommendation}
                </span>
              )}
              {extractedData.industry && extractedData.industry !== 'Not Available' && (
                <span className="text-slate-400">{extractedData.industry}</span>
              )}
              {extractedData.current_price && extractedData.current_price !== 'Not Available' && (
                <span className="text-slate-400">CMP: {extractedData.current_price}</span>
              )}
              {extractedData.target_price && extractedData.target_price !== 'Not Available' && (
                <span className="text-gold-400 font-semibold">Target: {extractedData.target_price}</span>
              )}
            </div>
          </div>
        )}

        {/* ── Report Preview (done state) ────────────────────────── */}
        {isDone && (
          <ReportPreview
            previewUrl={previewUrl}
            downloadUrl={downloadUrl}
            filename={reportFilename}
            mode={reportMode}
            companyName={submittedCompany}
            chartsGenerated={chartsGenerated}
            onReset={handleReset}
          />
        )}

        {/* ── Feature strip ──────────────────────────────────────── */}
        {(isIdle || isError) && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className={`glass-card p-4 border bg-gradient-to-br ${f.color} animate-fade-in-up`}
              >
                <div className="text-gold-400 mb-2">{f.icon}</div>
                <p className="text-xs font-semibold text-white mb-1">{f.title}</p>
                <p className="text-[11px] text-slate-500">{f.desc}</p>
              </div>
            ))}
          </div>
        )}

      </main>

      {/* ============================================================
          FOOTER
      ============================================================ */}
      <footer className="relative z-10 border-t border-white/5 py-4 px-6
                         flex flex-col sm:flex-row items-center justify-between gap-2">
        <p className="text-xs text-slate-600">
          © 2024 Bull AI · Financial Research Report Generator
        </p>
        <p className="text-xs text-slate-600">
          Powered by{' '}
          <span className="text-gold-500 font-semibold">Google Gemini</span>
          {' '}·{' '}
          <span className="text-navy-400 font-semibold">FastAPI</span>
          {' '}·{' '}
          <span className="text-blue-400 font-semibold">React</span>
        </p>
      </footer>

    </div>
  )
}
