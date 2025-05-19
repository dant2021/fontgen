// Base API URL
const API_BASE_URL = process.env.NEXT_PUBLIC_FONT_API_URL || "https://font-gen-production.up.railway.app"

/**
 * Uploads an image to start the font generation process
 * @param image The image file to process
 * @returns Promise with the job ID
 */
export async function uploadFontImage(image: File): Promise<{ jobId: string }> {
  // Create a FormData object to send the image
  const formData = new FormData()
  formData.append("file", image) // Note: Backend expects "file", not "image"

  // Construct the full API URL
  const apiUrl = `${API_BASE_URL}/generate-font`

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `API error: ${response.status}`)
    }

    const data = await response.json()
    return { jobId: data.job_id }
  } catch (error) {
    console.error("Error uploading font image:", error)
    throw error
  }
}

/**
 * Generate a font directly from a prompt
 * @param prompt The text prompt describing the font
 * @returns Promise with the job ID
 */
export async function generateFontFromPrompt(prompt: string): Promise<{ jobId: string }> {
  // Create a FormData object to send the prompt
  const formData = new FormData()
  formData.append("prompt", prompt)

  // Construct the full API URL
  const apiUrl = `${API_BASE_URL}/generate-from-prompt`

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `API error: ${response.status}`)
    }

    const data = await response.json()
    return { jobId: data.job_id }
  } catch (error) {
    console.error("Error generating font from prompt:", error)
    throw error
  }
}

// Update the checkFontStatus function to include the new info-message field
export async function checkFontStatus(jobId: string): Promise<{
  status: string
  infoMessage?: string
  availableFormats?: string[]
  missingGlyphs?: string[]
}> {
  if (!jobId) {
    return { status: "error", missingGlyphs: [] }
  }

  // Add timestamp to prevent caching
  const timestamp = Date.now()
  const apiUrl = `${API_BASE_URL}/font-status/${jobId}?t=${timestamp}`

  try {
    const response = await fetch(apiUrl, {
      // Add cache control headers
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `API error: ${response.status}`)
    }

    const data = await response.json()
    console.log("Font status response:", data)

    // Check if missing glyphs format is available
    if (data.available_formats && data.available_formats.includes("missing-glyphs")) {
      // Fetch the missing glyphs file with cache busting
      const missingGlyphsUrl = `${API_BASE_URL}/download-font/${jobId}/missing-glyphs?t=${timestamp}`
      try {
        const missingGlyphsResponse = await fetch(missingGlyphsUrl, {
          // Add cache control headers
          headers: {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Pragma: "no-cache",
            Expires: "0",
          },
        })

        if (missingGlyphsResponse.ok) {
          const missingGlyphsData = await missingGlyphsResponse.json()
          console.log("Missing glyphs data:", missingGlyphsData)
          return {
            status: data.status,
            infoMessage: data["info-message"],
            availableFormats: data.available_formats,
            missingGlyphs: missingGlyphsData,
          }
        }
      } catch (error) {
        console.error("Error fetching missing glyphs:", error)
        // Continue with the process even if missing glyphs fetch fails
      }
    }

    return {
      status: data.status,
      infoMessage: data["info-message"],
      availableFormats: data.available_formats,
      missingGlyphs: [],
    }
  } catch (error) {
    console.error("Error checking font status:", error)
    throw error
  }
}

// The rest of the file remains the same
export function getFontDownloadUrl(jobId: string, format: string): string {
  // Make sure the format is one of the allowed values
  // Format should now be like "400-ttf", "700-otf", "900-woff2"
  const validWeights = [100, 200, 300, 400, 500, 600, 700, 800, 900]
  const validFormats = ["ttf", "otf", "woff2"]

  let weight = 500
  let fileFormat = "ttf"

  if (format === "missing-glyphs") {
    // Special case for missing glyphs
    fileFormat = format
  } else if (format.includes("-")) {
    // Parse format like "400-ttf"
    const [weightStr, formatStr] = format.split("-")
    const parsedWeight = Number.parseInt(weightStr)

    if (validWeights.includes(parsedWeight)) {
      weight = parsedWeight
    }

    if (validFormats.includes(formatStr)) {
      fileFormat = formatStr
    }
  } else if (validFormats.includes(format)) {
    // Legacy format support (just "ttf" or "otf")
    fileFormat = format
  }

  // Construct the format string
  const formatString = fileFormat === "missing-glyphs" ? "missing-glyphs" : `${weight}-${fileFormat}`

  // Add a cache-busting parameter to ensure we get the latest version
  const cacheBuster = new Date().getTime()

  // Construct and return the URL
  const url = `${API_BASE_URL}/download-font/${jobId}/${formatString}?t=${cacheBuster}`;
  console.log("Download URL:", url);
  return url;
}

/**
 * Regenerate missing glyphs using the direct API endpoint
 * @param jobId The ID of the font job
 * @param charsToRegenerate Comma-separated list of characters to regenerate
 * @returns Promise with success status
 */
export async function regenerateMissingGlyphs(
  jobId: string,
  charsToRegenerate: string,
): Promise<{ jobId: string; message: string }> {
  if (!jobId || !charsToRegenerate) {
    throw new Error("Missing required parameters for glyph regeneration")
  }

  const apiUrl = `${API_BASE_URL}/regenerate-missing-glyphs/${jobId}`

  try {
    console.log(`Regenerating glyphs for job ${jobId}: ${charsToRegenerate}`)

    const formData = new FormData()
    formData.append("chars_to_regenerate", charsToRegenerate)

    const response = await fetch(apiUrl, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage = errorData.message || errorData.error || `API error: ${response.status}`
      console.error(`Glyph regeneration failed: ${errorMessage}`)
      throw new Error(errorMessage)
    }

    const data = await response.json()
    console.log("Regeneration response:", data)
    return data
  } catch (error) {
    console.error("Error regenerating glyphs:", error)
    throw error
  }
}

export async function updateFontSettings(jobId: string, settings: any): Promise<{ fontUrl: string }> {
  const apiUrl = `${API_BASE_URL}/update-settings/${jobId}`

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(settings),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error("Error updating font settings:", error)
    throw error
  }
}

/**
 * Download premium font package
 * @param jobId The ID of the font job
 * @returns Promise with download URL
 */
export async function getPremiumPackageUrl(jobId: string): Promise<string> {
  if (!jobId) {
    throw new Error("Missing job ID for premium package download")
  }

  // In a real implementation, this would call an API endpoint to get a secure download URL
  // For now, we'll construct a URL to a hypothetical endpoint
  return `${API_BASE_URL}/download-premium-package/${jobId}?t=${Date.now()}`
}

/**
 * Regenerate glyphs by uploading a new image
 * @param jobId The ID of the font job
 * @param image The image file containing the glyphs to regenerate
 * @param glyphsToRegenerate An array of glyphs to regenerate
 * @returns Promise with success status
 */
export async function regenerateGlyphs(jobId: string, image: File, glyphsToRegenerate: string[]): Promise<any> {
  if (!jobId || !image || glyphsToRegenerate.length === 0) {
    throw new Error("Missing required parameters for glyph regeneration")
  }

  const apiUrl = `${API_BASE_URL}/regenerate-glyphs/${jobId}`

  try {
    const formData = new FormData()
    formData.append("file", image)
    formData.append("glyphs", JSON.stringify(glyphsToRegenerate))

    const response = await fetch(apiUrl, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `API error: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error("Error regenerating glyphs:", error)
    throw error
  }
}

/**
 * Create a Stripe Checkout session for a premium font package
 * @param jobId The ID of the font job
 * @param returnUrl The return URL for the checkout session
 * @returns Promise with the Stripe session ID
 */
export async function createCheckoutSession(jobId: string, returnUrl: string): Promise<{ sessionId: string }> {
  const res = await fetch("/api/create-checkout-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId, returnUrl }),
  });
  if (!res.ok) throw new Error("Failed to create checkout session");
  return res.json();
}
