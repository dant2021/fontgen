import replicate
from dotenv import load_dotenv
import os

load_dotenv()


input = {
    "prompt": """
A high-resolution 8K flat design digital type specimen sheet on a pure white background (#FFFFFF). Display a full custom alphabet and character set in a futuristic, ultra-aggressive sans-serif typeface named "Momentum". All glyphs are solid black (#000000) with extremely sharp, clean vector-style edges, zero anti-aliasing. Each character is clearly spaced in neat horizontal rows. The design features strong forward-leaning oblique slant, sharply sheared terminals, and deep geometric ink traps at stroke junctions. Key glyph features: single-story 'a' with racetrack shape, asymmetrical forward-extending 't' crossbar, 'M' and 'W' vertices do not reach baseline or cap height. 
Include this exact character set: 
\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890!?.,@#$%&\"
Style: clean vector, minimalist type specimen, no textures, no lighting, no perspective, no blur, no missing characters, no decorative elements. Perfectly flat, 2D graphic layout. Render every glyph with perfect clarity and edge fidelity, suitable for vector tracing.

   """
}

output = replicate.run(
    "bytedance/seedream-3",
    input=input
)
with open("output.jpg", "wb") as file:
    file.write(output.read())
#=> output.jpg written to disk