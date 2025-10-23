'use client'

import { useCallback, useMemo, useEffect, useState } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel,
  ReactFlowProvider,
  NodeTypes,
  MiniMap,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ExecutionDAG, DAGNode, DAGEdge, ExecutionStatus } from '@/types'
import { cn, getStatusColor, formatDuration } from '@/lib/utils'
import {
  Play,
  Pause,
  Square,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
  FileText,
  User,
  Maximize2,
  Minimize2,
} from 'lucide-react'

interface ExecutionGraphProps {
  dag: ExecutionDAG
  selectedNodeId?: string
  onNodeSelect?: (nodeId: string | undefined) => void
  className?: string
}

interface CustomNodeData {
  label: string
  type: 'task' | 'agent' | 'artifact'
  status: ExecutionStatus
  progress: number
  startTime?: string
  endTime?: string
  estimatedDuration?: number
  actualDuration?: number
}

const getNodeIcon = (type: string) => {
  switch (type) {
    case 'agent':
      return User
    case 'artifact':
      return FileText
    case 'task':
    default:
      return Zap
  }
}

const getStatusIcon = (status: ExecutionStatus) => {
  switch (status) {
    case 'completed':
      return CheckCircle
    case 'failed':
      return XCircle
    case 'running':
      return Play
    case 'pending':
      return Clock
    default:
      return AlertCircle
  }
}

const getStatusColor = (status: ExecutionStatus) => {
  switch (status) {
    case 'completed':
      return 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-900/20'
    case 'failed':
      return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-900/20'
    case 'running':
      return 'text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-900/20'
    case 'pending':
      return 'text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-900/20'
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-900/20'
  }
}

function CustomNode({ data, selected }: { data: CustomNodeData; selected: boolean }) {
  const NodeIcon = getNodeIcon(data.type)
  const StatusIcon = getStatusIcon(data.status)

  return (
    <div
      className={cn(
        "px-4 py-3 shadow-lg rounded-lg border-2 bg-white dark:bg-gray-800 min-w-[200px] transition-all duration-200",
        selected ? "ring-2 ring-blue-500 ring-offset-2" : "",
        getStatusColor(data.status)
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <NodeIcon className="h-4 w-4" />
        <span className="font-medium text-sm truncate">{data.label}</span>
        <StatusIcon className="h-4 w-4 ml-auto" />
      </div>

      {data.status === 'running' && (
        <div className="mb-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${data.progress}%` }}
            />
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {data.progress}% complete
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <Badge variant="outline" className="text-xs">
          {data.type}
        </Badge>
        {data.actualDuration && (
          <span>{formatDuration(data.actualDuration)}</span>
        )}
        {data.estimatedDuration && !data.actualDuration && (
          <span>~{formatDuration(data.estimatedDuration)}</span>
        )}
      </div>
    </div>
  )
}

const nodeTypes: NodeTypes = {
  custom: CustomNode,
}

function ExecutionGraphInner({
  dag,
  selectedNodeId,
  onNodeSelect,
  className,
}: ExecutionGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Convert DAG to ReactFlow format
  const reactFlowNodes = useMemo((): Node[] => {
    return dag.nodes.map((node, index) => ({
      id: node.id,
      type: 'custom',
      position: calculateNodePosition(node, index, dag.nodes.length),
      data: {
        label: node.label,
        type: node.type,
        status: node.status,
        progress: node.progress,
        startTime: node.startTime,
        endTime: node.endTime,
        estimatedDuration: node.estimatedDuration,
        actualDuration: node.actualDuration,
      },
      selected: node.id === selectedNodeId,
    }))
  }, [dag.nodes, selectedNodeId])

  const reactFlowEdges = useMemo((): Edge[] => {
    return dag.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: edge.type === 'data_flow',
      style: {
        stroke: edge.type === 'dependency' ? '#6b7280' : '#3b82f6',
        strokeWidth: dag.criticalPath.includes(edge.source) && dag.criticalPath.includes(edge.target) ? 3 : 2,
      },
      label: edge.label,
      labelStyle: {
        fontSize: 12,
        fontWeight: 500,
      },
    }))
  }, [dag.edges, dag.criticalPath])

  useEffect(() => {
    setNodes(reactFlowNodes)
    setEdges(reactFlowEdges)
  }, [reactFlowNodes, reactFlowEdges, setNodes, setEdges])

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      onNodeSelect?.(node.id === selectedNodeId ? undefined : node.id)
    },
    [onNodeSelect, selectedNodeId]
  )

  const onPaneClick = useCallback(() => {
    onNodeSelect?.(undefined)
  }, [onNodeSelect])

  // Calculate node positions in a hierarchical layout
  function calculateNodePosition(node: DAGNode, index: number, totalNodes: number) {
    // Simple grid layout - in a real app, you'd use a proper layout algorithm
    const cols = Math.ceil(Math.sqrt(totalNodes))
    const row = Math.floor(index / cols)
    const col = index % cols

    return {
      x: col * 250 + 50,
      y: row * 150 + 50,
    }
  }

  const criticalPathNodes = dag.criticalPath
  const completedNodes = dag.nodes.filter(n => n.status === 'completed').length
  const totalNodes = dag.nodes.length
  const overallProgress = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0

  return (
    <div
      className={cn(
        "h-full bg-white dark:bg-gray-900 border rounded-lg overflow-hidden",
        isFullscreen && "fixed inset-0 z-50",
        className
      )}
    >
      <div className="h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Strict}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              const status = (node.data as CustomNodeData).status
              switch (status) {
                case 'completed':
                  return '#10b981'
                case 'failed':
                  return '#ef4444'
                case 'running':
                  return '#3b82f6'
                default:
                  return '#6b7280'
              }
            }}
            className="bg-white dark:bg-gray-800"
          />

          {/* Statistics Panel */}
          <Panel position="top-left">
            <Card className="shadow-lg">
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-medium">Execution Progress</div>
                    <Badge variant="outline">{Math.round(overallProgress)}%</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">Completed</div>
                      <div className="font-medium text-green-600">{completedNodes}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Total</div>
                      <div className="font-medium">{totalNodes}</div>
                    </div>
                  </div>
                  {criticalPathNodes.length > 0 && (
                    <div>
                      <div className="text-xs text-muted-foreground">Critical Path</div>
                      <div className="text-xs font-medium text-orange-600">
                        {criticalPathNodes.length} nodes
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </Panel>

          {/* Fullscreen Toggle */}
          <Panel position="top-right">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </Panel>

          {/* Legend */}
          <Panel position="bottom-right">
            <Card className="shadow-lg">
              <CardContent className="p-3">
                <div className="text-xs font-medium mb-2">Legend</div>
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded border-2 border-gray-400"></div>
                    <span>Dependency</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded border-2 border-blue-400"></div>
                    <span>Data Flow</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded border-4 border-orange-400"></div>
                    <span>Critical Path</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  )
}

export function ExecutionGraph(props: ExecutionGraphProps) {
  return (
    <ReactFlowProvider>
      <ExecutionGraphInner {...props} />
    </ReactFlowProvider>
  )
}