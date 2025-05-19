// app/customize/page.tsx

"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import FontCustomizer from "@/components/font-customizer"
import { getFontDownloadUrl } from "@/lib/api"
import { Loader2 } from "lucide-react"

// Client component that uses useSearchParams
function CustomizerContent() {
  const searchParams = useSearchParams()
  const jobId = searchParams.get("jobId")
  const [fontUrl, setFontUrl] = useState<string | null>(null)
  const [boldFontUrl, setBoldFontUrl] = useState<string | null>(null)
  const [lightFontUrl, setLightFontUrl] = useState<string | null>(null)
  
  useEffect(() => {
    if (jobId) {
      // Set the default font URLs
      const url = getFontDownloadUrl(jobId, "500-woff2")
      setFontUrl(url)
      
      const boldUrl = getFontDownloadUrl(jobId, "700-woff2")
      setBoldFontUrl(boldUrl)
      
      const lightUrl = getFontDownloadUrl(jobId, "300-woff2")
      setLightFontUrl(lightUrl)
    }
  }, [jobId])

  // Handle font downloading
  const handleDownload = (format: string) => {
    if (!jobId) return;
    
    try {
      // Get the download URL from the API
      const url = getFontDownloadUrl(jobId, format);
      
      // Open the URL in a new tab to trigger download
      window.open(url, '_blank');
      
      console.log(`Downloading font in format: ${format}`);
    } catch (error) {
      console.error("Error downloading font:", error);
    }
  }

  if (!jobId) {
    return (
      <div className="text-center py-12 text-lg">
        No job ID provided. Please start by generating a font.
      </div>
    );
  }

  return (
    <FontCustomizer
      fontUrl={fontUrl}
      boldFontUrl={boldFontUrl}
      lightFontUrl={lightFontUrl}
      jobId={jobId}
      onRegenerateGlyph={async () => false}
      onUpdateFontSettings={async () => {}}
      onDownload={handleDownload}
    />
  );
}

export default function CustomizePage() {
  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-4">
        <Link href="/" className="inline-flex items-center text-sm text-blue-600 hover:underline">
          ← Back to Home
        </Link>
      </div>
      <Suspense fallback={<div className="flex justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
        <CustomizerContent />
      </Suspense>
    </div>
  )
}