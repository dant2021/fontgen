import os
from openai import OpenAI

def enhance_prompt_with_ai(user_input: str, api_key: str = None) -> str:
    """Use AI to enhance the user's font style description with detailed typographic characteristics.
    
    Args:
        user_input (str): The user's original style description
        api_key (str, optional): OpenRouter API key. If not provided, will try to get from environment.
        
    Returns:
        str: An enhanced prompt with detailed typographic characteristics
    """
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key:
        print("Warning: No OpenRouter API key found. Using original prompt.")
        return user_input

    system_prompt = """You are a typography expert. Enhance the given font style description by adding specific 
    typographic details about stroke weight, serifs, x-height, letter spacing, and overall design characteristics. 
    Keep the original style intent but make it more precise and professional. keep it short and concise and respond immediately. give only one option"""
    
    try:
        # Initialize OpenAI client with OpenRouter
        client_kwargs = {
            "api_key": api_key,
            "base_url": "https://openrouter.ai/api/v1"
        }
        client = OpenAI(**client_kwargs)
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://font-generator.com",
                "X-Title": "Font Generator",
            },
            model="qwen/qwen3-235b-a22b:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Enhance this font style description: {user_input}"}
            ],
            temperature=0.7,
            max_tokens=600
        )
        
        if completion and completion.choices and len(completion.choices) > 0:
            enhanced_style = completion.choices[0].message.content.strip()
        else:
            print("Unexpected response format from API")
            print(completion)
            enhanced_style = user_input
            
    except Exception as e:
        print(f"Error enhancing prompt: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print("Response content:", e.response.text)
            except:
                pass
        enhanced_style = user_input  # Fallback to original input
    
    return enhanced_style

def generate_prompt(user_input: str, api_key: str = None) -> str:
    """Generate a detailed prompt for font image generation.
    
    Args:
        user_input (str): The base style description from the user
        api_key (str, optional): OpenRouter API key. If not provided, will try to get from environment.
        
    Returns:
        str: A detailed prompt for font generation
    """
    # Enhance the user's input using AI
    #enhanced_style = enhance_prompt_with_ai(user_input, api_key)
    enhanced_style = user_input
    print(f"Enhanced style: {enhanced_style}")  # Debug print
    
    # Base prompt components
    base_prompt = "A clean 2D digital graphic displaying a full uppercase and lowercase English alphabet (A-Z, a-z), numerals (0-9), and common punctuation (! ? . , @ # $ % &), all in a consistent custom-designed typeface."
    
    # Style description
    style_part = f"The font style is {enhanced_style}"
    
    # Layout and technical specifications
    ending = "The letters are laid out in rows. Ensure all letters are present and visible. Each character is evenly spaced and designed with matching weight and proportion, in high resolution suitable for creating a font set."
    
    return f"{base_prompt} {style_part} {ending}", enhanced_style
