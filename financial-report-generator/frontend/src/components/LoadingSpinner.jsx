/**
 * LoadingSpinner.jsx — Animated loading indicator with a status message.
 */

import React from 'react'

export default function LoadingSpinner({ message = 'Processing...' }) {
  return (
    <div className="flex flex-col items-center gap-5 py-8">
      {/* Concentric spinning rings */}
      <div className="relative w-16 h-16">
        {/* Outer ring */}
        <div className="absolute inset-0 rounded-full border-2 border-navy-600/30" />
        <div
          className="absolute inset-0 rounded-full border-2 border-transparent border-t-gold-500"
          style={{ animation: 'spinRing 1s linear infinite' }}
        />
        {/* Middle ring */}
        <div className="absolute inset-2 rounded-full border-2 border-navy-600/20" />
        <div
          className="absolute inset-2 rounded-full border-2 border-transparent border-t-navy-500"
          style={{ animation: 'spinRing 1.5s linear infinite reverse' }}
        />
        {/* Inner dot */}
        <div className="absolute inset-5 rounded-full bg-gold-500/80 animate-pulse" />
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold text-white">{message}</p>
        <p className="text-xs text-slate-500 mt-1">This may take a moment…</p>
      </div>
    </div>
  )
}
