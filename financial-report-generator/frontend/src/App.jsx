/**
 * App.jsx — Root component with Toaster provider.
 */

import React from 'react'
import { Toaster } from 'react-hot-toast'
import HomePage from './pages/HomePage'

export default function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0F1928',
            color: '#E2E8F0',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            fontSize: '13px',
            fontFamily: 'Inter, sans-serif',
          },
          success: {
            iconTheme: { primary: '#27AE60', secondary: '#0F1928' },
          },
          error: {
            iconTheme: { primary: '#E74C3C', secondary: '#0F1928' },
            duration: 7000,
          },
        }}
      />
      <HomePage />
    </>
  )
}
