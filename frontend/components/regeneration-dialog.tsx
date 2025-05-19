"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Loader2, Upload } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { regenerateGlyphs } from "@/lib/api"

interface RegenerationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  jobId: string
  glyphsToRegenerate: string[]
  onRegenerationComplete: () => void
}

export default function RegenerationDialog({
  open,
  onOpenChange,
  jobId,
  glyphsToRegenerate,
  onRegenerationComplete,
}: RegenerationDialogProps) {
  const [image, setImage] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const { toast } = useToast()

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImage(e.target.files[0])
    }
  }

  const handleSubmit = async () => {
    if (!image || !jobId || glyphsToRegenerate.length === 0) {
      toast({
        title: "Missing information",
        description: "Please upload an image and select glyphs to regenerate.",
        variant: "destructive",
      })
      return
    }

    setIsUploading(true)

    try {
      await regenerateGlyphs(jobId, image, glyphsToRegenerate)

      toast({
        title: "Regeneration successful",
        description: `Successfully regenerated ${glyphsToRegenerate.length} glyphs.`,
      })

      onRegenerationComplete()
      onOpenChange(false)
    } catch (error) {
      console.error("Error regenerating glyphs:", error)
      toast({
        title: "Regeneration failed",
        description: "There was a problem regenerating the glyphs. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Regenerate Glyphs</DialogTitle>
          <DialogDescription>
            Upload a new image to regenerate the selected glyphs ({glyphsToRegenerate.length}).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div
            className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => document.getElementById("regeneration-image")?.click()}
          >
            <input
              id="regeneration-image"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleImageChange}
            />
            {image ? (
              <div className="space-y-2">
                <img
                  src={URL.createObjectURL(image) || "/placeholder.svg"}
                  alt="Regeneration image"
                  className="max-h-48 mx-auto object-contain"
                />
                <p className="text-sm text-muted-foreground">Click to change image</p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-content space-y-2">
                <Upload className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium">Click to upload</p>
                <p className="text-xs text-muted-foreground">
                  Upload an image with the characters you want to regenerate
                </p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!image || isUploading}>
            {isUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Regenerating...
              </>
            ) : (
              "Regenerate Glyphs"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
