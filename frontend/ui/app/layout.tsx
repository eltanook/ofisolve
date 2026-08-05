import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ThemeProvider } from 'next-themes'

import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter"
});

export const metadata: Metadata = {
  title: 'OfiSolve - Inteligencia Artificial para Escribanías',
  description: 'Sistema de IA especializado para Escribanías y Notarías en Argentina',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/logo-ofisolve.png',
        type: 'image/png',
      },
    ],
    apple: '/logo-ofisolve.png',
  },
}

import { Toaster } from "sonner"
import QueryProvider from "@/components/query-provider"

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`} suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          storageKey="ofisolve-theme"
        >
          <QueryProvider>
            {children}
            <Toaster position="top-right" richColors />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
