"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface FontPreviewProps {
  fontUrl: string
  previewText: string
  fontWeight?: "thin" | "regular" | "bold" | number
  fontSize?: number
  tracking?: number
}

export default function FontPreview({
  fontUrl,
  previewText,
  fontWeight = "regular",
  fontSize = 24,
  tracking = 0,
}: FontPreviewProps) {
  const [fontLoaded, setFontLoaded] = useState(false)
  const fontFamily = "GeneratedFont"

  useEffect(() => {
    if (!fontUrl) return

    // Map the fontWeight to a numeric value
    let fontWeightValue
    if (typeof fontWeight === "string") {
      fontWeightValue = fontWeight === "bold" ? 700 : fontWeight === "thin" ? 300 : 400
    } else {
      fontWeightValue = fontWeight
    }

    // Create a new font face
    const font = new FontFace(fontFamily, `url(${fontUrl})`, {
      weight: fontWeightValue.toString(),
      style: "normal",
    })

    // Load the font and add it to the document
    font
      .load()
      .then((loadedFont) => {
        document.fonts.add(loadedFont)
        setFontLoaded(true)
      })
      .catch((error) => {
        console.error("Error loading font:", error)
      })

    return () => {
      // Clean up by removing the font when component unmounts
      try {
        document.fonts.delete(font)
      } catch (e) {
        console.warn("Could not delete font:", e)
      }
    }
  }, [fontUrl, fontWeight])

  if (!fontLoaded) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-6 w-5/6" />
      </div>
    )
  }

  return (
    <Card className="bg-muted/50">
      <CardContent className="p-6">
        <div
          style={{
            fontFamily,
            fontSize: `${fontSize}px`,
            fontWeight:
              typeof fontWeight === "string"
                ? fontWeight === "bold"
                  ? 700
                  : fontWeight === "thin"
                    ? 300
                    : 400
                : fontWeight,
            letterSpacing: `${tracking}em`,
          }}
          className="break-words"
        >
          {previewText || "The quick brown fox jumps over the lazy dog"}
        </div>
      </CardContent>
    </Card>
  )
}
