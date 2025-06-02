# AI-Powered KiCad Schematic Generator (Backend)

This repository contains a Flask backend that:
1. Accepts a plain-English circuit description (e.g. “Design a 5V buck converter from 12V @ 2A”).
2. Uses Gemini v2 to parse the prompt into a structured JSON spec.
3. Matches that spec to a JSON schematic template (e.g. `templates/buck_converter.json`).
4. Uses SKiDL + KiCad 7 to generate a full KiCad schematic file (`.kicad_sch`).
5. Serves the generated `.kicad_sch` via a `/download/<filename>` endpoint.

## Directory Structure

# pcbbuilder.xunoia.com
