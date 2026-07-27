/**
 * api.js — Axios API client for the Bull AI backend.
 *
 * All requests go through the Vite proxy (/api → http://localhost:8000/api)
 * in development, and directly to the backend in production.
 */

import axios from 'axios'

// ── Axios instance ────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api',
  timeout: 120_000, // 2 minutes (AI extraction can be slow)
})

// ── Response interceptor — normalise errors ───────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      'An unexpected error occurred.'
    return Promise.reject(new Error(detail))
  }
)

// ── API functions ─────────────────────────────────────────────────────────────

/**
 * Upload a financial document and extract its raw text.
 *
 * @param {File} file - The file to upload.
 * @param {string} companyName - Company name for context.
 * @param {Function} onProgress - Upload progress callback (0–100).
 * @returns {Promise<{extracted_text: string, char_count: number, file_type: string}>}
 */
export async function uploadDocument(file, companyName, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('company_name', companyName)

  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    },
  })
  return data
}

/**
 * Extract structured financial data from document text using Gemini AI.
 *
 * @param {string} companyName
 * @param {string} extractedText
 * @returns {Promise<{data: object}>}
 */
export async function extractFinancialData(companyName, extractedText) {
  const { data } = await api.post('/extract', {
    company_name: companyName,
    extracted_text: extractedText,
  })
  return data
}

/**
 * Generate the full financial report (charts + HTML + PDF).
 *
 * @param {object} financialData - The structured JSON from /extract.
 * @returns {Promise<{filename: string, mode: 'pdf'|'html', charts_generated: string[]}>}
 */
export async function generateReport(financialData) {
  const { data } = await api.post('/generate', { data: financialData })
  return data
}

/**
 * Get the preview URL for a generated report file.
 *
 * @param {string} filename
 * @returns {string} URL
 */
export function getPreviewUrl(filename) {
  return `/api/preview/${encodeURIComponent(filename)}`
}

/**
 * Get the download URL for a generated report file.
 *
 * @param {string} filename
 * @returns {string} URL
 */
export function getDownloadUrl(filename) {
  return `/api/download/${encodeURIComponent(filename)}`
}

/**
 * Check backend health status.
 *
 * @returns {Promise<{status: string, gemini_configured: boolean}>}
 */
export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}

export default api
