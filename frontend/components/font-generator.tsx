"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Upload, Loader2, AlertCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import FontCustomizer from "@/components/font-customizer"
import { uploadFontImage, checkFontStatus, getFontDownloadUrl, generateFontFromPrompt } from "@/lib/api"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import SocialProofSection from "@/components/social-proof-section"
import { useRouter } from "next/navigation"

interface FontSettings {
  weights: {
    thin: number
    regular: number
    bold: number
  }
  tracking: number
}

interface FontGeneratorProps {
  droppedFile?: File | null
}

const DEFAULT_SETTINGS: FontSettings = {
  weights: {
    thin: -32,
    regular: 0,
    bold: 32,
  },
  tracking: 0,
}

export default function FontGenerator({ droppedFile }: FontGeneratorProps) {
  const [image, setImage] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("upload")
  const { toast } = useToast()
  const router = useRouter()

  // Add state for font settings at the top level
  const [fontSettings, setFontSettings] = useState<FontSettings>(DEFAULT_SETTINGS)
  // Add state for font URLs with timestamp for cache busting
  const [fontTimestamp, setFontTimestamp] = useState<number>(Date.now())

  // Add state for font description
  const [fontDescription, setFontDescription] = useState("")
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false)

  // Add state for status message
  const [statusMessage, setStatusMessage] = useState<string>("")

  // Add state for smooth progress animation
  const [displayProgress, setDisplayProgress] = useState(0)

  // Add state for redirected job ID
  const [redirectedJobId, setRedirectedJobId] = useState<string | null>(null)

  // Add state for just completed job ID
  const [justCompletedJobId, setJustCompletedJobId] = useState<string | null>(null)

  const prevIsComplete = useRef(isComplete)

  // Handle dropped file from parent component
  useEffect(() => {
    if (droppedFile) {
      setImage(droppedFile)
      setPreviewUrl(URL.createObjectURL(droppedFile))
      setJobId(null)
      setIsComplete(false)
      setProgress(0)
      setDisplayProgress(0)
      setError(null)
    }
  }, [droppedFile])

  // Check for stored job ID on component mount
  useEffect(() => {
    const storedJobId = localStorage.getItem("currentFontJobId")
    if (storedJobId) {
      setJobId(storedJobId)
      checkIfFontIsComplete(storedJobId)
    }
  }, [])

  // Smooth progress animation
  useEffect(() => {
    if (displayProgress < progress) {
      const timer = setTimeout(() => {
        setDisplayProgress((prev) => Math.min(prev + 1, progress))
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [displayProgress, progress])

  const checkIfFontIsComplete = async (id: string) => {
    try {
      const { status, infoMessage } = await checkFontStatus(id)
      if (status === "completed") {
        setIsComplete(true)
        setProgress(100)
        setDisplayProgress(100)
        setStatusMessage(infoMessage || "Font generation complete")
      }
    } catch (error) {
      console.error("Error checking stored font status:", error)
    }
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setImage(file)
      setPreviewUrl(URL.createObjectURL(file))
      setJobId(null)
      setIsComplete(false)
      setProgress(0)
      setDisplayProgress(0)
      setError(null)
    }
  }

  const handleSubmit = async () => {
    if (!image) {
      toast({
        title: "No image selected",
        description: "Please upload an image of a font style first.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const { jobId: newJobId } = await uploadFontImage(image)
      setJobId(newJobId)
      // Store job ID in localStorage
      localStorage.setItem("currentFontJobId", newJobId)
      setIsProcessing(true)
      setProgress(10)
      setDisplayProgress(0)
      setStatusMessage("Starting font generation...")
      toast({
        title: "Processing started",
        description: "Your font is being generated. This may take a minute.",
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred"
      setError(errorMessage)
      toast({
        title: "Error uploading image",
        description: "There was a problem uploading your image. Please try again.",
        variant: "destructive",
      })
      console.error("Error uploading image:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // New function to handle direct font generation from prompt
  const handleGeneratePrompt = async () => {
    if (!fontDescription.trim()) {
      toast({
        title: "Description required",
        description: "Please describe your ideal font.",
        variant: "destructive",
      })
      return
    }

    setIsGeneratingPrompt(true)
    setError(null)

    try {
      // Call the new API endpoint to generate font directly from prompt
      const { jobId: newJobId } = await generateFontFromPrompt(fontDescription)
      setJobId(newJobId)

      // Store job ID in localStorage
      localStorage.setItem("currentFontJobId", newJobId)
      setIsProcessing(true)
      setProgress(10)
      setDisplayProgress(0)
      setStatusMessage("Starting font generation from prompt...")

      toast({
        title: "Font generation started",
        description: "Your font is being generated from your description. This may take a few minutes.",
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred"
      setError(errorMessage)
      toast({
        title: "Error generating font",
        description: "There was a problem generating your font. Please try again.",
        variant: "destructive",
      })
      console.error("Error generating font from prompt:", error)
    } finally {
      setIsGeneratingPrompt(false)
    }
  }

  // Update the checkStatus function to handle missing glyphs and status messages
  const checkStatus = async () => {
    try {
      const { status, infoMessage, availableFormats, missingGlyphs: missingGlyphsData } = await checkFontStatus(jobId || "")

      // Update status message if available
      if (infoMessage) {
        setStatusMessage(infoMessage)
      }

      if (status === "completed") {
        setIsProcessing(false)
        setIsComplete(true)
        setProgress(100)
        setActiveTab("customize")

        // Store missing glyphs data if available
        if (missingGlyphsData && missingGlyphsData.length > 0) {
          console.log("Missing glyphs:", missingGlyphsData)
          localStorage.setItem(`missingGlyphs-${jobId}`, JSON.stringify(missingGlyphsData))
        } else {
          // Clear missing glyphs if none are reported
          localStorage.removeItem(`missingGlyphs-${jobId}`)
        }

        toast({
          title: "Font generated successfully!",
          description: "Your font is ready to preview and customize.",
        })

        // Only set the flag if it wasn't already complete
        if (!isComplete) {
          setJustCompletedJobId(jobId)
        }
      } else {
        // Calculate progress based on available formats
        if (availableFormats) {
          // Define the expected progression of formats
          const progressSteps = [
            "better-prompt", // 20%
            "base-image", // 40%
            "grid-glyphs", // 60%
            "missing-glyphs", // 80%
          ]

          // Find the last completed step
          let lastCompletedStep = -1
          progressSteps.forEach((step, index) => {
            if (availableFormats.includes(step)) {
              lastCompletedStep = index
            }
          })

          // Calculate progress percentage (20% per step, plus 10% initial)
          const calculatedProgress = Math.min(90, 10 + (lastCompletedStep + 1) * 20)
          setProgress(calculatedProgress)
        } else {
          // Fallback to incremental progress
          setProgress((prev) => Math.min(prev + 5, 90))
        }
      }
    } catch (error) {
      console.error("Error checking status:", error)
    }
  }

  // Add a function to reload fonts with a new timestamp
  const handleReloadFonts = () => {
    // Generate a new timestamp for cache busting
    const newTimestamp = Date.now()
    setFontTimestamp(newTimestamp)
    console.log("Reloading fonts with new timestamp:", newTimestamp)

    // Force a refresh of the font status to get updated missing glyphs
    if (jobId) {
      // Clear any cached data
      localStorage.removeItem(`missingGlyphs-${jobId}`)

      // Explicitly check status with fresh data
      setTimeout(() => {
        checkStatus()
      }, 1000) // Small delay to ensure API has latest data
    }
  }

  // Update the handleRegenerateGlyph function to handle multiple glyphs
  const handleRegenerateGlyph = async (glyphUnicodes: string[]) => {
    if (!jobId) return false

    toast({
      title: "Regenerating glyphs",
      description: `Preparing to regenerate ${glyphUnicodes.length} glyph${glyphUnicodes.length !== 1 ? "s" : ""}`,
    })

    try {
      // This function will be called by the RegenerationDialog component
      // The actual API call is handled in handleRegenerationComplete
      return true
    } catch (error) {
      console.error("Error regenerating glyphs:", error)

      toast({
        title: "Error regenerating glyphs",
        description: "There was a problem regenerating the glyphs. Please try again.",
        variant: "destructive",
      })

      return false
    }
  }

  useEffect(() => {
    if (!jobId || !isProcessing) return

    const interval = setInterval(checkStatus, 2000)
    return () => clearInterval(interval)
  }, [jobId, isProcessing])

  // Add this function after the other useEffect hooks
  useEffect(() => {
    // Add clipboard paste event listener
    const handlePaste = (e: ClipboardEvent) => {
      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const file = e.clipboardData.files[0]
        if (file.type.startsWith("image/")) {
          setImage(file)
          setPreviewUrl(URL.createObjectURL(file))
          setJobId(null)
          setIsComplete(false)
          setProgress(0)
          setDisplayProgress(0)
          setError(null)
        }
      }
    }

    // Add the event listener to the document
    document.addEventListener("paste", handlePaste)

    // Clean up the event listener
    return () => {
      document.removeEventListener("paste", handlePaste)
    }
  }, [])

  // Update the font URLs to use the new weight-based format
  // Use the timestamp to bust cache for font URLs
  // Update the font URLs to use all weights from 100 to 900
  const fontUrls = jobId
    ? Array.from({ length: 9 }, (_, i) => {
        const weight = (i + 1) * 100
        return {
          weight,
          ttf: `${getFontDownloadUrl(jobId, `${weight}-ttf`)}&ts=${fontTimestamp}`,
          otf: `${getFontDownloadUrl(jobId, `${weight}-otf`)}&ts=${fontTimestamp}`,
          woff2: `${getFontDownloadUrl(jobId, `${weight}-woff2`)}&ts=${fontTimestamp}`,
        }
      })
    : []

  // For backward compatibility and simpler access
  const ttfDownloadUrl = jobId ? `${getFontDownloadUrl(jobId, "400-ttf")}&ts=${fontTimestamp}` : null
  const otfDownloadUrl = jobId ? `${getFontDownloadUrl(jobId, "400-otf")}&ts=${fontTimestamp}` : null
  const boldTtfDownloadUrl = jobId ? `${getFontDownloadUrl(jobId, "700-ttf")}&ts=${fontTimestamp}` : null
  const lightTtfDownloadUrl = jobId ? `${getFontDownloadUrl(jobId, "200-ttf")}&ts=${fontTimestamp}` : null
  const woff2DownloadUrl = jobId ? `${getFontDownloadUrl(jobId, "400-woff2")}&ts=${fontTimestamp}` : null

  // Update the handleUpdateFontSettings function
  const handleUpdateFontSettings = async (settings: FontSettings) => {
    // Store settings in component state
    setFontSettings(settings)

    // This would call your API to update font settings
    console.log("Updating font settings:", settings)

    // In a real implementation, this would send the settings to your backend
    return Promise.resolve()
  }

  // Update the handleDownload function to use the new format structure
  const handleDownload = (format: string) => {
    let downloadUrl

    // Check if format includes a weight prefix like "300-ttf"
    if (format.includes("-")) {
      downloadUrl = jobId ? `${getFontDownloadUrl(jobId, format)}&ts=${fontTimestamp}` : null
    } else {
      // Legacy format handling
      switch (format) {
        case "ttf":
          downloadUrl = ttfDownloadUrl
          break
        case "otf":
          downloadUrl = otfDownloadUrl
          break
        case "bold-ttf":
          downloadUrl = boldTtfDownloadUrl
          break
        case "light-ttf":
          downloadUrl = lightTtfDownloadUrl
          break
        case "woff2":
          downloadUrl = woff2DownloadUrl
          break
        default:
          downloadUrl = ttfDownloadUrl
      }
    }

    if (downloadUrl) {
      window.open(downloadUrl, "_blank")
    }
  }

  // Update the font URLs to include console logging for debugging
  useEffect(() => {
    if (jobId && isComplete) {
      console.log("Font URLs:", {
        regular: ttfDownloadUrl,

      })
    }
  }, [jobId, isComplete, ttfDownloadUrl])

  // Function to load an example font
  const handleLoadExampleFont = (exampleJobId: string) => {
    if (isProcessing) {
      toast({
        title: "Font generation in progress",
        description: "Please wait for the current font to finish generating before loading an example.",
        variant: "destructive",
      })
      return
    }

    setJobId(exampleJobId)
    localStorage.setItem("currentFontJobId", exampleJobId)
    setIsComplete(true)
    setProgress(100)
    setDisplayProgress(100)
    setActiveTab("customize")

    toast({
      title: "Example font loaded",
      description: "You can now customize and download this example font.",
    })
  }

  useEffect(() => {
    if (justCompletedJobId) {
      router.push(`/customize?jobId=${justCompletedJobId}`);
      setJustCompletedJobId(null); // Reset so it doesn't trigger again
    }
  }, [justCompletedJobId, router]);

  return (
    <div className="space-y-8">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="upload">Create Font</TabsTrigger>
          <TabsTrigger
            value="customize"
            disabled={!isComplete}
            onClick={() => {
              if (isComplete && jobId) {
                router.push(`/customize?jobId=${jobId}`);
              }
            }}
          >
            Customize
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-6">
                {/* Describe Font Section - Now at the top */}
                <div className="space-y-2">
                  <Label htmlFor="font-description" className="text-lg">
                    Describe your ideal font
                  </Label>
                  <Textarea
                    id="font-description"
                    placeholder="Example: A modern, geometric sans-serif font with clean lines and balanced proportions"
                    rows={3}
                    value={fontDescription}
                    onChange={(e) => setFontDescription(e.target.value)}
                    className="resize-none"
                    disabled={isGeneratingPrompt || isProcessing}
                  />
                  <Button
                    onClick={handleGeneratePrompt}
                    disabled={isGeneratingPrompt || isProcessing || !fontDescription.trim()}
                    className="w-full mt-2"
                  >
                    {isGeneratingPrompt ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating Font...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Generate Font from Description
                      </>
                    )}
                  </Button>
                  <Alert className="mt-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Our AI will generate a font based on your description. This may take a few minutes.
                    </AlertDescription>
                  </Alert>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">Or</span>
                  </div>
                </div>

                {/* Upload Image Section - Now below */}
                <div className="space-y-2">
                  <Label htmlFor="font-image" className="text-lg">
                    Upload Font Image
                  </Label>
                  <div
                    className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:bg-muted/50 transition-colors ${
                      isProcessing ? "opacity-50 pointer-events-none" : ""
                    }`}
                    onClick={() => !isProcessing && document.getElementById("font-image")?.click()}
                  >
                    <Input
                      id="font-image"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageChange}
                      disabled={isProcessing}
                    />
                    {previewUrl ? (
                      <div className="space-y-2">
                        <img
                          src={previewUrl || "/placeholder.svg"}
                          alt="Font preview"
                          className="max-h-48 mx-auto object-contain"
                        />
                        <p className="text-sm text-muted-foreground">
                          {isProcessing
                            ? "Processing image..."
                            : "Click to change image or drag and drop a new image anywhere on the page"}
                        </p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-content space-y-2">
                        <Upload className="h-8 w-8 text-muted-foreground" />
                        <p className="text-sm font-medium">Drag and drop anywhere or click to upload</p>
                        <p className="text-xs text-muted-foreground">Upload an image of your desired font style</p>
                      </div>
                    )}
                  </div>

                  {error && (
                    <Alert variant="destructive" className="mt-4">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Error</AlertTitle>
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <Button onClick={handleSubmit} disabled={!image || isLoading || isProcessing} className="w-full mt-4">
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Uploading Image...
                      </>
                    ) : isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing Font...
                      </>
                    ) : (
                      "Generate Font from Image"
                    )}
                  </Button>

                  {isProcessing && (
                    <div className="space-y-2 mt-4">
                      <Progress value={displayProgress} className="h-2" />
                      <div className="flex justify-between items-center">
                        <p className="text-xs text-muted-foreground">
                          {statusMessage || "Processing your font. This may take a few minutes..."}
                        </p>
                        <p className="text-xs font-medium">{displayProgress}%</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Social Proof Section */}
          <div className="mt-12">
            <SocialProofSection onExampleClick={handleLoadExampleFont} />
          </div>
        </TabsContent>

        <TabsContent value="customize">
          {isComplete && jobId && ttfDownloadUrl && (
            <FontCustomizer
              fontUrl={ttfDownloadUrl}
              boldFontUrl={boldTtfDownloadUrl}
              lightFontUrl={lightTtfDownloadUrl}
              jobId={jobId}
              onRegenerateGlyph={handleRegenerateGlyph}
              onUpdateFontSettings={handleUpdateFontSettings}
              onDownload={handleDownload}
              settings={fontSettings}
              onReloadFonts={handleReloadFonts}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
