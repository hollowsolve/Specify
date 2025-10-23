export const dynamic = 'force-dynamic'

'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { useAnalysis } from '@/lib/hooks/useAnalysis'
import { cn } from '@/lib/utils'
import {
  ArrowRight,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  Lightbulb,
  FileText,
  Loader2,
} from 'lucide-react'

const EXAMPLE_PROMPTS = [
  {
    title: "E-commerce Platform",
    prompt: "Build a modern e-commerce platform where users can browse products, add items to cart, make secure payments, and track orders. Include admin dashboard for inventory management."
  },
  {
    title: "Task Management App",
    prompt: "Create a collaborative task management application with project boards, team member assignments, due dates, file attachments, and real-time notifications."
  },
  {
    title: "Social Media Dashboard",
    prompt: "Develop a social media management tool that allows users to schedule posts across multiple platforms, analyze engagement metrics, and collaborate with team members."
  },
]

export default function AnalyzePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const sessionId = searchParams.get('session')

  const {
    prompt,
    isAnalyzing,
    result,
    progress,
    error,
    analyzePrompt,
    updatePrompt,
    clearError,
  } = useAnalysis()

  const [selectedExample, setSelectedExample] = useState<number | null>(null)

  useEffect(() => {
    if (sessionId && !result) {
      // Load existing session data if needed
      // This would fetch from API if session exists
    }
  }, [sessionId, result])

  const handleAnalyze = async () => {
    if (!prompt.trim()) return

    try {
      clearError()
      const analysisResult = await analyzePrompt({
        prompt,
        sessionId: sessionId || undefined,
      })

      // Navigate to specification phase
      router.push(`/specify?analysis=${analysisResult.id}`)
    } catch (error) {
      // Error is already handled in the hook
    }
  }

  const handleExampleSelect = (example: string) => {
    updatePrompt(example)
    setSelectedExample(null)
  }

  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return 'destructive'
      case 'medium':
        return 'warning'
      case 'low':
        return 'secondary'
      default:
        return 'secondary'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Target className="h-6 w-6 text-blue-600" />
              <h1 className="text-2xl font-bold">Analyze Requirements</h1>
            </div>
            <div className="flex-1" />
            <Button variant="outline" onClick={() => router.push('/')}>
              Back to Home
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Input Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Describe Your Software Requirements
              </CardTitle>
              <CardDescription>
                Provide a detailed description of what you want to build. The AI will analyze your requirements,
                identify potential ambiguities, and extract key specifications.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="Example: Build a task management application where teams can create projects, assign tasks to members, set deadlines, track progress, and receive notifications. Include user authentication, real-time updates, and mobile responsiveness..."
                value={prompt}
                onChange={(e) => updatePrompt(e.target.value)}
                className="min-h-[200px] resize-none"
                disabled={isAnalyzing}
              />

              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {prompt.length} characters
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedExample(selectedExample === null ? 0 : null)}
                  >
                    <Lightbulb className="h-4 w-4 mr-2" />
                    Example Prompts
                  </Button>
                  <Button
                    onClick={handleAnalyze}
                    disabled={!prompt.trim() || isAnalyzing}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Target className="h-4 w-4 mr-2" />
                        Analyze Requirements
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Example Prompts */}
              {selectedExample !== null && (
                <Card className="border-dashed">
                  <CardHeader>
                    <CardTitle className="text-lg">Example Prompts</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {EXAMPLE_PROMPTS.map((example, index) => (
                      <div
                        key={index}
                        className="p-3 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => handleExampleSelect(example.prompt)}
                      >
                        <div className="font-medium mb-1">{example.title}</div>
                        <div className="text-sm text-muted-foreground line-clamp-2">
                          {example.prompt}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>

          {/* Progress */}
          {isAnalyzing && (
            <Card>
              <CardContent className="py-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                    <div>
                      <div className="font-medium">Analyzing your requirements...</div>
                      <div className="text-sm text-muted-foreground">
                        This may take a few moments
                      </div>
                    </div>
                  </div>
                  <Progress value={progress} className="w-full" />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {error && (
            <Card className="border-destructive">
              <CardContent className="py-6">
                <div className="flex items-center gap-3 text-destructive">
                  <AlertTriangle className="h-5 w-5" />
                  <div>
                    <div className="font-medium">Analysis Failed</div>
                    <div className="text-sm">{error}</div>
                  </div>
                  <Button variant="outline" size="sm" onClick={clearError} className="ml-auto">
                    Dismiss
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    Analysis Complete
                  </CardTitle>
                  <CardDescription>
                    AI has analyzed your requirements and identified key insights
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">{result.requirements.length}</div>
                      <div className="text-sm text-muted-foreground">Requirements</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-yellow-600">{result.ambiguities.length}</div>
                      <div className="text-sm text-muted-foreground">Ambiguities</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">{Math.round(result.confidence * 100)}%</div>
                      <div className="text-sm text-muted-foreground">Confidence</div>
                    </div>
                  </div>

                  <Button
                    onClick={() => router.push(`/specify?analysis=${result.id}`)}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    Proceed to Specification
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>

              {/* Intent */}
              <Card>
                <CardHeader>
                  <CardTitle>Identified Intent</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground leading-relaxed">{result.intent}</p>
                </CardContent>
              </Card>

              {/* Requirements */}
              <Card>
                <CardHeader>
                  <CardTitle>Extracted Requirements</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {result.requirements.map((req, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>{req}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              {/* Assumptions */}
              {result.assumptions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Key Assumptions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {result.assumptions.map((assumption, index) => (
                        <li key={index} className="flex items-start gap-3">
                          <Clock className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                          <span>{assumption}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Ambiguities */}
              {result.ambiguities.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Identified Ambiguities</CardTitle>
                    <CardDescription>
                      These areas need clarification to ensure accurate specification
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {result.ambiguities.map((ambiguity) => (
                        <div
                          key={ambiguity.id}
                          className={cn(
                            "p-4 border rounded-lg",
                            ambiguity.severity === 'high' && "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
                            ambiguity.severity === 'medium' && "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20",
                            ambiguity.severity === 'low' && "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20"
                          )}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4" />
                              <Badge variant={getSeverityColor(ambiguity.severity)}>
                                {ambiguity.severity}
                              </Badge>
                            </div>
                          </div>
                          <p className="font-medium mb-2">{ambiguity.description}</p>
                          <div className="text-sm text-muted-foreground">
                            <strong>Context:</strong> {ambiguity.context}
                          </div>
                          {ambiguity.suggestions.length > 0 && (
                            <div className="mt-3">
                              <div className="text-sm font-medium mb-1">Suggestions:</div>
                              <ul className="text-sm text-muted-foreground space-y-1">
                                {ambiguity.suggestions.map((suggestion, index) => (
                                  <li key={index} className="flex items-start gap-2">
                                    <span className="text-blue-600">•</span>
                                    <span>{suggestion}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}