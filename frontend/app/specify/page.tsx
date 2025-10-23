'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useSpecification } from '@/lib/hooks/useSpecification'
import { useAnalysis } from '@/lib/hooks/useAnalysis'
import { cn, getSeverityColor } from '@/lib/utils'
import {
  ArrowRight,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  ShieldAlert,
  Zap,
  Target,
  ArrowLeft,
} from 'lucide-react'

export default function SpecifyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const analysisId = searchParams.get('analysis')

  const { getAnalysis, result: analysisResult } = useAnalysis()
  const {
    isGenerating,
    result,
    progress,
    error,
    generateSpecification,
    clearError,
  } = useSpecification()

  useEffect(() => {
    if (analysisId) {
      loadAnalysisAndGenerate()
    }
  }, [analysisId])

  const loadAnalysisAndGenerate = async () => {
    if (!analysisId) return

    try {
      // Load analysis result first
      await getAnalysis(analysisId)

      // Generate specification
      await generateSpecification({
        analysisId,
      })
    } catch (error) {
      console.error('Failed to load analysis or generate specification:', error)
    }
  }

  const handleProceedToRefinement = () => {
    if (result) {
      router.push(`/refine?specification=${result.id}`)
    }
  }

  const getSeverityIcon = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-red-600" />
      case 'medium':
        return <ShieldAlert className="h-4 w-4 text-yellow-600" />
      case 'low':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const getSeverityBadgeVariant = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return 'high' as const
      case 'medium':
        return 'medium' as const
      case 'low':
        return 'low' as const
      default:
        return 'secondary' as const
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-purple-600" />
              <h1 className="text-2xl font-bold">Generate Specification</h1>
            </div>
            <div className="flex-1" />
            <Button variant="outline" onClick={() => router.push('/')}>
              Home
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-5xl mx-auto space-y-8">
          {/* Analysis Summary */}
          {analysisResult && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5 text-blue-600" />
                  Analysis Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-blue-600">{analysisResult.requirements.length}</div>
                    <div className="text-sm text-muted-foreground">Requirements</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-yellow-600">{analysisResult.ambiguities.length}</div>
                    <div className="text-sm text-muted-foreground">Ambiguities</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-green-600">{analysisResult.assumptions.length}</div>
                    <div className="text-sm text-muted-foreground">Assumptions</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-purple-600">{Math.round(analysisResult.confidence * 100)}%</div>
                    <div className="text-sm text-muted-foreground">Confidence</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Generation Progress */}
          {isGenerating && (
            <Card>
              <CardContent className="py-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
                    <div>
                      <div className="font-medium">Generating comprehensive specification...</div>
                      <div className="text-sm text-muted-foreground">
                        Analyzing edge cases, identifying contradictions, and checking completeness
                      </div>
                    </div>
                  </div>
                  <Progress value={progress} className="w-full" />
                  <div className="text-sm text-muted-foreground text-center">
                    {progress}% complete
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Specification Generation Failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-6">
              {/* Overview */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    Specification Generated Successfully
                  </CardTitle>
                  <CardDescription>
                    Comprehensive analysis complete with {result.edgeCases.length} edge cases,{' '}
                    {result.contradictions.length} contradictions, and {result.completenessGaps.length} completeness gaps identified
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">{result.edgeCases.length}</div>
                      <div className="text-sm text-muted-foreground">Edge Cases</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-red-600">{result.contradictions.length}</div>
                      <div className="text-sm text-muted-foreground">Contradictions</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">{result.completenessGaps.length}</div>
                      <div className="text-sm text-muted-foreground">Completeness Gaps</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">{Math.round(result.confidence * 100)}%</div>
                      <div className="text-sm text-muted-foreground">Confidence</div>
                    </div>
                  </div>

                  <Button
                    onClick={handleProceedToRefinement}
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    size="lg"
                  >
                    Proceed to Refinement
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>

              {/* Compressed Requirements */}
              <Card>
                <CardHeader>
                  <CardTitle>Compressed Requirements</CardTitle>
                  <CardDescription>
                    Optimized and structured requirements based on the analysis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {result.compressedRequirements.map((requirement, index) => (
                      <li key={index} className="flex items-start gap-3 p-3 border rounded-lg">
                        <Zap className="h-5 w-5 text-purple-600 mt-0.5 flex-shrink-0" />
                        <span>{requirement}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              {/* Edge Cases */}
              {result.edgeCases.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Identified Edge Cases</CardTitle>
                    <CardDescription>
                      Potential scenarios that need special handling
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {result.edgeCases.map((edgeCase) => (
                        <div
                          key={edgeCase.id}
                          className={cn(
                            "p-4 border rounded-lg",
                            getSeverityColor(edgeCase.severity)
                          )}
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-2">
                              {getSeverityIcon(edgeCase.severity)}
                              <Badge variant={getSeverityBadgeVariant(edgeCase.severity)}>
                                {edgeCase.severity}
                              </Badge>
                              <Badge variant="outline">{edgeCase.category}</Badge>
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {Math.round(edgeCase.confidence * 100)}% confidence
                            </div>
                          </div>
                          <h4 className="font-medium mb-2">{edgeCase.description}</h4>
                          <div className="text-sm text-muted-foreground">
                            <strong>Suggested Handling:</strong> {edgeCase.suggestedHandling}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Contradictions */}
              {result.contradictions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <XCircle className="h-5 w-5 text-red-600" />
                      Identified Contradictions
                    </CardTitle>
                    <CardDescription>
                      Conflicting requirements that need resolution
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {result.contradictions.map((contradiction) => (
                        <div
                          key={contradiction.id}
                          className="p-4 border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 rounded-lg"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <Badge variant="destructive">{contradiction.severity}</Badge>
                          </div>
                          <h4 className="font-medium mb-2">{contradiction.description}</h4>
                          <div className="space-y-2 text-sm">
                            <div>
                              <strong>Conflicting Requirements:</strong>
                              <ul className="mt-1 ml-4 space-y-1">
                                {contradiction.conflictingRequirements.map((req, index) => (
                                  <li key={index} className="list-disc text-muted-foreground">
                                    {req}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <strong>Suggested Resolution:</strong>
                              <p className="text-muted-foreground mt-1">{contradiction.suggestedResolution}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Completeness Gaps */}
              {result.completenessGaps.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-blue-600" />
                      Completeness Gaps
                    </CardTitle>
                    <CardDescription>
                      Missing aspects that should be considered
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {result.completenessGaps.map((gap) => (
                        <div
                          key={gap.id}
                          className="p-4 border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20 rounded-lg"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <Badge variant="info">{gap.importance}</Badge>
                          </div>
                          <h4 className="font-medium mb-2">{gap.description}</h4>
                          <div className="space-y-2 text-sm">
                            <div>
                              <strong>Missing Aspects:</strong>
                              <ul className="mt-1 ml-4 space-y-1">
                                {gap.missingAspects.map((aspect, index) => (
                                  <li key={index} className="list-disc text-muted-foreground">
                                    {aspect}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <strong>Suggested Additions:</strong>
                              <ul className="mt-1 ml-4 space-y-1">
                                {gap.suggestedAdditions.map((addition, index) => (
                                  <li key={index} className="list-disc text-muted-foreground">
                                    {addition}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
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