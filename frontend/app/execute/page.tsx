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
import { ExecutionGraph } from '@/components/execution/ExecutionGraph'
import { useExecution } from '@/lib/hooks/useExecution'
import { useRefinement } from '@/lib/hooks/useRefinement'
import { AgentStatus, Artifact, ExecutionLog } from '@/types'
import { cn, getStatusColor, formatTimestamp, formatDuration } from '@/lib/utils'
import {
  Play,
  Square,
  Download,
  ArrowLeft,
  Activity,
  Code,
  FileText,
  User,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Package,
} from 'lucide-react'

export default function ExecutePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const refinementId = searchParams.get('refinement')

  const { getRefinement, result: refinementResult } = useRefinement()
  const {
    isExecuting,
    result,
    progress,
    error,
    viewMode,
    selectedNodeId,
    executeSpecification,
    stopExecution,
    downloadArtifact,
    downloadAllArtifacts,
    setViewMode,
    selectNode,
    clearError,
  } = useExecution()

  useEffect(() => {
    if (refinementId) {
      loadRefinementAndExecute()
    }
  }, [refinementId])

  const loadRefinementAndExecute = async () => {
    if (!refinementId) return

    try {
      await getRefinement(refinementId)

      // Start execution
      await executeSpecification({
        refinementId,
        config: {
          language: 'typescript',
          framework: 'nextjs',
          architecture: 'microservices',
          testingLevel: 'all',
          documentation: true,
        },
      })
    } catch (error) {
      console.error('Failed to load refinement or start execution:', error)
    }
  }

  const handleStopExecution = async () => {
    if (result?.id) {
      try {
        await stopExecution(result.id)
      } catch (error) {
        console.error('Failed to stop execution:', error)
      }
    }
  }

  const handleDownloadArtifact = async (artifact: Artifact) => {
    if (result?.id) {
      try {
        await downloadArtifact(result.id, artifact.id, artifact.name)
      } catch (error) {
        console.error('Failed to download artifact:', error)
      }
    }
  }

  const handleDownloadAll = async () => {
    if (result?.id) {
      try {
        await downloadAllArtifacts(result.id)
      } catch (error) {
        console.error('Failed to download all artifacts:', error)
      }
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'failed':
        return <AlertTriangle className="h-4 w-4 text-red-600" />
      case 'running':
        return <Activity className="h-4 w-4 text-blue-600 animate-pulse" />
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-600" />
    }
  }

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case 'code':
        return <Code className="h-4 w-4 text-blue-600" />
      case 'documentation':
        return <FileText className="h-4 w-4 text-green-600" />
      case 'test':
        return <CheckCircle className="h-4 w-4 text-purple-600" />
      case 'config':
        return <Zap className="h-4 w-4 text-orange-600" />
      default:
        return <Package className="h-4 w-4 text-gray-600" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-red-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <Play className="h-6 w-6 text-orange-600" />
              <h1 className="text-2xl font-bold">Execute Specification</h1>
            </div>
            <div className="flex-1" />
            <div className="flex gap-2">
              {result && result.status === 'running' && (
                <Button
                  variant="outline"
                  onClick={handleStopExecution}
                  className="text-red-600 hover:text-red-700"
                >
                  <Square className="h-4 w-4 mr-2" />
                  Stop
                </Button>
              )}
              {result && result.artifacts.length > 0 && (
                <Button
                  variant="outline"
                  onClick={handleDownloadAll}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download All
                </Button>
              )}
              <Button variant="outline" onClick={() => router.push('/')}>
                Home
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="space-y-8">
          {/* Execution Overview */}
          {result && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {getStatusIcon(result.status)}
                      Execution Status
                    </CardTitle>
                    <CardDescription>
                      Started {formatTimestamp(result.startTime)}
                      {result.endTime && ` • Completed ${formatTimestamp(result.endTime)}`}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={result.status === 'completed' ? 'success' :
                            result.status === 'failed' ? 'destructive' :
                            result.status === 'running' ? 'info' : 'secondary'}
                    className="text-sm"
                  >
                    {result.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-blue-600">{result.dag.nodes.length}</div>
                    <div className="text-sm text-muted-foreground">Total Tasks</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-green-600">
                      {result.dag.nodes.filter(n => n.status === 'completed').length}
                    </div>
                    <div className="text-sm text-muted-foreground">Completed</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-orange-600">{result.agents.length}</div>
                    <div className="text-sm text-muted-foreground">Active Agents</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-purple-600">{result.artifacts.length}</div>
                    <div className="text-sm text-muted-foreground">Artifacts</div>
                  </div>
                  <div className="text-center p-3 border rounded-lg">
                    <div className="text-lg font-semibold text-indigo-600">{Math.round(result.progress)}%</div>
                    <div className="text-sm text-muted-foreground">Progress</div>
                  </div>
                </div>

                <Progress value={result.progress} className="w-full" />
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Execution Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Main Content */}
          {result && (
            <Tabs value={viewMode} onValueChange={(value: any) => setViewMode(value)}>
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="dag">Execution Graph</TabsTrigger>
                <TabsTrigger value="agents">Agents ({result.agents.length})</TabsTrigger>
                <TabsTrigger value="artifacts">Artifacts ({result.artifacts.length})</TabsTrigger>
                <TabsTrigger value="logs">Logs ({result.logs.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="dag" className="space-y-4">
                <Card>
                  <CardContent className="p-0">
                    <div className="h-[600px]">
                      <ExecutionGraph
                        dag={result.dag}
                        selectedNodeId={selectedNodeId}
                        onNodeSelect={selectNode}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Selected Node Details */}
                {selectedNodeId && (
                  <NodeDetails
                    node={result.dag.nodes.find(n => n.id === selectedNodeId)}
                  />
                )}
              </TabsContent>

              <TabsContent value="agents" className="space-y-4">
                <div className="grid gap-4">
                  {result.agents.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} />
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="artifacts" className="space-y-4">
                <div className="grid gap-4">
                  {result.artifacts.map((artifact) => (
                    <ArtifactCard
                      key={artifact.id}
                      artifact={artifact}
                      onDownload={() => handleDownloadArtifact(artifact)}
                    />
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="logs" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Execution Logs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar">
                      {result.logs.map((log) => (
                        <LogEntry key={log.id} log={log} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  )
}

interface NodeDetailsProps {
  node?: any
}

function NodeDetails({ node }: NodeDetailsProps) {
  if (!node) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {node.type === 'agent' && <User className="h-5 w-5" />}
          {node.type === 'task' && <Zap className="h-5 w-5" />}
          {node.type === 'artifact' && <Package className="h-5 w-5" />}
          {node.label}
        </CardTitle>
        <CardDescription>
          {node.type} • {node.status}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm font-medium mb-1">Progress</div>
            <Progress value={node.progress} className="w-full" />
            <div className="text-xs text-muted-foreground mt-1">{node.progress}%</div>
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Duration</div>
            <div className="text-sm text-muted-foreground">
              {node.actualDuration && formatDuration(node.actualDuration)}
              {node.estimatedDuration && !node.actualDuration && `~${formatDuration(node.estimatedDuration)}`}
              {!node.actualDuration && !node.estimatedDuration && 'Not started'}
            </div>
          </div>
        </div>

        {node.dependencies.length > 0 && (
          <div className="mt-4">
            <div className="text-sm font-medium mb-2">Dependencies</div>
            <div className="flex flex-wrap gap-2">
              {node.dependencies.map((dep: string) => (
                <Badge key={dep} variant="outline" className="text-xs">
                  {dep}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface AgentCardProps {
  agent: AgentStatus
}

function AgentCard({ agent }: AgentCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              {agent.name}
            </CardTitle>
            <CardDescription>{agent.type}</CardDescription>
          </div>
          <Badge variant={agent.status === 'running' ? 'info' : 'secondary'}>
            {agent.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {agent.currentTask && (
            <div>
              <div className="text-sm font-medium mb-1">Current Task</div>
              <div className="text-sm text-muted-foreground">{agent.currentTask}</div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium mb-1">Progress</div>
              <Progress value={agent.progress} className="w-full" />
              <div className="text-xs text-muted-foreground mt-1">{agent.progress}%</div>
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Time Elapsed</div>
              <div className="text-sm text-muted-foreground">
                {formatDuration(agent.timeElapsed)}
              </div>
            </div>
          </div>

          {agent.capabilities.length > 0 && (
            <div>
              <div className="text-sm font-medium mb-2">Capabilities</div>
              <div className="flex flex-wrap gap-2">
                {agent.capabilities.map((capability) => (
                  <Badge key={capability} variant="outline" className="text-xs">
                    {capability}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {agent.queuedTasks.length > 0 && (
            <div>
              <div className="text-sm font-medium mb-2">Queued Tasks ({agent.queuedTasks.length})</div>
              <div className="text-sm text-muted-foreground">
                {agent.queuedTasks.slice(0, 3).join(', ')}
                {agent.queuedTasks.length > 3 && ` and ${agent.queuedTasks.length - 3} more...`}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

interface ArtifactCardProps {
  artifact: Artifact
  onDownload: () => void
}

function ArtifactCard({ artifact, onDownload }: ArtifactCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {getArtifactIcon(artifact.type)}
              {artifact.name}
            </CardTitle>
            <CardDescription>
              {artifact.path} • {(artifact.size / 1024).toFixed(1)} KB
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant="outline">{artifact.type}</Badge>
            <Button variant="outline" size="sm" onClick={onDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground">Created by</div>
            <div className="font-medium">{artifact.createdBy}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Created at</div>
            <div className="font-medium">{formatTimestamp(artifact.createdAt)}</div>
          </div>
          {artifact.language && (
            <div>
              <div className="text-muted-foreground">Language</div>
              <div className="font-medium">{artifact.language}</div>
            </div>
          )}
          <div>
            <div className="text-muted-foreground">Checksum</div>
            <div className="font-mono text-xs">{artifact.checksum.substring(0, 16)}...</div>
          </div>
        </div>

        {artifact.content && (
          <div className="mt-4">
            <div className="text-sm font-medium mb-2">Preview</div>
            <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto max-h-32">
              {artifact.content.substring(0, 500)}
              {artifact.content.length > 500 && '...'}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface LogEntryProps {
  log: ExecutionLog
}

function LogEntry({ log }: LogEntryProps) {
  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'warn':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'info':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'debug':
        return 'text-gray-600 bg-gray-50 border-gray-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  return (
    <div className={cn('p-3 rounded-lg border text-sm', getLevelColor(log.level))}>
      <div className="flex items-start justify-between mb-1">
        <div className="font-mono text-xs">{formatTimestamp(log.timestamp)}</div>
        <div className="flex gap-2">
          <Badge variant="outline" className="text-xs">
            {log.level}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {log.source}
          </Badge>
        </div>
      </div>
      <div>{log.message}</div>
    </div>
  )
}

function getArtifactIcon(type: string) {
  switch (type) {
    case 'code':
      return <Code className="h-4 w-4 text-blue-600" />
    case 'documentation':
      return <FileText className="h-4 w-4 text-green-600" />
    case 'test':
      return <CheckCircle className="h-4 w-4 text-purple-600" />
    case 'config':
      return <Zap className="h-4 w-4 text-orange-600" />
    default:
      return <Package className="h-4 w-4 text-gray-600" />
  }
}