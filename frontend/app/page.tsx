"use client"

import type React from "react"

import { useState } from "react"
import FontGenerator from "@/components/font-generator"

export default function Home() {
  const [dragActive, setDragActive] = useState(false)
  const [droppedFile, setDroppedFile] = useState<File | null>(null)

  // Handle drag events
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  // Handle drop event
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.type.startsWith("image/")) {
        setDroppedFile(file)
      }
    }
  }

  // Pass the dropped file to the FontGenerator component
  return (
    <div
      className={`min-h-screen ${dragActive ? "bg-blue-50" : ""}`}
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
    >
      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">AI Font Generator</h1>
          <p className="text-lg text-muted-foreground">
            Upload an image of a font style, customize it, and download a full font
          </p>
          {dragActive && (
            <div className="fixed inset-0 bg-blue-500/10 backdrop-blur-sm flex items-center justify-center z-50 pointer-events-none">
              <div className="bg-white p-8 rounded-lg shadow-lg text-center">
                <p className="text-xl font-bold">Drop image here</p>
              </div>
            </div>
          )}
        </div>

        <FontGenerator droppedFile={droppedFile} />
      </main>
    </div>
  )
}
