"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ExternalLink } from "lucide-react"
import Link from "next/link"

interface SocialProofSectionProps {
  onExampleClick: (jobId: string) => void
}

// Example fonts with their job IDs
const EXAMPLE_FONTS = [
  {
    id: "elegant_font",
    name: "Elegant Font",
    description: "A flowing, elegant script font generated with AI.",
    prompt: "Elegant flowing script with beautiful curves and flourishes",
    previewImage: "/examples/elegant_font/base_image.png",
    fontUrl: "/examples/elegant_font/MyFont-400.woff2",
    fontFamily: "ElegantFont",
    jobId: "font-example-2",
  },
  {
    id: "mono_font",
    name: "Mono Font",
    description: "A modern, monospaced font for code and UI.",
    prompt: "Modern geometric monospaced font for code and UI",
    previewImage: "/examples/mono_font/base_image.png",
    fontUrl: "/examples/mono_font/MyFont-400.woff2",
    fontFamily: "MonoFont",
    jobId: "font-example-1",
  },
  {
    id: "playful_font",
    name: "Playful Font",
    description: "A fun, playful display font with unique character.",
    prompt: "Playful display font with quirky shapes and friendly curves",
    previewImage: "/examples/playful_font/base_image.png",
    fontUrl: "/examples/playful_font/MyFont-400.woff2",
    fontFamily: "PlayfulFont",
    jobId: "font-example-3",
  },
]

export default function SocialProofSection({ onExampleClick }: SocialProofSectionProps) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Join hundreds of designers creating custom fonts</h2>
        <p className="text-muted-foreground">Get inspired by these examples or create your own unique font</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {EXAMPLE_FONTS.map((font) => (
          <Card key={font.id} className="overflow-hidden hover:shadow-md transition-shadow">
            <style>
              {`
                @font-face {
                  font-family: '${font.fontFamily}';
                  src: url('${font.fontUrl}') format('woff2');
                  font-weight: 500;
                  font-style: normal;
                }
              `}
            </style>
            <div className="aspect-video relative overflow-hidden bg-muted">
              <img
                src={font.previewImage}
                alt={`${font.name} preview`}
                className="object-cover w-full h-full"
              />
            </div>
            <CardContent className="p-4">
              <h3 className="font-bold text-lg mb-1">{font.name}</h3>
              <p className="text-sm text-muted-foreground mb-3">{font.description}</p>
              <div className="flex flex-col space-y-2">
                <div className="text-xs bg-muted p-2 rounded-md">
                  <span
                    className="font-mono text-muted-foreground"
                    style={{ fontFamily: font.fontFamily }}
                  >
                    {font.prompt}
                  </span>
                </div>
                <Button asChild variant="outline" size="sm" className="mt-2">
                  <Link href={`/customize?jobId=${font.jobId}&example=1`}>
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Try this font
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
