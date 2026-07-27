/**
 * useReportGenerator.js — State machine hook for the report generation workflow.
 *
 * States:
 *   idle → uploading → extracting → generating → done
 *                                              ↓ (on error)
 *                                            error
 */

import { useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import {
  uploadDocument,
  extractFinancialData,
  generateReport,
  getPreviewUrl,
  getDownloadUrl,
} from '../services/api'

// ── Step definitions ──────────────────────────────────────────────────────────
export const STEPS = [
  { id: 'upload',    label: 'Uploading',   description: 'Reading your document...' },
  { id: 'extract',   label: 'Extracting',  description: 'Gemini AI is analysing financials...' },
  { id: 'generate',  label: 'Generating',  description: 'Building your report...' },
  { id: 'done',      label: 'Ready',       description: 'Your report is ready!' },
]

const INITIAL_STATE = {
  status: 'idle',      // idle | uploading | extracting | generating | done | error
  currentStep: -1,     // index into STEPS (-1 = not started)
  uploadProgress: 0,
  extractedData: null,
  reportFilename: null,
  reportMode: null,    // 'pdf' | 'html'
  error: null,
  charCount: 0,
  chartsGenerated: [],
}

// ─────────────────────────────────────────────────────────────────────────────

export function useReportGenerator() {
  const [state, setState] = useState(INITIAL_STATE)

  const updateState = (patch) =>
    setState((prev) => ({ ...prev, ...patch }))

  /**
   * Main entry point — runs the full pipeline:
   *   upload → extract → generate
   *
   * @param {File} file
   * @param {string} companyName
   */
  const generate = useCallback(async (file, companyName) => {
    // Reset
    setState({ ...INITIAL_STATE, status: 'uploading', currentStep: 0 })

    try {
      // ── Step 1: Upload & parse ──────────────────────────────────────────────
      updateState({ status: 'uploading', currentStep: 0 })
      const uploadResult = await uploadDocument(
        file,
        companyName,
        (pct) => updateState({ uploadProgress: pct })
      )
      updateState({ charCount: uploadResult.char_count })
      toast.success(`Document parsed (${(uploadResult.char_count / 1000).toFixed(1)}k chars)`)

      // ── Step 2: AI extraction ───────────────────────────────────────────────
      updateState({ status: 'extracting', currentStep: 1, uploadProgress: 100 })
      const extractResult = await extractFinancialData(
        companyName,
        uploadResult.extracted_text
      )
      updateState({ extractedData: extractResult.data })
      toast.success('Financial data extracted by Gemini AI')

      // ── Step 3: Report generation ───────────────────────────────────────────
      updateState({ status: 'generating', currentStep: 2 })
      const genResult = await generateReport(extractResult.data)

      // ── Done ────────────────────────────────────────────────────────────────
      updateState({
        status: 'done',
        currentStep: 3,
        reportFilename: genResult.filename,
        reportMode: genResult.mode,
        chartsGenerated: genResult.charts_generated || [],
        error: null,
      })
      toast.success('🎉 Report is ready!')

    } catch (err) {
      const message = err?.message || 'An unexpected error occurred.'
      updateState({ status: 'error', error: message, currentStep: -1 })
      toast.error(message, { duration: 8000 })
    }
  }, [])

  /** Reset to initial state */
  const reset = useCallback(() => {
    setState(INITIAL_STATE)
  }, [])

  // ── Derived helpers ─────────────────────────────────────────────────────────
  const previewUrl  = state.reportFilename ? getPreviewUrl(state.reportFilename) : null
  const downloadUrl = state.reportFilename ? getDownloadUrl(state.reportFilename) : null
  const isLoading   = ['uploading', 'extracting', 'generating'].includes(state.status)

  return {
    ...state,
    isLoading,
    previewUrl,
    downloadUrl,
    generate,
    reset,
    STEPS,
  }
}
