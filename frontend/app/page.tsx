'use client'

import { useState, useEffect } from 'react'

// Types
interface AnalysisResult {
  intent: string
  assumptions: string[]
  ambiguities: string[]
  requirements: string[]
}

interface EdgeCase {
  id: string
  title: string
  description: string
  severity: 'high' | 'medium' | 'low'
}

interface Contradiction {
  id: string
  description: string
  conflictingRequirements: string[]
}

interface CompletenessGap {
  id: string
  category: string
  description: string
}

interface SpecificationResult {
  edgeCases: EdgeCase[]
  contradictions: Contradiction[]
  completenessGaps: CompletenessGap[]
}

interface RefinementSuggestion {
  id: string
  type: 'edge_case' | 'contradiction' | 'gap'
  title: string
  description: string
  impact: string
  suggestion: string
  severity?: 'high' | 'medium' | 'low'
}

interface SessionData {
  sessionId: string
  analysis?: AnalysisResult
  specification?: SpecificationResult
  refinementSuggestions?: RefinementSuggestion[]
  currentSuggestionIndex: number
  finalizedSpecification?: string
}

type Phase = 'entry' | 'analysis' | 'specification' | 'refinement' | 'result'

const EXAMPLE_PROMPTS = [
  "Build a REST API for managing user tasks with authentication, CRUD operations, and real-time notifications",
  "Create a real-time chat application with message encryption, file sharing, and video calling capabilities",
  "Design a dashboard for analytics visualization with custom charts, data filtering, and export functionality",
  "Develop an e-commerce platform with inventory management, payment processing, and order tracking",
  "Build a project management tool with task assignment, time tracking, and team collaboration features"
]

export default function SpecifyApp() {
  const [phase, setPhase] = useState<Phase>('entry')
  const [prompt, setPrompt] = useState('')
  const [sessionData, setSessionData] = useState<SessionData>({
    sessionId: '',
    currentSuggestionIndex: 0
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [specificationProgress, setSpecificationProgress] = useState(0)
  const [refinementDecisions, setRefinementDecisions] = useState<Record<string, 'accepted' | 'rejected' | 'modified' | 'skipped'>>({})

  // Auto-advance phases
  useEffect(() => {
    if (phase === 'analysis' && sessionData.analysis) {
      const timer = setTimeout(() => {
        setPhase('specification')
      }, 1500)
      return () => clearTimeout(timer)
    }
    if (phase === 'specification' && sessionData.specification) {
      const timer = setTimeout(() => {
        setPhase('refinement')
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [phase, sessionData])

  // Keyboard shortcuts for refinement
  useEffect(() => {
    if (phase !== 'refinement') return

    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return

      switch (e.key.toLowerCase()) {
        case ' ':
        case 'enter':
          e.preventDefault()
          handleRefinementAction('accepted')
          break
        case 'x':
          e.preventDefault()
          handleRefinementAction('rejected')
          break
        case 'e':
          e.preventDefault()
          handleRefinementAction('modified')
          break
        case 's':
          e.preventDefault()
          handleRefinementAction('skipped')
          break
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [phase, sessionData.currentSuggestionIndex])

  const handleAnalyze = async () => {
    if (!prompt.trim()) return

    setIsLoading(true)
    setError('')
    setPhase('analysis')
    setAnalysisProgress(0)

    try {
      // Simulate analysis progress
      const progressInterval = setInterval(() => {
        setAnalysisProgress(prev => Math.min(prev + 25, 100))
      }, 800)

      // Call analysis API
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/analyze/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })

      if (!response.ok) throw new Error('Analysis failed')

      const analysisResult = await response.json()
      clearInterval(progressInterval)
      setAnalysisProgress(100)

      setSessionData(prev => ({
        ...prev,
        sessionId: analysisResult.session_id || analysisResult.sessionId || `session-${Date.now()}`,
        analysisId: analysisResult.analysis_id,
        analysis: analysisResult
      }))

      // Auto-start specification
      setTimeout(() => startSpecification(analysisResult.analysis_id, analysisResult.session_id || analysisResult.sessionId), 1000)

    } catch (err) {
      setError('Failed to analyze prompt. Please try again.')
      setPhase('entry')
    } finally {
      setIsLoading(false)
    }
  }

  const startSpecification = async (analysisId: string, sessionId: string) => {
    setSpecificationProgress(0)

    try {
      const progressInterval = setInterval(() => {
        setSpecificationProgress(prev => Math.min(prev + 20, 100))
      }, 600)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/specify/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_result_id: analysisId,
          session_id: sessionId,
          mode: 'balanced'
        })
      })

      if (!response.ok) throw new Error('Specification failed')

      const specResult = await response.json()
      clearInterval(progressInterval)
      setSpecificationProgress(100)

      setSessionData(prev => ({
        ...prev,
        specification: specResult
      }))

      // Start refinement
      setTimeout(() => startRefinement(sessionId), 1000)

    } catch (err) {
      setError('Failed to generate specification. Please try again.')
      setPhase('entry')
    }
  }

  const startRefinement = async (sessionId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/refinement/start/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId })
      })

      if (!response.ok) throw new Error('Refinement failed to start')

      const refinementData = await response.json()
      setSessionData(prev => ({
        ...prev,
        refinementSuggestions: refinementData.suggestions || []
      }))

    } catch (err) {
      setError('Failed to start refinement. Please try again.')
    }
  }

  const handleRefinementAction = async (action: 'accepted' | 'rejected' | 'modified' | 'skipped') => {
    const currentSuggestion = sessionData.refinementSuggestions?.[sessionData.currentSuggestionIndex]
    if (!currentSuggestion) return

    setRefinementDecisions(prev => ({
      ...prev,
      [currentSuggestion.id]: action
    }))

    // Move to next suggestion
    const nextIndex = sessionData.currentSuggestionIndex + 1
    if (nextIndex < (sessionData.refinementSuggestions?.length || 0)) {
      setSessionData(prev => ({
        ...prev,
        currentSuggestionIndex: nextIndex
      }))
    } else {
      // All suggestions processed, finalize
      await finalizeSpecification()
    }
  }

  const finalizeSpecification = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/refinement/${sessionData.sessionId}/finalize/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decisions: refinementDecisions })
      })

      if (!response.ok) throw new Error('Finalization failed')

      const finalResult = await response.json()
      setSessionData(prev => ({
        ...prev,
        finalizedSpecification: finalResult.specification
      }))
      setPhase('result')

    } catch (err) {
      setError('Failed to finalize specification. Please try again.')
    }
  }

  const copyToClipboard = async () => {
    if (sessionData.finalizedSpecification) {
      await navigator.clipboard.writeText(sessionData.finalizedSpecification)
      // Could add a toast notification here
    }
  }

  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high': return '#ef4444'
      case 'medium': return '#f97316'
      case 'low': return '#22c55e'
      default: return '#6b7280'
    }
  }

  const currentSuggestion = sessionData.refinementSuggestions?.[sessionData.currentSuggestionIndex]
  const totalSuggestions = sessionData.refinementSuggestions?.length || 0

  return (
    <>
      <style jsx>{`
        .app-container {
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          color: #1a1a1a;
        }

        .phase-container {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          padding: 2rem;
          transition: all 0.3s ease;
        }

        .hero-section {
          text-align: center;
          max-width: 800px;
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 24px;
          padding: 3rem;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
          animation: fadeIn 0.6s ease-out;
        }

        .hero-title {
          font-size: 3.5rem;
          font-weight: 700;
          margin-bottom: 1rem;
          background: linear-gradient(135deg, #667eea, #764ba2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-subtitle {
          font-size: 1.2rem;
          color: #6b7280;
          margin-bottom: 2rem;
          line-height: 1.6;
        }

        .prompt-container {
          margin-bottom: 2rem;
        }

        .prompt-textarea {
          width: 100%;
          min-height: 200px;
          padding: 1.5rem;
          border: 2px solid #e5e7eb;
          border-radius: 16px;
          font-size: 1.1rem;
          line-height: 1.6;
          resize: vertical;
          transition: all 0.3s ease;
          font-family: inherit;
        }

        .prompt-textarea:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .examples-dropdown {
          margin-bottom: 1.5rem;
        }

        .examples-select {
          width: 100%;
          padding: 1rem;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          font-size: 1rem;
          background: white;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .examples-select:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .primary-button {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          border: none;
          padding: 1.2rem 2.5rem;
          border-radius: 16px;
          font-size: 1.1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
          min-width: 200px;
        }

        .primary-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 25px rgba(102, 126, 234, 0.4);
        }

        .primary-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .secondary-button {
          background: white;
          color: #667eea;
          border: 2px solid #667eea;
          padding: 1rem 2rem;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          margin: 0.5rem;
        }

        .secondary-button:hover {
          background: #667eea;
          color: white;
          transform: translateY(-1px);
        }

        .time-estimate {
          color: #6b7280;
          font-size: 0.9rem;
          margin-top: 1rem;
        }

        .progress-container {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 24px;
          padding: 3rem;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
          max-width: 600px;
          width: 100%;
          animation: slideIn 0.5s ease-out;
        }

        .progress-title {
          font-size: 2.5rem;
          font-weight: 700;
          margin-bottom: 2rem;
          text-align: center;
          color: #1a1a1a;
        }

        .progress-step {
          display: flex;
          align-items: center;
          padding: 1rem 0;
          font-size: 1.1rem;
          transition: all 0.3s ease;
        }

        .progress-step.completed {
          color: #22c55e;
        }

        .progress-step.active {
          color: #667eea;
          font-weight: 600;
        }

        .progress-icon {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          margin-right: 1rem;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
        }

        .progress-icon.completed {
          background: #22c55e;
          color: white;
        }

        .progress-icon.active {
          background: #667eea;
          color: white;
        }

        .progress-icon.pending {
          background: #e5e7eb;
          color: #6b7280;
        }

        .specification-container {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 24px;
          padding: 2rem;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
          max-width: 1000px;
          width: 100%;
          max-height: 80vh;
          overflow-y: auto;
          animation: slideIn 0.5s ease-out;
        }

        .spec-section {
          margin-bottom: 2rem;
        }

        .spec-section h3 {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: #1a1a1a;
        }

        .edge-case-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 1rem;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          border-left: 4px solid;
          transition: all 0.3s ease;
        }

        .edge-case-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        }

        .edge-case-card.high {
          border-left-color: #ef4444;
        }

        .edge-case-card.medium {
          border-left-color: #f97316;
        }

        .edge-case-card.low {
          border-left-color: #22c55e;
        }

        .severity-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .severity-badge.high {
          background: #fee2e2;
          color: #dc2626;
        }

        .severity-badge.medium {
          background: #fed7aa;
          color: #ea580c;
        }

        .severity-badge.low {
          background: #dcfce7;
          color: #16a34a;
        }

        .refinement-container {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 24px;
          padding: 3rem;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
          max-width: 800px;
          width: 100%;
          text-align: center;
          animation: slideIn 0.5s ease-out;
        }

        .suggestion-card {
          background: white;
          border-radius: 16px;
          padding: 2.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          text-align: left;
          transition: all 0.3s ease;
        }

        .suggestion-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
        }

        .suggestion-title {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: #1a1a1a;
        }

        .suggestion-description {
          font-size: 1.1rem;
          line-height: 1.6;
          color: #4b5563;
          margin-bottom: 1.5rem;
        }

        .suggestion-impact {
          background: #f3f4f6;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          font-style: italic;
        }

        .action-buttons {
          display: flex;
          gap: 1rem;
          justify-content: center;
          flex-wrap: wrap;
        }

        .action-button {
          padding: 1rem 2rem;
          border: none;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          min-width: 120px;
        }

        .action-button.accept {
          background: #22c55e;
          color: white;
        }

        .action-button.reject {
          background: #ef4444;
          color: white;
        }

        .action-button.modify {
          background: #3b82f6;
          color: white;
        }

        .action-button.skip {
          background: #6b7280;
          color: white;
        }

        .action-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }

        .progress-indicator {
          margin-bottom: 2rem;
          font-size: 1.1rem;
          color: #6b7280;
        }

        .keyboard-hints {
          margin-top: 2rem;
          padding: 1rem;
          background: #f9fafb;
          border-radius: 8px;
          font-size: 0.9rem;
          color: #6b7280;
        }

        .result-container {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 24px;
          padding: 3rem;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
          max-width: 800px;
          width: 100%;
          text-align: center;
          animation: slideIn 0.5s ease-out;
        }

        .success-icon {
          width: 80px;
          height: 80px;
          background: #22c55e;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 2rem;
          animation: bounce 0.6s ease-out;
        }

        .specification-output {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 2rem;
          margin: 2rem 0;
          text-align: left;
          max-height: 400px;
          overflow-y: auto;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.9rem;
          line-height: 1.6;
        }

        .result-actions {
          display: flex;
          gap: 1rem;
          justify-content: center;
          flex-wrap: wrap;
          margin-top: 2rem;
        }

        .error-message {
          background: #fee2e2;
          color: #dc2626;
          padding: 1rem;
          border-radius: 8px;
          margin: 1rem 0;
          text-align: center;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #e5e7eb;
          border-top-color: #667eea;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }

        @keyframes bounce {
          0%, 20%, 53%, 80%, 100% { transform: translateY(0); }
          40%, 43% { transform: translateY(-10px); }
          70% { transform: translateY(-5px); }
          90% { transform: translateY(-2px); }
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .hero-title {
            font-size: 2.5rem;
          }

          .phase-container {
            padding: 1rem;
          }

          .hero-section, .progress-container, .specification-container, .refinement-container, .result-container {
            padding: 2rem;
          }

          .action-buttons {
            flex-direction: column;
          }

          .action-button {
            min-width: 100%;
          }
        }
      `}</style>

      <div className="app-container">
        {phase === 'entry' && (
          <div className="phase-container">
            <div className="hero-section">
              <h1 className="hero-title">Specify</h1>
              <p className="hero-subtitle">
                Transform your ideas into comprehensive software specifications with AI-powered analysis and refinement
              </p>

              <div className="prompt-container">
                <div className="examples-dropdown">
                  <select
                    className="examples-select"
                    onChange={(e) => e.target.value && setPrompt(e.target.value)}
                    value=""
                  >
                    <option value="">Choose an example prompt...</option>
                    {EXAMPLE_PROMPTS.map((example, index) => (
                      <option key={index} value={example}>{example}</option>
                    ))}
                  </select>
                </div>

                <textarea
                  className="prompt-textarea"
                  placeholder="Describe what you want to build. Be as detailed or as brief as you like - our AI will help you flesh out the complete specification..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
              </div>

              <button
                className="primary-button"
                onClick={handleAnalyze}
                disabled={!prompt.trim() || isLoading}
              >
                {isLoading ? (
                  <div className="loading-spinner" />
                ) : (
                  'Analyze & Specify'
                )}
              </button>

              <div className="time-estimate">
                Estimated time: 30-45 seconds
              </div>

              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}
            </div>
          </div>
        )}

        {phase === 'analysis' && (
          <div className="phase-container">
            <div className="progress-container">
              <h2 className="progress-title">Analyzing Your Prompt</h2>

              <div className="progress-step completed">
                <div className="progress-icon completed">✓</div>
                Extracting intent and requirements
              </div>

              <div className={`progress-step ${analysisProgress >= 50 ? 'completed' : analysisProgress >= 25 ? 'active' : ''}`}>
                <div className={`progress-icon ${analysisProgress >= 50 ? 'completed' : analysisProgress >= 25 ? 'active' : 'pending'}`}>
                  {analysisProgress >= 50 ? '✓' : '2'}
                </div>
                Identifying assumptions and ambiguities
              </div>

              <div className={`progress-step ${analysisProgress >= 75 ? 'completed' : analysisProgress >= 50 ? 'active' : ''}`}>
                <div className={`progress-icon ${analysisProgress >= 75 ? 'completed' : analysisProgress >= 50 ? 'active' : 'pending'}`}>
                  {analysisProgress >= 75 ? '✓' : '3'}
                </div>
                Mapping functional requirements
              </div>

              <div className={`progress-step ${analysisProgress >= 100 ? 'completed' : analysisProgress >= 75 ? 'active' : ''}`}>
                <div className={`progress-icon ${analysisProgress >= 100 ? 'completed' : analysisProgress >= 75 ? 'active' : 'pending'}`}>
                  {analysisProgress >= 100 ? '✓' : '4'}
                </div>
                Preparing specification framework
              </div>
            </div>
          </div>
        )}

        {phase === 'specification' && (
          <div className="phase-container">
            <div className="progress-container">
              <h2 className="progress-title">Generating Specification</h2>

              <div className="progress-step completed">
                <div className="progress-icon completed">✓</div>
                Analyzing edge cases
              </div>

              <div className={`progress-step ${specificationProgress >= 40 ? 'completed' : specificationProgress >= 20 ? 'active' : ''}`}>
                <div className={`progress-icon ${specificationProgress >= 40 ? 'completed' : specificationProgress >= 20 ? 'active' : 'pending'}`}>
                  {specificationProgress >= 40 ? '✓' : '2'}
                </div>
                Detecting contradictions
              </div>

              <div className={`progress-step ${specificationProgress >= 60 ? 'completed' : specificationProgress >= 40 ? 'active' : ''}`}>
                <div className={`progress-icon ${specificationProgress >= 60 ? 'completed' : specificationProgress >= 40 ? 'active' : 'pending'}`}>
                  {specificationProgress >= 60 ? '✓' : '3'}
                </div>
                Identifying completeness gaps
              </div>

              <div className={`progress-step ${specificationProgress >= 80 ? 'completed' : specificationProgress >= 60 ? 'active' : ''}`}>
                <div className={`progress-icon ${specificationProgress >= 80 ? 'completed' : specificationProgress >= 60 ? 'active' : 'pending'}`}>
                  {specificationProgress >= 80 ? '✓' : '4'}
                </div>
                Generating refinement suggestions
              </div>

              <div className={`progress-step ${specificationProgress >= 100 ? 'completed' : specificationProgress >= 80 ? 'active' : ''}`}>
                <div className={`progress-icon ${specificationProgress >= 100 ? 'completed' : specificationProgress >= 80 ? 'active' : 'pending'}`}>
                  {specificationProgress >= 100 ? '✓' : '5'}
                </div>
                Preparing interactive refinement
              </div>

              {sessionData.specification && (
                <div className="specification-container" style={{ marginTop: '2rem', maxHeight: '400px' }}>
                  <div className="spec-section">
                    <h3>Edge Cases Identified ({sessionData.specification.edgeCases.length})</h3>
                    {sessionData.specification.edgeCases.slice(0, 3).map((edgeCase) => (
                      <div key={edgeCase.id} className={`edge-case-card ${edgeCase.severity}`}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                          <strong>{edgeCase.title}</strong>
                          <span className={`severity-badge ${edgeCase.severity}`}>{edgeCase.severity}</span>
                        </div>
                        <p>{edgeCase.description}</p>
                      </div>
                    ))}
                    {sessionData.specification.edgeCases.length > 3 && (
                      <p style={{ color: '#6b7280', fontStyle: 'italic' }}>
                        +{sessionData.specification.edgeCases.length - 3} more edge cases identified
                      </p>
                    )}
                  </div>

                  {sessionData.specification.contradictions.length > 0 && (
                    <div className="spec-section">
                      <h3>Contradictions Found ({sessionData.specification.contradictions.length})</h3>
                      {sessionData.specification.contradictions.slice(0, 2).map((contradiction) => (
                        <div key={contradiction.id} className="edge-case-card high">
                          <p><strong>Conflict:</strong> {contradiction.description}</p>
                          <p><strong>Requirements:</strong> {contradiction.conflictingRequirements.join(', ')}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {sessionData.specification.completenessGaps.length > 0 && (
                    <div className="spec-section">
                      <h3>Completeness Gaps ({sessionData.specification.completenessGaps.length})</h3>
                      {sessionData.specification.completenessGaps.slice(0, 2).map((gap) => (
                        <div key={gap.id} className="edge-case-card medium">
                          <p><strong>{gap.category}:</strong> {gap.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {phase === 'refinement' && (
          <div className="phase-container">
            <div className="refinement-container">
              <h2 className="progress-title">Interactive Refinement</h2>

              <div className="progress-indicator">
                Suggestion {sessionData.currentSuggestionIndex + 1} of {totalSuggestions}
              </div>

              {currentSuggestion && (
                <div className="suggestion-card">
                  <h3 className="suggestion-title">{currentSuggestion.title}</h3>
                  <p className="suggestion-description">{currentSuggestion.description}</p>

                  {currentSuggestion.impact && (
                    <div className="suggestion-impact">
                      <strong>Impact:</strong> {currentSuggestion.impact}
                    </div>
                  )}

                  {currentSuggestion.severity && (
                    <div style={{ marginBottom: '1rem' }}>
                      <span className={`severity-badge ${currentSuggestion.severity}`}>
                        {currentSuggestion.severity} priority
                      </span>
                    </div>
                  )}

                  <p><strong>Suggestion:</strong> {currentSuggestion.suggestion}</p>
                </div>
              )}

              <div className="action-buttons">
                <button
                  className="action-button accept"
                  onClick={() => handleRefinementAction('accepted')}
                >
                  ✓ Accept
                </button>
                <button
                  className="action-button reject"
                  onClick={() => handleRefinementAction('rejected')}
                >
                  ✗ Reject
                </button>
                <button
                  className="action-button modify"
                  onClick={() => handleRefinementAction('modified')}
                >
                  ✏️ Modify
                </button>
                <button
                  className="action-button skip"
                  onClick={() => handleRefinementAction('skipped')}
                >
                  ⏭️ Skip
                </button>
              </div>

              <div className="keyboard-hints">
                <strong>Keyboard shortcuts:</strong> Space/Enter = Accept, X = Reject, E = Modify, S = Skip
              </div>

              {sessionData.currentSuggestionIndex >= Math.floor(totalSuggestions * 0.8) && (
                <button
                  className="secondary-button"
                  onClick={finalizeSpecification}
                  style={{ marginTop: '2rem' }}
                >
                  Finalize Specification Now
                </button>
              )}
            </div>
          </div>
        )}

        {phase === 'result' && (
          <div className="phase-container">
            <div className="result-container">
              <div className="success-icon">
                ✓
              </div>

              <h2 className="progress-title">Specification Complete!</h2>
              <p className="hero-subtitle">
                Your comprehensive software specification is ready with all refinements applied.
              </p>

              {sessionData.finalizedSpecification && (
                <div className="specification-output">
                  {sessionData.finalizedSpecification}
                </div>
              )}

              <div className="result-actions">
                <button
                  className="primary-button"
                  onClick={copyToClipboard}
                >
                  📋 Copy to Clipboard
                </button>
                <button
                  className="secondary-button"
                  onClick={() => {
                    // This would integrate with your agent execution system
                    alert('Agent execution feature coming soon!')
                  }}
                >
                  🚀 Execute with Agents
                </button>
              </div>

              <div style={{ marginTop: '2rem' }}>
                <button
                  className="secondary-button"
                  onClick={() => {
                    setPhase('entry')
                    setPrompt('')
                    setSessionData({ sessionId: '', currentSuggestionIndex: 0 })
                    setRefinementDecisions({})
                    setError('')
                  }}
                >
                  Create New Specification
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}