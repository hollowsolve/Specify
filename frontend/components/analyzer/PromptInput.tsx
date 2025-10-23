'use client'

import { useState, useRef, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Lightbulb,
  Copy,
  RotateCcw,
  Wand2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

interface ExamplePrompt {
  title: string
  category: string
  prompt: string
  tags: string[]
}

interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  minRows?: number
  maxRows?: number
  showExamples?: boolean
  showEnhancements?: boolean
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    title: "E-commerce Platform",
    category: "Web Application",
    prompt: "Build a modern e-commerce platform where users can browse products with advanced filtering (price, category, brand, ratings), add items to cart with quantity selection, apply discount codes, make secure payments via multiple methods (credit card, PayPal, Apple Pay), track order status in real-time, and leave product reviews. Include an admin dashboard for inventory management, order processing, analytics dashboard with sales metrics, and customer management. Support mobile responsiveness, SEO optimization, and integration with shipping providers.",
    tags: ["ecommerce", "web", "mobile", "payments", "admin"]
  },
  {
    title: "Collaborative Task Management",
    category: "Productivity",
    prompt: "Create a comprehensive task management application where teams can create projects with customizable workflows, assign tasks to members with priority levels and due dates, track progress through kanban boards, attach files and images to tasks, set up automated notifications and reminders, generate time tracking reports, and collaborate through comments and mentions. Include calendar integration, Gantt chart visualization, team performance analytics, and mobile app synchronization.",
    tags: ["productivity", "collaboration", "project-management", "mobile"]
  },
  {
    title: "AI-Powered Learning Platform",
    category: "Education",
    prompt: "Develop an adaptive learning platform that uses AI to personalize educational content based on student performance and learning style. Include features for course creation with multimedia content (videos, interactive quizzes, simulations), progress tracking with detailed analytics, peer collaboration tools, automated grading system, discussion forums, live virtual classrooms with video conferencing, mobile learning app, and integration with LMS systems. Support multiple languages and accessibility features.",
    tags: ["ai", "education", "adaptive", "multimedia", "accessibility"]
  },
  {
    title: "Healthcare Management System",
    category: "Healthcare",
    prompt: "Build a comprehensive healthcare management system for clinics and hospitals with patient registration and electronic health records (EHR), appointment scheduling with automated reminders, prescription management with drug interaction checking, billing and insurance processing, inventory management for medical supplies, staff scheduling and payroll, telemedicine capabilities with video consultations, lab results integration, reporting and analytics dashboard, and HIPAA-compliant security measures.",
    tags: ["healthcare", "ehr", "telemedicine", "hipaa", "billing"]
  },
  {
    title: "IoT Smart Home Platform",
    category: "IoT",
    prompt: "Create a smart home automation platform that connects and controls various IoT devices (lights, thermostats, security cameras, door locks, appliances) through a unified interface. Include features for custom automation rules and scenes, energy usage monitoring and optimization, security alerts and notifications, voice control integration (Alexa, Google Assistant), mobile app for remote control, data analytics for usage patterns, device health monitoring, and support for multiple communication protocols (WiFi, Zigbee, Z-Wave).",
    tags: ["iot", "smart-home", "automation", "mobile", "voice-control"]
  }
]

export function PromptInput({
  value,
  onChange,
  placeholder = "Describe your software requirements in detail...",
  disabled = false,
  minRows = 8,
  maxRows = 20,
  showExamples = true,
  showEnhancements = true,
}: PromptInputProps) {
  const [showExamplesList, setShowExamplesList] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const categories = Array.from(new Set(EXAMPLE_PROMPTS.map(p => p.category)))
  const filteredPrompts = selectedCategory
    ? EXAMPLE_PROMPTS.filter(p => p.category === selectedCategory)
    : EXAMPLE_PROMPTS

  useEffect(() => {
    adjustTextareaHeight()
  }, [value])

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    const scrollHeight = textarea.scrollHeight
    const lineHeight = 24 // Approximate line height
    const minHeight = minRows * lineHeight
    const maxHeight = maxRows * lineHeight

    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight)
    textarea.style.height = `${newHeight}px`
  }

  const handlePromptSelect = (prompt: string) => {
    onChange(prompt)
    setShowExamplesList(false)
  }

  const handleCopyPrompt = async (prompt: string) => {
    try {
      await navigator.clipboard.writeText(prompt)
      // You could add a toast notification here
    } catch (error) {
      console.error('Failed to copy prompt:', error)
    }
  }

  const handleClear = () => {
    onChange('')
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  const enhancePrompt = () => {
    // This would integrate with an AI service to enhance the prompt
    // For now, we'll just add some enhancement suggestions
    const enhancements = [
      "Consider adding specific user roles and permissions",
      "Include performance and scalability requirements",
      "Specify security and compliance needs",
      "Define integration requirements with external systems",
      "Outline mobile and cross-platform support"
    ]

    const currentPrompt = value.trim()
    if (currentPrompt) {
      const enhancedPrompt = `${currentPrompt}\n\nAdditional considerations:\n${enhancements.map(e => `- ${e}`).join('\n')}`
      onChange(enhancedPrompt)
    }
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            "resize-none transition-all duration-200",
            "focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            "placeholder:text-muted-foreground/70"
          )}
          style={{ minHeight: `${minRows * 24}px` }}
        />

        {/* Character count */}
        <div className="absolute bottom-3 right-3 text-xs text-muted-foreground bg-background/80 backdrop-blur-sm px-2 py-1 rounded">
          {value.length.toLocaleString()} characters
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {showExamples && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExamplesList(!showExamplesList)}
              disabled={disabled}
            >
              <Lightbulb className="h-4 w-4 mr-2" />
              Examples
              {showExamplesList ? (
                <ChevronUp className="h-4 w-4 ml-2" />
              ) : (
                <ChevronDown className="h-4 w-4 ml-2" />
              )}
            </Button>
          )}
          {value && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              disabled={disabled}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Clear
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {showEnhancements && value.trim() && (
            <Button
              variant="outline"
              size="sm"
              onClick={enhancePrompt}
              disabled={disabled}
            >
              <Wand2 className="h-4 w-4 mr-2" />
              Enhance
            </Button>
          )}
        </div>
      </div>

      {/* Examples List */}
      {showExamplesList && (
        <Card className="border-dashed">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Example Prompts</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant={selectedCategory === null ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedCategory(null)}
                >
                  All
                </Button>
                {categories.map((category) => (
                  <Button
                    key={category}
                    variant={selectedCategory === category ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedCategory(category)}
                  >
                    {category}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredPrompts.map((example, index) => (
                <div
                  key={index}
                  className="group p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => handlePromptSelect(example.prompt)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-medium group-hover:text-blue-600 transition-colors">
                        {example.title}
                      </h4>
                      <p className="text-sm text-muted-foreground">{example.category}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCopyPrompt(example.prompt)
                      }}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>

                  <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
                    {example.prompt}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    {example.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}