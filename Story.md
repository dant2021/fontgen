# The Story: Building AI Font Generator

## The Spark

This project started in a pretty random way. I was sitting next to my friend Dillon in San Francisco. He was making slides for his startup, and instead of picking a font, he'd go on Flux, generate the text he wanted, and paste those images into his slides. The problem? Every image was a little different—colors, shapes, even the alignment. It looked cool, but not quite right. That inconsistency bugged me. I thought: "Why can't we just generate a whole font, consistently, from a single style or sample?"

That was the seed. I wanted to build a tool that could take a description or an image of a font and spit out a real, usable typeface. Something that would make designers' and founders' lives easier, and maybe even be fun for casual users.

## The First Steps (and Setbacks)

I started with the idea of training my own model. I'm comfortable with Python, so I stuck to my usual stack. But right out of the gate, I hit a wall: my remote GPU workstation was down for days (thanks to a bloated CUDNN folder). Productivity tanked. In the meantime, I built my personal site [latembed.com](https://latembed.com/) using V0—honestly, V0 is a lifesaver for people like me who don't love frontend work.

Once I got access to compute again, I dove into font generation. I started with a Variational Autoencoder (VAE) to learn compressed representations of font glyphs. The pipeline: render each character as a 64×64 image, encode it into a 256D latent space, and decode it back. I added glyph-specific embeddings to help the model tell characters apart.

## The Hard Parts

The biggest technical headache? Blurry glyphs. Compressing a font down to a tiny latent space means you lose detail—edges get fuzzy, and the font just doesn't look professional. I tried adding residual connections, but the model just "cheated" and skipped the latent space, defeating the point. Removing those connections forced the model to actually learn, but mixing styles was still rough.

I also learned a ton about typography—tracking, spacing, alignment, descenders. I had zero experience with fonts before this, and it turns out, design is all about the details. Getting every letter to look consistent is way harder than it sounds. The regenerate function (making a new glyph match the style of the rest) was especially tough. I spent a lot of time grinding through edge cases and tiny fixes. Honestly, that's where I started to lose steam. I'm an 80/20 person—the last 20% of polish is a slog, but it's what makes a tool truly great.

## Experimenting and Pivoting

I didn't stop at VAEs. I tried a bunch of approaches:

- **Autoencoders with Flux:** Better edge preservation, and I discovered that the latent space dimensions acted like edge detectors and contrast filters.
- **Latent Diffusion:** Promising, but slow and data-hungry.
- **Autoregressive Transformers:** Compressed the latent space, but lost too much detail.
- **Vector Arithmetic:** Surprisingly, you can do algebra in the embedding space—`A + B - O` gives you legible new shapes.
- **GPT-4o Image Prompting:** Eventually, I pivoted to using GPT-4o for image prompts. It's faster, more controllable, and already has refinement built in.

## The Pipeline

Here's how it works now:

1. **Image Cleanup:** Upload a handwriting sample, threshold to black and white, clean up the bitmap.
2. **Path Creation:** Potrace converts pixels to SVG paths—smooth, scalable curves.
3. **Character Assembly:** Group paths, merge components, identify glyphs (dots over "i"s are a pain).
4. **Baseline Detection:** Find where letters sit on the line, handle descenders with statistical tricks.
5. **AI Recognition:** Arrange glyphs in a grid, use a vision model to label them.
6. **Font Engineering:** Import SVGs into FontForge, scale, align, and export TTF/OTF files.

## What Works (and What Doesn't)

- ✓ You can upload handwriting and get a working font.
- ✓ Supports basic Latin characters and numbers.
- ✓ Exports standard font files.
- ✓ The interface is simple and functional.

But… it's not perfect. Punctuation and some characters are missing. Spacing and kerning are tricky—sometimes the text feels "alive" in a weird way. Dotting "i"s and handling descenders is still a work in progress. It's not quite at designer-level quality or customizability yet.

## Lessons Learned

- Consistency is everything. Getting all letters to match in style is the hardest part.
- Customizability is key—users want to tweak individual letters.
- Speed matters. Iteration should be fast and fun.
- Qwen 2.5 VL is an amazing model.
- Generating a font from scratch is way harder than it looks.
- Design is all about the details.

## What's Next?

I'm happy with the progress, but I'm not planning to take this to a polished, designer-ready product myself. The last 20% is a lot of work, and I'm more interested in building tools and small functions. I might open-source the code if there's interest. In the meantime, you can [try the tool here](https://ai-font-generator.vercel.app/), and I'd love feedback or pull requests.

If you want to beta test, reach out! I hope you have as much fun using it as I did building it.
