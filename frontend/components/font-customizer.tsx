"use client"

import { useState, useEffect, useCallback } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  AlertCircle,
  RefreshCw,
  Bold,
  Type,
  Loader2,
  Download,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/hooks/use-toast"
import { checkFontStatus, getFontDownloadUrl, regenerateMissingGlyphs } from "@/lib/api"
import PremiumFontPackage from "@/components/premium-font-package"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useSearchParams, useRouter } from "next/navigation"

interface FontCustomizerProps {
  fontUrl: string | null
  boldFontUrl: string | null
  lightFontUrl: string | null
  jobId: string | null
  onRegenerateGlyph: (glyphUnicodes: string[]) => Promise<boolean>
  onUpdateFontSettings: (settings: FontSettings) => Promise<void>
  onDownload: (format: string) => void
  settings?: FontSettings
  onSettingsChange?: (settings: FontSettings) => Promise<void>
  onReloadFonts?: () => void
}

interface GlyphData {
  unicode: string
  character: string
  isAvailable: boolean
  flagged?: boolean
  selected?: boolean
}

interface FontSettings {
  weights: {
    thin: number
    regular: number
    bold: number
  }
  tracking: number
}

const DEFAULT_SETTINGS: FontSettings = {
  weights: {
    thin: -32,
    regular: 0,
    bold: 32,
  },
  tracking: 0,
}

// Latin alphabet and numbers
const BASIC_GLYPHS: GlyphData[] = [
  ..."ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789".split("").map((char) => ({
    unicode: char.charCodeAt(0).toString(16).padStart(4, "0").toUpperCase(),
    character: char,
    isAvailable: true,
    flagged: false,
    selected: false,
  })),
  ...".,!?@#$%&".split("").map((char) => ({
    unicode: char.charCodeAt(0).toString(16).padStart(4, "0").toUpperCase(),
    character: char,
    isAvailable: true,
    flagged: false,
    selected: false,
  })),
]

// Define all available font weights
const AVAILABLE_WEIGHTS = [100, 200, 300, 400, 500, 600, 700, 800, 900]

// Polls the font status endpoint until regeneration is complete, failed, or times out
const pollFontRegenerationStatus = async (
  jobId: string,
  { interval = 3000, timeout = 10 * 60 * 1000 } = {} // 10 minutes
): Promise<"completed" | "failed" | "timeout"> => {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const status = await checkFontStatus(jobId);
      // Check both possible fields for completion
      if (status?.status === "completed") {
        return "completed";
      }
      if (status?.status === "failed") {
        return "failed";
      }
    } catch (e) {
      // Optionally handle error, or just continue polling
    }
    await new Promise((res) => setTimeout(res, interval));
  }
  return "timeout";
};

export default function FontCustomizer({
  fontUrl,
  jobId,
  onRegenerateGlyph,
  onUpdateFontSettings,
  onDownload,
  settings: propSettings,
  onSettingsChange,
  onReloadFonts,
}: FontCustomizerProps) {
  const [settings, setSettings] = useState<FontSettings>(propSettings || DEFAULT_SETTINGS)
  const [previewText, setPreviewText] = useState("Yo, You can type anything here! Click me to edit")
  const [previewSize, setPreviewSize] = useState(36)
  const [fontWeight, setFontWeight] = useState(500)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [detectedGlyphs, setDetectedGlyphs] = useState<GlyphData[]>([...BASIC_GLYPHS])
  const [fontLoaded, setFontLoaded] = useState(false)
  const [fontLoadErrors, setFontLoadErrors] = useState<{ [key: string]: string }>({})
  const [activeTabKey, setActiveTabKey] = useState<string>("preview")
  const [missingGlyphsLoaded, setMissingGlyphsLoaded] = useState(false)
  const [isCheckingMissingGlyphs, setIsCheckingMissingGlyphs] = useState(false)
  const [showRegenerationSuccess, setShowRegenerationSuccess] = useState(false)
  const [fontLoadRetries, setFontLoadRetries] = useState(0)
  const { toast } = useToast()

  const [isPremiumPurchased, setIsPremiumPurchased] = useState(false)
  const [loadedFontWeights, setLoadedFontWeights] = useState<Record<number, boolean>>({})
  const [isLoadingFonts, setIsLoadingFonts] = useState(false)

  // New state for direct regeneration
  const [isDirectRegenerating, setIsDirectRegenerating] = useState(false)
  const [regenerationProgress, setRegenerationProgress] = useState(0)

  const searchParams = useSearchParams();
  const router = useRouter();

  // Apply settings when they change
  useEffect(() => {
    if (fontUrl) {
      const applySettings = async () => {
        try {
          await onUpdateFontSettings(settings)
        } catch (error) {
          console.error("Failed to update font settings:", error)
        }
      }

      applySettings()
    }
  }, [settings, fontUrl, onUpdateFontSettings])

  // Load fonts with retry mechanism
  useEffect(() => {
    const MAX_RETRIES = 3
    const RETRY_DELAY = 1000 // 1 second

    const loadFont = async (url: string | null, fontFamily: string, setLoaded: (loaded: boolean) => void) => {
      if (!url) return null

      try {
        console.log(`Loading ${fontFamily} from ${url}`)
        const font = new FontFace(fontFamily, `url(${url})`, {
          display: "swap",
          style: "normal",
          weight: "normal",
        })

        const loadedFont = await font.load()
        document.fonts.add(loadedFont)
        setLoaded(true)
        setFontLoadErrors((prev) => ({ ...prev, [fontFamily]: "" }))
        return font
      } catch (error) {
        console.error(`Error loading ${fontFamily}:`, error)
        setFontLoadErrors((prev) => ({
          ...prev,
          [fontFamily]: error instanceof Error ? error.message : "Unknown error",
        }))
        return null
      }
    }

    const fonts: Array<FontFace | null> = []

    const loadFonts = async () => {
      if (fontLoadRetries >= MAX_RETRIES) {
        console.log("Max font load retries reached, giving up")
        return
      }

      let loadSuccess = false

      if (fontUrl) {
        const regularFont = await loadFont(fontUrl, "GeneratedFont", setFontLoaded)
        if (regularFont) {
          fonts.push(regularFont)
          loadSuccess = true
        }
      }

      if (!loadSuccess && fontUrl) {
        console.log(`Font load failed, retrying in ${RETRY_DELAY}ms (attempt ${fontLoadRetries + 1}/${MAX_RETRIES})`)
        setTimeout(() => {
          setFontLoadRetries((prev) => prev + 1)
        }, RETRY_DELAY)
      }
    }

    loadFonts()

    // Cleanup
    return () => {
      fonts.forEach((font) => {
        if (font) {
          try {
            document.fonts.delete(font)
          } catch (e) {
            console.warn("Could not delete font:", e)
          }
        }
      })
    }
  }, [fontUrl, fontLoadRetries])

  // Sync settings with props
  useEffect(() => {
    if (propSettings) {
      setSettings(propSettings)
    }
  }, [propSettings])

  // Check if user has purchased premium package
  useEffect(() => {
    if (jobId) {
      const purchased = localStorage.getItem(`premium-purchased-${jobId}`) === "true"
      setIsPremiumPurchased(purchased)
    }
  }, [jobId])

  // Function to load a specific font weight
  const loadFontWeight = useCallback(
    async (weight: number) => {
      if (!jobId || loadedFontWeights[weight] || isLoadingFonts) return

      try {
        setIsLoadingFonts(true)
        const fontUrl = getFontDownloadUrl(jobId, `${weight}-woff2`)
        console.log(`Loading font weight ${weight} from ${fontUrl}`)

        const fontFamily = `GeneratedFont-${weight}`
        const font = new FontFace(fontFamily, `url(${fontUrl})`, {
          weight: weight.toString(),
          style: "normal",
        })

        const loadedFont = await font.load()
        document.fonts.add(loadedFont)

        setLoadedFontWeights((prev) => ({
          ...prev,
          [weight]: true,
        }))

        console.log(`Successfully loaded font weight ${weight}`)
      } catch (error) {
        console.error(`Error loading font weight ${weight}:`, error)
        toast({
          title: "Font Loading Error",
          description: `Could not load font weight ${weight}. Using fallback.`,
          variant: "destructive",
        })
      } finally {
        setIsLoadingFonts(false)
      }
    },
    [jobId, loadedFontWeights, isLoadingFonts, toast],
  )

  // Load all font weights when the component mounts
  useEffect(() => {
    if (!jobId || !fontLoaded) return

    const loadAllFontWeights = async () => {
      // Start with the current weight
      await loadFontWeight(fontWeight)

      // Then load other weights in the background
      for (const weight of AVAILABLE_WEIGHTS) {
        if (weight !== fontWeight) {
          await loadFontWeight(weight)
        }
      }
    }

    loadAllFontWeights()
  }, [jobId, fontLoaded, fontWeight, loadFontWeight])

  // Function to check for missing glyphs
  const checkForMissingGlyphs = useCallback(async () => {
    if (!jobId || !fontLoaded || isCheckingMissingGlyphs) return

    setIsCheckingMissingGlyphs(true)

    try {
      // Try to get missing glyphs data from the API with cache busting
      const { missingGlyphs: missingGlyphsData } = await checkFontStatus(jobId)

      console.log("Checking for missing glyphs, received:", missingGlyphsData)

      // Start with all basic glyphs as available and not selected
      const updatedGlyphs = [...BASIC_GLYPHS].map((glyph) => ({
        ...glyph,
        isAvailable: true,
        flagged: false,
        selected: false,
      }))

      if (missingGlyphsData && missingGlyphsData.length > 0) {
        console.log("Loaded missing glyphs from API:", missingGlyphsData)

        // Store in localStorage for future reference
        localStorage.setItem(`missingGlyphs-${jobId}`, JSON.stringify(missingGlyphsData))

        // Mark the missing glyphs from the API
        missingGlyphsData.forEach((char: string) => {
          // Find if this glyph exists in our list
          const index = updatedGlyphs.findIndex((g) => g.character === char)

          if (index >= 0) {
            // Mark as unavailable and selected for regeneration
            updatedGlyphs[index].isAvailable = false
            updatedGlyphs[index].selected = true
          } else {
            // Add to our list if not found
            const unicode = char.codePointAt(0)?.toString(16).padStart(4, "0").toUpperCase() || ""
            updatedGlyphs.push({
              unicode,
              character: char,
              isAvailable: false,
              flagged: false,
              selected: true,
            })
          }
        })
      } else {
        // No missing glyphs found, all glyphs are available
        console.log("No missing characters found")
        localStorage.removeItem(`missingGlyphs-${jobId}`)
      }

      setDetectedGlyphs(updatedGlyphs)
      setMissingGlyphsLoaded(true)
    } catch (error) {
      console.error("Error checking for missing glyphs:", error)

      // Fallback to localStorage if API check fails
      const storedMissingGlyphs = localStorage.getItem(`missingGlyphs-${jobId}`)

      if (storedMissingGlyphs) {
        try {
          const missingGlyphsData = JSON.parse(storedMissingGlyphs)
          console.log("Loaded missing glyphs from localStorage:", missingGlyphsData)

          // Start with all basic glyphs as available
          const updatedGlyphs = [...BASIC_GLYPHS].map((glyph) => ({
            ...glyph,
            isAvailable: true,
            flagged: false,
            selected: false,
          }))

          // Handle the array of characters format from the API
          missingGlyphsData.forEach((char: string) => {
            // Find if this glyph exists in our list
            const index = updatedGlyphs.findIndex((g) => g.character === char)

            if (index >= 0) {
              // Mark as unavailable and selected for regeneration
              updatedGlyphs[index].isAvailable = false
              updatedGlyphs[index].selected = true
            } else {
              // Add to our list if not found
              const unicode = char.codePointAt(0)?.toString(16).padStart(4, "0").toUpperCase() || ""
              updatedGlyphs.push({
                unicode,
                character: char,
                isAvailable: false,
                flagged: false,
                selected: true,
              })
            }
          })

          setDetectedGlyphs(updatedGlyphs)
        } catch (error) {
          console.error("Error parsing missing glyphs data:", error)
          // Fallback to all glyphs available
          setDetectedGlyphs([...BASIC_GLYPHS])
        }
      } else {
        // Fallback to all glyphs available
        setDetectedGlyphs([...BASIC_GLYPHS])
      }

      setMissingGlyphsLoaded(true)
    } finally {
      setIsCheckingMissingGlyphs(false)
    }
  }, [jobId, fontLoaded, isCheckingMissingGlyphs])

  // Load missing glyphs
  useEffect(() => {
    if (jobId && fontLoaded && !missingGlyphsLoaded) {
      checkForMissingGlyphs()
    }
  }, [jobId, fontLoaded, missingGlyphsLoaded, checkForMissingGlyphs])

  // Simulated progress for regeneration
  useEffect(() => {
    if (isDirectRegenerating && regenerationProgress < 95) {
      const timer = setTimeout(() => {
        setRegenerationProgress((prev) => Math.min(prev + 5, 95))
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isDirectRegenerating, regenerationProgress])

  // Direct regeneration function - new implementation
  const handleDirectRegeneration = async () => {
    if (!jobId) return;

    const selectedGlyphUnicodes = detectedGlyphs.filter((glyph) => glyph.selected).map((glyph) => glyph.character);

    if (selectedGlyphUnicodes.length === 0) {
      toast({
        title: "No characters selected",
        description: "Please select at least one character to regenerate.",
        variant: "destructive",
      });
      return;
    }

    setIsDirectRegenerating(true);
    setRegenerationProgress(5);

    try {
      const glyphsString = selectedGlyphUnicodes.join(",");
      const result = await regenerateMissingGlyphs(jobId, glyphsString);

      toast({
        title: "Regeneration started",
        description: result.message || `Regenerating ${selectedGlyphUnicodes.length} characters. This may take a while.`,
      });

      // Poll for regeneration status
      let progress = 10;
      setRegenerationProgress(progress);

      const progressInterval = setInterval(() => {
        progress = Math.min(progress + 2, 95);
        setRegenerationProgress(progress);
      }, 3000);

      const pollResult = await pollFontRegenerationStatus(jobId);

      clearInterval(progressInterval);

      if (pollResult === "completed") {
        setRegenerationProgress(100);
        await handleRegenerationComplete();
        toast({
          title: "Regeneration complete",
          description: "The selected glyphs have been regenerated successfully.",
        });
      } else if (pollResult === "timeout") {
        toast({
          title: "Regeneration timed out",
          description: "The regeneration process took too long. Please try again.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Regeneration failed",
          description: "There was a problem regenerating the characters. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error regenerating characters:", error);
      toast({
        title: "Regeneration failed",
        description: error instanceof Error ? error.message : "There was a problem regenerating the characters. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsDirectRegenerating(false);
      setRegenerationProgress(0);
    }
  };

  // Handle regeneration completion
  const handleRegenerationComplete = async () => {
    if (!jobId) return

    setIsRegenerating(true)

    try {
      // First, reload the fonts with a new timestamp
      if (onReloadFonts) {
        onReloadFonts()
      }

      // Reset font load retries to trigger a fresh load
      setFontLoadRetries(0)

      // Reset missing glyphs loaded flag to force a refresh
      setMissingGlyphsLoaded(false)

      // Clear the detected glyphs to avoid stale data
      setDetectedGlyphs(
        [...BASIC_GLYPHS].map((glyph) => ({
          ...glyph,
          isAvailable: true,
          flagged: false,
          selected: false,
        })),
      )


      // Clear loaded font weights to force reload
      setLoadedFontWeights({})

      // Wait for API to process the changes
      await new Promise((resolve) => setTimeout(resolve, 2000))

      // Explicitly check for missing glyphs again
      await checkForMissingGlyphs()

      // Show success message
      setShowRegenerationSuccess(true)

      // Hide success message after 5 seconds
      setTimeout(() => {
        setShowRegenerationSuccess(false)
      }, 5000)
    } catch (error) {
      console.error("Failed to complete regeneration:", error)

      toast({
        title: "Regeneration issue",
        description: "There was a problem completing the regeneration. Some glyphs may still be missing.",
        variant: "destructive",
      })
    } finally {
      setIsRegenerating(false)
    }
  }

  // Update the handleWeightChange function
  const handleWeightChange = (type: "thin" | "regular" | "bold", value: number) => {
    const newSettings = {
      ...settings,
      weights: {
        ...settings.weights,
        [type]: value,
      },
    }
    setSettings(newSettings)

    // Notify parent component of settings change
    if (onSettingsChange) {
      onSettingsChange(newSettings)
    }
  }

  // Update the handleFontWeightChange function to directly use the weight value
  const handleFontWeightChange = (value: number[]) => {
    // Round to nearest 100
    const roundedWeight = Math.round(value[0] / 100) * 100

    // Ensure weight is within valid range
    const validWeight = Math.max(100, Math.min(900, roundedWeight))

    setFontWeight(validWeight)

    // Load this font weight if not already loaded
    if (!loadedFontWeights[validWeight]) {
      loadFontWeight(validWeight)
    }

  }


  // Toggle selection of a glyph for regeneration
  const toggleGlyphSelection = (glyph: GlyphData) => {
    const updatedGlyphs = [...detectedGlyphs]
    const index = updatedGlyphs.findIndex((g) => g.unicode === glyph.unicode)

    if (index >= 0) {
      updatedGlyphs[index] = {
        ...updatedGlyphs[index],
        selected: !updatedGlyphs[index].selected,
      }

      setDetectedGlyphs(updatedGlyphs)
    }
  }

  const toggleGlyphFlag = (glyph: GlyphData) => {
    // Only allow toggling for available glyphs (can't unflag missing glyphs)
    if (!glyph.isAvailable) return

    // Toggle the flagged status
    const updatedGlyphs = [...detectedGlyphs]
    const index = updatedGlyphs.findIndex((g) => g.unicode === glyph.unicode)

    if (index >= 0) {
      updatedGlyphs[index] = {
        ...updatedGlyphs[index],
        flagged: !updatedGlyphs[index].flagged,
        selected: !updatedGlyphs[index].flagged, // Select when flagged
      }

      setDetectedGlyphs(updatedGlyphs)
    }
  }

  // Update the getFontFamily function to use the loaded font for the current weight
  const getFontFamily = () => {
    // Use the specific font family for the current weight if loaded
    if (loadedFontWeights[fontWeight]) {
      return `'GeneratedFont-${fontWeight}'`
    }

    // Otherwise, find the closest loaded weight
    const loadedWeights = Object.keys(loadedFontWeights)
      .filter((weight) => loadedFontWeights[Number(weight)])
      .map(Number)
      .sort((a, b) => Math.abs(a - fontWeight) - Math.abs(b - fontWeight))

    if (loadedWeights.length > 0) {
      return `'GeneratedFont-${loadedWeights[0]}'`
    }

    // Fallback to the default font
    return "'GeneratedFont'"
  }

  // Check if there are any actual font loading errors
  const hasRealFontLoadErrors = () => {
    // Only count as an error if we tried to load a font and it failed
    if (fontUrl && !fontLoaded && fontLoadErrors["GeneratedFont"]) return true
    return false
  }

  // Add this function to handle when a purchase is completed
  const handlePurchaseComplete = () => {
    setIsPremiumPurchased(true)
  }

  // Filter glyphs for different sections
  const missingGlyphs = detectedGlyphs.filter((glyph) => !glyph.isAvailable)
  const flaggedGlyphs = detectedGlyphs.filter((glyph) => glyph.flagged && glyph.isAvailable)
  const glyphsToRegenerate = [...missingGlyphs, ...flaggedGlyphs]
  const selectedGlyphsCount = detectedGlyphs.filter((glyph) => glyph.selected).length
  const regularGlyphs = detectedGlyphs.filter((glyph) => glyph.isAvailable && !glyph.flagged)

  // Count missing glyphs in preview text
  const missingGlyphsInPreview = detectedGlyphs.filter(
    (glyph) => (!glyph.isAvailable || glyph.flagged) && previewText.includes(glyph.character),
  )

  // Count loaded font weights
  const loadedWeightsCount = Object.values(loadedFontWeights).filter(Boolean).length

  return (
    <div className="space-y-6">
      {showRegenerationSuccess && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-700 flex items-center">
            Glyphs regenerated successfully! Your font has been updated.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Font Customization</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTabKey} onValueChange={setActiveTabKey}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="preview">Preview</TabsTrigger>
              <TabsTrigger value="characters">Characters</TabsTrigger>
            </TabsList>

            <TabsContent value="preview" className="space-y-4">
              <div className="space-y-2 mt-4">
                <Label htmlFor="preview-size">Font Size: {previewSize}px</Label>
                <Slider
                  id="preview-size"
                  min={12}
                  max={72}
                  step={1}
                  value={[previewSize]}
                  onValueChange={(value) => setPreviewSize(value[0])}
                  className="mx-auto"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="font-weight">Font Weight: {fontWeight}</Label>
                  {isLoadingFonts && <Loader2 className="h-4 w-4 animate-spin ml-2" />}
                </div>
                <Slider
                  id="font-weight"
                  min={100}
                  max={900}
                  step={100}
                  value={[fontWeight]}
                  onValueChange={handleFontWeightChange}
                  className="mx-auto"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>100</span>
                  <span>300</span>
                  <span>500</span>
                  <span>700</span>
                  <span>900</span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {loadedWeightsCount > 0 ? (
                    <span>
                      {loadedWeightsCount} of {AVAILABLE_WEIGHTS.length} weights loaded.
                      {loadedFontWeights[fontWeight]
                        ? " Using actual font file for this weight."
                        : " Using closest available weight."}
                    </span>
                  ) : (
                    <span>Loading font weights...</span>
                  )}
                </div>
              </div>

              {hasRealFontLoadErrors() && (
                <Alert variant="destructive" className="mt-2">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Some font weights couldn't be loaded. Using available weights as fallback.
                  </AlertDescription>
                </Alert>
              )}

              <div className="border rounded-md p-4 min-h-[200px] mt-4 relative">
                <Textarea
                  className="outline-none w-full h-full resize-none border-none bg-transparent min-h-[200px] leading-normal"
                  style={{
                    fontFamily: getFontFamily(),
                    fontSize: `${previewSize}px`,
                    letterSpacing: `${settings.tracking}em`,
                    lineHeight: "1.3",
                  }}
                  value={previewText}
                  onChange={(e) => setPreviewText(e.target.value)}
                  placeholder="Click here to type and preview your font"
                />
              </div>

              <div className="text-sm text-muted-foreground mt-2 flex items-center">
                <Type className="h-4 w-4 mr-2" />
                Click in the preview area to edit text directly in your custom font
              </div>

              {missingGlyphsInPreview.length > 0 && (
                <Alert className="mt-4 border-amber-500 text-amber-500">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <AlertDescription className="text-amber-500">
                    Your text contains missing or flagged characters. Go to the Characters tab to regenerate them.
                  </AlertDescription>
                </Alert>
              )}
            </TabsContent>

              <TabsContent value="characters" className="space-y-4">
              {/* Improved instruction area */}
              <div className="bg-muted/30 rounded-lg p-4 mb-4 flex items-start gap-3">
                <HelpCircle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium">How to regenerate missing or problematic characters:</p>
                  <ol className="text-sm text-muted-foreground list-decimal pl-5 space-y-1">
                    <li>Click on any characters that need improvement to select them</li>
                    <li>Selected characters will be highlighted with an amber border</li>
                    <li>Click the "Regenerate Selected Characters" button when ready</li>
                  </ol>
                  {selectedGlyphsCount > 0 && (
                    <p className="text-sm font-medium text-amber-600 mt-2">
                      {selectedGlyphsCount} character{selectedGlyphsCount !== 1 ? "s" : ""} selected for regeneration
                    </p>
                  )}
                </div>
              </div>

              {/* Uppercase Letters */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">Uppercase Letters</h3>
                  <Badge variant="outline" className="font-mono">
                    A-Z
                  </Badge>
                </div>
                <div className="grid grid-cols-10 gap-2">
                  {detectedGlyphs
                    .filter((glyph) => /^[A-Z]$/.test(glyph.character))
                    .map((glyph) => (
                      <TooltipProvider key={`glyph-${glyph.unicode}`}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={`
                                border rounded-md p-2 text-center cursor-pointer relative
                                transition-all duration-150
                                ${!glyph.isAvailable ? "bg-muted/20" : ""}
                                ${glyph.selected ? "border-amber-500 border-2 shadow-sm" : "hover:border-amber-200"}
                                active:bg-muted/50
                                group
                              `}
                              onClick={() => toggleGlyphSelection(glyph)}
                            >
                              <div
                                style={{
                                  fontFamily: getFontFamily(),
                                  fontSize: "28px",
                                  opacity: glyph.isAvailable && !glyph.flagged ? 1 : 0.6,
                                }}
                              >
                                {glyph.character}
                              </div>
                              {glyph.selected && (
                                <div className="absolute bottom-1 right-1">
                                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                                </div>
                              )}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            {!glyph.isAvailable
                              ? "Missing glyph - click to select for regeneration"
                              : glyph.selected
                                ? "Selected for regeneration - click to deselect"
                                : "Click to select for regeneration"}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                </div>
              </div>

              {/* Lowercase Letters */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">Lowercase Letters</h3>
                  <Badge variant="outline" className="font-mono">
                    a-z
                  </Badge>
                </div>
                <div className="grid grid-cols-10 gap-2">
                  {detectedGlyphs
                    .filter((glyph) => /^[a-z]$/.test(glyph.character))
                    .map((glyph) => (
                      <TooltipProvider key={`glyph-${glyph.unicode}`}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={`
                                border rounded-md p-2 text-center cursor-pointer relative
                                transition-all duration-150
                                ${!glyph.isAvailable ? "bg-muted/20" : ""}
                                ${glyph.selected ? "border-amber-500 border-2 shadow-sm" : "hover:border-amber-200"}
                                active:bg-muted/50
                                group
                              `}
                              onClick={() => toggleGlyphSelection(glyph)}
                            >
                              <div
                                style={{
                                  fontFamily: getFontFamily(),
                                  fontSize: "28px",
                                  opacity: glyph.isAvailable && !glyph.flagged ? 1 : 0.6,
                                }}
                              >
                                {glyph.character}
                              </div>
                              {glyph.selected && (
                                <div className="absolute bottom-1 right-1">
                                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                                </div>
                              )}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            {!glyph.isAvailable
                              ? "Missing glyph - click to select for regeneration"
                              : glyph.selected
                                ? "Selected for regeneration - click to deselect"
                                : "Click to select for regeneration"}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                </div>
              </div>

              {/* Numbers */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">Numbers</h3>
                  <Badge variant="outline" className="font-mono">
                    0-9
                  </Badge>
                </div>
                <div className="grid grid-cols-10 gap-2">
                  {detectedGlyphs
                    .filter((glyph) => /^[0-9]$/.test(glyph.character))
                    .map((glyph) => (
                      <TooltipProvider key={`glyph-${glyph.unicode}`}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={`
                                border rounded-md p-2 text-center cursor-pointer relative
                                transition-all duration-150
                                ${!glyph.isAvailable ? "bg-muted/20" : ""}
                                ${glyph.selected ? "border-amber-500 border-2 shadow-sm" : "hover:border-amber-200"}
                                active:bg-muted/50
                                group
                              `}
                              onClick={() => toggleGlyphSelection(glyph)}
                            >
                              <div
                                style={{
                                  fontFamily: getFontFamily(),
                                  fontSize: "28px",
                                  opacity: glyph.isAvailable && !glyph.flagged ? 1 : 0.6,
                                }}
                              >
                                {glyph.character}
                              </div>
                              {glyph.selected && (
                                <div className="absolute bottom-1 right-1">
                                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                                </div>
                              )}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            {!glyph.isAvailable
                              ? "Missing glyph - click to select for regeneration"
                              : glyph.selected
                                ? "Selected for regeneration - click to deselect"
                                : "Click to select for regeneration"}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                </div>
              </div>

              {/* Special Characters */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">Special Characters</h3>
                  <Badge variant="outline" className="font-mono">
                    !@#$%...
                  </Badge>
                </div>
                <div className="grid grid-cols-10 gap-2">
                  {detectedGlyphs
                    .filter((glyph) => !/^[A-Za-z0-9]$/.test(glyph.character))
                    .map((glyph) => (
                      <TooltipProvider key={`glyph-${glyph.unicode}`}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={`
                                border rounded-md p-2 text-center cursor-pointer relative
                                transition-all duration-150
                                ${!glyph.isAvailable ? "bg-muted/20" : ""}
                                ${glyph.selected ? "border-amber-500 border-2 shadow-sm" : "hover:border-amber-200"}
                                active:bg-muted/50
                                group
                              `}
                              onClick={() => toggleGlyphSelection(glyph)}
                            >
                              <div
                                style={{
                                  fontFamily: getFontFamily(),
                                  fontSize: "28px",
                                  opacity: glyph.isAvailable ? 1 : 0.6,
                                }}
                              >
                                {glyph.character}
                              </div>
                              {glyph.selected && (
                                <div className="absolute bottom-1 right-1">
                                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                                </div>
                              )}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            {!glyph.isAvailable
                              ? "Missing glyph - click to select for regeneration"
                              : glyph.selected
                                ? "Selected for regeneration - click to deselect"
                                : "Click to select for regeneration"}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                </div>
              </div>

              {/* Regeneration Button - Direct API call implementation */}
              {selectedGlyphsCount > 0 && (
                <div className="mt-6 space-y-4">
                  {isDirectRegenerating && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span>Regenerating letters...</span>
                        <span>{regenerationProgress}%</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-amber-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${regenerationProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  <Button
                    onClick={handleDirectRegeneration}
                    className="w-full"
                    size="lg"
                    disabled={isDirectRegenerating || selectedGlyphsCount === 0}
                  >
                    {isDirectRegenerating ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="mr-2 h-5 w-5" />
                        Regenerate Selected Characters ({selectedGlyphsCount})
                      </>
                    )}
                  </Button>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-medium mb-2">Download Font</h3>
        <div className="grid grid-cols-3 gap-2">
          <Button variant="outline" onClick={() => onDownload(`${fontWeight}-ttf`)}>
            <Download className="mr-2 h-4 w-4" />
            TTF ({fontWeight})
          </Button>
          <Button variant="outline" onClick={() => onDownload(`${fontWeight}-otf`)}>
            <Download className="mr-2 h-4 w-4" />
            OTF ({fontWeight})
          </Button>
          <Button variant="outline" onClick={() => onDownload(`${fontWeight}-woff2`)}>
            <Download className="mr-2 h-4 w-4" />
            WOFF2 ({fontWeight})
          </Button>
        </div>
        <p className="text-sm text-muted-foreground mt-1 mb-2">
          The current font weight is {fontWeight}. Adjust the slider above to download different weights.
        </p>
      </div>

      {/* Premium Font Package */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Premium Options</h2>
        <PremiumFontPackage
          jobId={jobId}
          onPurchaseComplete={handlePurchaseComplete}
          isPurchased={isPremiumPurchased}
        />
      </div>
    </div>
  )
}
