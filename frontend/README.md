# Specify Frontend

Beautiful, modern Next.js 14 frontend for the Specify system with real-time updates and stunning visualizations.

## Features

- **Modern UI**: Built with Next.js 14, TypeScript, and Tailwind CSS
- **Real-time Updates**: WebSocket integration for live progress tracking
- **Beautiful Components**: shadcn/ui component library with custom styling
- **Responsive Design**: Mobile-first design that works on all screen sizes
- **Type Safety**: Full TypeScript integration with strict type checking
- **Performance**: Optimized builds with code splitting and lazy loading

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Running Specify API server (see ../api)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.local.example .env.local
# Edit .env.local with your API URLs
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier
- `npm run type-check` - Run TypeScript type checking

## Project Structure

```
frontend/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page
│   ├── analyze/             # Phase 1: Analysis UI
│   ├── specify/             # Phase 2: Specification UI
│   ├── refine/              # Phase 3: Refinement UI
│   └── execute/             # Phase 4: Execution UI
├── components/
│   ├── ui/                  # shadcn/ui base components
│   ├── analyzer/            # Analysis components
│   ├── specification/       # Spec engine components
│   ├── refinement/          # Refinement UI components
│   ├── execution/           # Execution visualization
│   └── shared/              # Shared components
├── lib/
│   ├── api/                 # API client
│   ├── websocket/           # WebSocket client
│   ├── hooks/               # Custom React hooks
│   └── utils/               # Utilities
└── types/                   # TypeScript types
```

## User Flow

### 1. Analysis Phase (`/analyze`)
- Large prompt input with examples
- Real-time analysis progress
- Display extracted requirements, assumptions, and ambiguities
- Navigate to specification phase

### 2. Specification Phase (`/specify`)
- Show analysis results summary
- Display identified edge cases with severity indicators
- Show contradictions with explanations
- Display completeness gaps with suggestions
- Navigate to refinement phase

### 3. Refinement Phase (`/refine`)
- Interactive suggestion cards
- Approve/reject/modify functionality
- Real-time collaboration features
- Progress tracking
- Navigate to execution phase

### 4. Execution Phase (`/execute`)
- Real-time execution DAG visualization
- Agent status monitoring
- Code output viewer with Monaco editor
- Artifact download functionality

## Key Components

### Core UI Components
- `Button` - Multiple variants with loading states
- `Card` - Flexible container component
- `Badge` - Status and severity indicators
- `Progress` - Real-time progress tracking
- `Alert` - Error and information display

### Specialized Components
- `PromptInput` - Auto-resizing textarea with examples
- `AnalysisResults` - Structured analysis display
- `EdgeCaseCard` - Edge case visualization
- `ExecutionGraph` - React Flow DAG visualization
- `CodeViewer` - Monaco editor integration

### Custom Hooks
- `useAnalysis` - Analysis state management
- `useSpecification` - Specification generation
- `useRefinement` - Refinement session handling
- `useExecution` - Execution tracking
- `useWebSocket` - Real-time updates

## Styling

### Tailwind CSS Configuration
- Custom color palette optimized for the Specify brand
- Dark mode support with system preference detection
- Custom animations and transitions
- Responsive breakpoints

### Component Variants
- Severity-based styling (high/medium/low)
- Status-based colors (success/warning/error/info)
- Interactive states with hover and focus effects

## Real-time Features

### WebSocket Integration
- Automatic connection management with reconnection
- Type-safe event handling
- Session-based subscriptions
- Optimistic UI updates

### Live Updates
- Analysis progress tracking
- Specification generation status
- Agent execution monitoring
- Artifact creation notifications

## Performance Optimizations

- Next.js 14 App Router with automatic code splitting
- Image optimization with Next.js Image component
- Bundle analysis and tree shaking
- Lazy loading for heavy components
- Efficient re-rendering with React.memo and useMemo

## Development

### Code Quality
- ESLint configuration with TypeScript rules
- Prettier for consistent code formatting
- Strict TypeScript configuration
- Git hooks for pre-commit checks

### Testing (Future)
- Jest for unit testing
- React Testing Library for component tests
- Cypress for end-to-end testing
- Storybook for component documentation

## Deployment

### Production Build
```bash
npm run build
npm run start
```

### Environment Variables
- `NEXT_PUBLIC_API_URL` - Specify API base URL
- `NEXT_PUBLIC_WS_URL` - WebSocket server URL
- Feature flags for optional functionality

### Hosting Options
- Vercel (recommended for Next.js)
- Netlify
- Docker container
- Static export for CDN hosting

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the established code style (ESLint + Prettier)
2. Add TypeScript types for new features
3. Update documentation for new components
4. Test on multiple browsers and screen sizes
5. Ensure accessibility standards are met

## License

MIT License - see LICENSE file for details