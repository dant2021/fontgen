import { generateFontPrompt, createChatGptLink } from "./prompt-utils"

const API_BASE_URL = process.env.NEXT_PUBLIC_FONT_API_URL || "https://font-gen-production.up.railway.app"

/**
 * Generate a font link via the API
 */
export async function generateFontLink(description: string): Promise<{
  prompt: string
  chatGptLink: string
}> {
  try {
    // Generate the link client-side
    const prompt = generateFontPrompt(description)
    const chatGptLink = createChatGptLink(prompt)

    return { prompt, chatGptLink }
  } catch (error) {
    console.error("Error generating font link:", error)
    throw error
  }
}

/**
 * Get a regeneration prompt for specific glyphs
 */
export function getRegenerationPrompt(description: string, glyphsToRegenerate: string[]): string {
  try {
    // Generate the prompt client-side
    const glyphsDisplay = glyphsToRegenerate.join(", ")
    const basePrompt = `Create this image. A clean 2D digital graphic displaying ONLY the following characters: ${glyphsDisplay}, all in a consistent custom-designed typeface.`
    const customPart = description
    const ending =
      "Each character should be evenly spaced and clearly visible, designed with matching weight and proportion to work with an existing font set. Ensure high resolution and that no characters are cut off or distorted."

    return `${basePrompt} ${customPart} ${ending}`
  } catch (error) {
    console.error("Error getting regeneration prompt:", error)
    throw new Error("Failed to generate prompt")
  }
}

/**
 * Regenerate specific glyphs with a new image
 */
export async function regenerateGlyphs(
  jobId: string,
  image: File,
  glyphsToRegenerate: string[],
): Promise<{ success: boolean }> {
  try {
    const formData = new FormData()
    formData.append("file", image)

    // Convert array to comma-separated string for the API
    const charsString = glyphsToRegenerate.join(",")
    formData.append("chars_to_regenerate", charsString)

    console.log(`Regenerating glyphs for job ${jobId}: ${charsString}`)

    const response = await fetch(`${API_BASE_URL}/regenerate-glyphs/${jobId}`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage = errorData.message || `API error: ${response.status}`
      console.error(`Glyph regeneration failed: ${errorMessage}`)
      throw new Error(errorMessage)
    }

    const data = await response.json()
    console.log(`Glyph regeneration response:`, data)
    return { success: true }
  } catch (error) {
    console.error("Error regenerating glyphs:", error)
    throw error
  }
}
