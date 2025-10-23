import type { Metadata } from 'next'

// Removed globals.css import to avoid Tailwind issues

export const metadata: Metadata = {
  title: 'Specify - AI-Powered Software Specification System',
  description: 'Transform ideas into comprehensive software specifications with AI-powered analysis, refinement, and execution.',
  keywords: ['AI', 'software specification', 'requirements analysis', 'automated development'],
  authors: [{ name: 'Specify Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0, padding: 0, fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        <main>{children}</main>
      </body>
    </html>
  )
}