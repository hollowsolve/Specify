'use client'

export const runtime = 'edge'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useRefinement } from '@/lib/hooks/useRefinement'
import { useSpecification } from '@/lib/hooks/useSpecification'
import { RefinementSuggestion } from '@/types'
import { cn } from '@/lib/utils'
import {
  ArrowRight,
  RefreshCw,
  Check,
  X,
  Edit3,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowLeft,
  Sparkles,
  FileCheck,
} from 'lucide-react'

export default function RefinePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const specificationId = searchParams.get('specification')

  const { getSpecification, result: specificationResult } = useSpecification()
  const {
    suggestions,
    isRefining,
    result,
    progress,
    error,
    refineSpecification,
    clearError,
  } = useRefinement()

  const [localSuggestions, setLocalSuggestions] = useState<RefinementSuggestion[]>([])
  const [activeTab, setActiveTab] = useState('suggestions')

  useEffect(() => {
    if (specificationId) {
      loadSpecificationAndGenerateSuggestions()
    }
  }, [specificationId])

  const loadSpecificationAndGenerateSuggestions = async () => {
    if (!specificationId) return

    try {
      await getSpecification(specificationId)

      // Auto-generate suggestions based on the specification
      if (specificationResult) {
        const autoSuggestions = generateSuggestions(specificationResult)
        setLocalSuggestions(autoSuggestions)
      }
    } catch (error) {
      console.error('Failed to load specification:', error)
    }
  }

  const generateSuggestions = (spec: any): RefinementSuggestion[] => {
    const suggestions: RefinementSuggestion[] = []

    // Generate suggestions from edge cases
    spec.edgeCases?.forEach((edgeCase: any, index: number) => {
      suggestions.push({
        id: `edge-${index}`,
        type: 'edge_case',
        action: 'approve',
        originalText: edgeCase.description,
        modifiedText: edgeCase.suggestedHandling,
        reasoning: `Handle edge case: ${edgeCase.category}`,
      })
    })

    // Generate suggestions from contradictions
    spec.contradictions?.forEach((contradiction: any, index: number) => {
      suggestions.push({
        id: `contradiction-${index}`,
        type: 'contradiction',
        action: 'modify',
        originalText: contradiction.description,
        modifiedText: contradiction.suggestedResolution,
        reasoning: 'Resolve requirement contradiction',
      })
    })

    // Generate suggestions from completeness gaps
    spec.completenessGaps?.forEach((gap: any, index: number) => {
      suggestions.push({
        id: `gap-${index}`,
        type: 'completeness',
        action: 'approve',
        originalText: gap.description,
        modifiedText: gap.suggestedAdditions.join('; '),
        reasoning: 'Address completeness gap',
      })
    })

    return suggestions
  }

  const handleSuggestionAction = (
    suggestionId: string,
    action: 'approve' | 'reject' | 'modify',
    modifiedText?: string
  ) => {
    setLocalSuggestions(prev =>
      prev.map(suggestion =>
        suggestion.id === suggestionId
          ? { ...suggestion, action, modifiedText }
          : suggestion
      )
    )
  }

  const handleFinalize = async () => {
    if (!specificationId) return

    try {
      await refineSpecification({
        specificationId,
        suggestions: localSuggestions,
      })

      if (result) {
        router.push(`/execute?refinement=${result.id}`)
      }
    } catch (error) {
      console.error('Failed to finalize refinement:', error)
    }
  }

  const approvedSuggestions = localSuggestions.filter(s => s.action === 'approve')
  const rejectedSuggestions = localSuggestions.filter(s => s.action === 'reject')
  const modifiedSuggestions = localSuggestions.filter(s => s.action === 'modify')

  const getSuggestionTypeIcon = (type: string) => {
    switch (type) {
      case 'edge_case':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />
      case 'contradiction':
        return <X className="h-4 w-4 text-red-600" />
      case 'completeness':
        return <CheckCircle className="h-4 w-4 text-blue-600" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getSuggestionTypeBadge = (type: string) => {
    switch (type) {
      case 'edge_case':
        return <Badge variant="warning">Edge Case</Badge>
      case 'contradiction':
        return <Badge variant="destructive">Contradiction</Badge>
      case 'completeness':
        return <Badge variant="info">Completeness</Badge>
      default:
        return <Badge variant="secondary">{type}</Badge>
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <RefreshCw className="h-6 w-6 text-green-600" />
              <h1 className="text-2xl font-bold">Refine Specification</h1>
            </div>
            <div className="flex-1" />
            <Button variant="outline" onClick={() => router.push('/')}>
              Home
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto space-y-8">
          {/* Specification Summary */}
          {specificationResult && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  Specification Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-orange-600">{specificationResult.edgeCases?.length || 0}</div>
                    <div className="text-sm text-muted-foreground">Edge Cases</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-red-600">{specificationResult.contradictions?.length || 0}</div>
                    <div className="text-sm text-muted-foreground">Contradictions</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-blue-600">{specificationResult.completenessGaps?.length || 0}</div>
                    <div className="text-sm text-muted-foreground">Completeness Gaps</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-green-600">{localSuggestions.length}</div>
                    <div className="text-sm text-muted-foreground">Total Suggestions</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Refinement Progress */}
          {isRefining && (
            <Card>
              <CardContent className="py-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="h-5 w-5 animate-spin text-green-600" />
                    <div>
                      <div className="font-medium">Finalizing specification...</div>
                      <div className="text-sm text-muted-foreground">
                        Applying refinements and generating final specification
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
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Refinement Failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Main Content */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="suggestions">
                All Suggestions ({localSuggestions.length})
              </TabsTrigger>
              <TabsTrigger value="approved">
                Approved ({approvedSuggestions.length})
              </TabsTrigger>
              <TabsTrigger value="modified">
                Modified ({modifiedSuggestions.length})
              </TabsTrigger>
              <TabsTrigger value="rejected">
                Rejected ({rejectedSuggestions.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="suggestions" className="space-y-4">
              <div className="grid gap-4">
                {localSuggestions.map((suggestion) => (
                  <SuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    onAction={handleSuggestionAction}
                  />
                ))}
              </div>
            </TabsContent>

            <TabsContent value="approved" className="space-y-4">
              <div className="grid gap-4">
                {approvedSuggestions.map((suggestion) => (
                  <SuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    onAction={handleSuggestionAction}
                    readonly
                  />
                ))}
              </div>
            </TabsContent>

            <TabsContent value="modified" className="space-y-4">
              <div className="grid gap-4">
                {modifiedSuggestions.map((suggestion) => (
                  <SuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    onAction={handleSuggestionAction}
                    readonly
                  />
                ))}
              </div>
            </TabsContent>

            <TabsContent value="rejected" className="space-y-4">
              <div className="grid gap-4">
                {rejectedSuggestions.map((suggestion) => (
                  <SuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    onAction={handleSuggestionAction}
                    readonly
                  />
                ))}
              </div>
            </TabsContent>
          </Tabs>

          {/* Actions */}
          <Card>
            <CardContent className="py-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium mb-1">Ready to finalize?</h3>
                  <p className="text-sm text-muted-foreground">
                    {approvedSuggestions.length + modifiedSuggestions.length} suggestions will be applied
                  </p>
                </div>
                <Button
                  onClick={handleFinalize}
                  disabled={isRefining || localSuggestions.length === 0}
                  className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
                  size="lg"
                >
                  <FileCheck className="h-4 w-4 mr-2" />
                  Finalize Specification
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

interface SuggestionCardProps {
  suggestion: RefinementSuggestion
  onAction: (id: string, action: 'approve' | 'reject' | 'modify', modifiedText?: string) => void
  readonly?: boolean
}

function SuggestionCard({ suggestion, onAction, readonly = false }: SuggestionCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(suggestion.modifiedText || suggestion.originalText)

  const getSuggestionTypeIcon = (type: string) => {
    switch (type) {
      case 'edge_case':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />
      case 'contradiction':
        return <X className="h-4 w-4 text-red-600" />
      case 'completeness':
        return <CheckCircle className="h-4 w-4 text-blue-600" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getSuggestionTypeBadge = (type: string) => {
    switch (type) {
      case 'edge_case':
        return <Badge variant="warning">Edge Case</Badge>
      case 'contradiction':
        return <Badge variant="destructive">Contradiction</Badge>
      case 'completeness':
        return <Badge variant="info">Completeness</Badge>
      default:
        return <Badge variant="secondary">{type}</Badge>
    }
  }

  const handleSaveEdit = () => {
    onAction(suggestion.id, 'modify', editText)
    setIsEditing(false)
  }

  return (
    <Card className={cn(
      "transition-all duration-200",
      suggestion.action === 'approve' && "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20",
      suggestion.action === 'reject' && "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
      suggestion.action === 'modify' && "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
    )}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {getSuggestionTypeIcon(suggestion.type)}
            {getSuggestionTypeBadge(suggestion.type)}
            {suggestion.action !== 'approve' && (
              <Badge variant="outline" className="ml-2">
                {suggestion.action}
              </Badge>
            )}
          </div>
          {!readonly && (
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(!isEditing)}
              >
                <Edit3 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium mb-2">Original</h4>
            <p className="text-sm text-muted-foreground p-3 border rounded-lg bg-muted/30">
              {suggestion.originalText}
            </p>
          </div>

          <div>
            <h4 className="font-medium mb-2">Suggested</h4>
            {isEditing ? (
              <div className="space-y-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full p-3 border rounded-lg min-h-[100px] resize-none"
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleSaveEdit}>
                    <Check className="h-4 w-4 mr-2" />
                    Save
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditing(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm p-3 border rounded-lg">
                {suggestion.modifiedText || suggestion.originalText}
              </p>
            )}
          </div>

          {suggestion.reasoning && (
            <div>
              <h4 className="font-medium mb-2">Reasoning</h4>
              <p className="text-sm text-muted-foreground italic">
                {suggestion.reasoning}
              </p>
            </div>
          )}

          {!readonly && !isEditing && (
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAction(suggestion.id, 'approve')}
                className={cn(
                  suggestion.action === 'approve' && "bg-green-100 border-green-300 text-green-700"
                )}
              >
                <Check className="h-4 w-4 mr-2" />
                Approve
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAction(suggestion.id, 'reject')}
                className={cn(
                  suggestion.action === 'reject' && "bg-red-100 border-red-300 text-red-700"
                )}
              >
                <X className="h-4 w-4 mr-2" />
                Reject
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsEditing(true)
                  setEditText(suggestion.modifiedText || suggestion.originalText)
                }}
              >
                <Edit3 className="h-4 w-4 mr-2" />
                Modify
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}