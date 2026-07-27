/**
 * ProgressIndicator.jsx — Step-by-step progress bar for the report pipeline.
 *
 * Shows 4 steps: Upload → Extract → Generate → Ready
 * Each step transitions through: pending → active → done
 */

import React from 'react'
import { Check, Upload, Cpu, FileText, Sparkles } from 'lucide-react'

const ICONS = [Upload, Cpu, FileText, Sparkles]

export default function ProgressIndicator({ steps, currentStep, status }) {
  return (
    <div className="w-full">
      {/* Step dots + connectors */}
      <div className="flex items-center justify-between relative">
        {steps.map((step, idx) => {
          const Icon = ICONS[idx]
          const isDone   = idx < currentStep
          const isActive = idx === currentStep
          const isPending = idx > currentStep

          return (
            <React.Fragment key={step.id}>
              {/* Step node */}
              <div className="flex flex-col items-center gap-2 z-10">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center
                    transition-all duration-500 relative
                    ${isDone
                      ? 'bg-green-500 shadow-lg shadow-green-500/30'
                      : isActive
                      ? 'bg-gradient-to-br from-navy-500 to-navy-600 shadow-lg shadow-navy-600/40'
                      : 'bg-white/5 border border-white/10'
                    }
                  `}
                >
                  {isDone ? (
                    <Check className="w-4 h-4 text-white" strokeWidth={3} />
                  ) : (
                    <Icon
                      className={`w-4 h-4 ${isActive ? 'text-white' : 'text-white/25'}`}
                      strokeWidth={1.8}
                    />
                  )}

                  {/* Active pulse ring */}
                  {isActive && status !== 'done' && (
                    <div className="absolute inset-0 rounded-full border-2 border-navy-400/50 animate-ping" />
                  )}
                </div>

                <div className="text-center">
                  <p className={`text-xs font-semibold transition-colors duration-300
                    ${isDone ? 'text-green-400' : isActive ? 'text-white' : 'text-white/25'}`}
                  >
                    {step.label}
                  </p>
                </div>
              </div>

              {/* Connector line */}
              {idx < steps.length - 1 && (
                <div className="flex-1 h-0.5 mx-2 relative overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{
                      width: idx < currentStep ? '100%' : idx === currentStep ? '50%' : '0%',
                      background: idx < currentStep
                        ? 'linear-gradient(90deg, #27AE60, #2ECC71)'
                        : 'linear-gradient(90deg, #1E3A5F, #2C5282)',
                    }}
                  />
                </div>
              )}
            </React.Fragment>
          )
        })}
      </div>

      {/* Active step description */}
      {currentStep >= 0 && currentStep < steps.length && (
        <p className="text-center text-xs text-slate-400 mt-4 animate-fade-in-up">
          {steps[currentStep].description}
        </p>
      )}
    </div>
  )
}
