/**
 * Generate a prompt for font image generation based on a single description
 */
export function generateFontPrompt(description: string): string {
  const basePrompt =
    "Create this image, be careful not to miss characters. Ensure no letters are cut off. A clean 2D digital graphic displaying a full uppercase and lowercase English alphabet (A-Z, a-z), numerals (0-9), and common punctuation (! ? . , @ # $ % &), all in a consistent custom-designed typeface."

  // Add the user's description to the prompt
  const customPart = description

  // Add standard ending for font display requirements
  const ending =
    "The letters are laid out in rows. Each character is evenly spaced and designed with matching weight and proportion, in high resolution suitable for creating a font set."

  // Combine all parts
  return `${basePrompt} ${customPart} ${ending}`
}

/**
 * Create a ChatGPT link with the given prompt
 */
export function createChatGptLink(prompt: string): string {
  const encodedPrompt = encodeURIComponent(prompt)
  return `https://chat.openai.com/?model=gpt-4&q=${encodedPrompt}`
}
