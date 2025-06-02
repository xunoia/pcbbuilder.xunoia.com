# LLM-Circuit-MVP

An AI-driven tool that automates the end-to-end electronics design flow—from prompt to schematic and PCB layout—using Gemini (Google’s Generative Language model) and the tscircuit CLI. This repository demonstrates how to:

1. Turn a plain-English circuit prompt (e.g. “Design a 5V buck converter from 12V input at 2A”) into a structured circuit definition.
2. Render a traditional electrical-symbol schematic as SVG.
3. Export a KiCad-compatible PCB file (.kicad\_pcb).

---

## Table of Contents

1. [Design Flow](#design-flow)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Getting Started](#getting-started)

   * [Prerequisites](#prerequisites)
   * [Installation](#installation)
   * [Configuration](#configuration)
   * [Running Locally](#running-locally)
5. [Usage](#usage)

   * [API Endpoint](#api-endpoint)
   * [Example Request/Response](#example-requestresponse)
6. [Design Flow Mapping](#design-flow-mapping)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Design Flow

This tool implements the canonical electronics design process:

1. **Design Requirements / Specification**
   Understand what the circuit must do (inputs, outputs, power, interfaces).

2. **Schematic Design**
   Create a circuit diagram (logical connections, not physical layout).

3. **Component Selection**
   Choose real-world parts (ICs, resistors, capacitors, inductors, etc.) with correct footprints.

4. **Netlist Generation**
   Generate connectivity data (nets) from the schematic for the layout stage.

5. **PCB Layout Design**
   Place parts on a board and route copper traces, driven by the netlist.

6. **Design Rule Checking (DRC)**
   Ensure the PCB layout follows manufacturing rules (clearance, widths, spacing).

7. **Electrical Rule Check (ERC)**
   Check schematic for logical issues (unconnected pins, shorted nets, power nets).

8. **Simulation & Signal Integrity (Optional)**
   Validate analog/digital behavior or EMI/EMC considerations (not covered in MVP).

9. **Generate Gerber Files**
   Export manufacturing-ready files (Gerbers, drill files, pick-and-place data).

Our MVP implements steps 1–5 (and partially step 9 by exporting a KiCad PCB file) in a single serverless API call.

---

## Features

* **Prompt→Circuit JSON (via Gemini)**
  Convert a plain-English prompt into a validated tscircuit JSON definition.

* **Schematic Rendering (SVG)**
  Generate a traditional electrical-symbol schematic (SVG output).

* **PCB Export (KiCad .kicad\_pcb)**
  Export a fully compatible KiCad PCB file ready for further layout or Gerber generation.

* **Serverless-Friendly**
  Designed to run in `/tmp` for file I/O; deployable on Vercel, Cloudflare Functions, or any Node.js serverless environment.

---

## Architecture

```
┌──────────────────┐        1. POST /generate { prompt }
│  Frontend (UI)   │ ──────────────────────────────────────────┐
└──────────────────┘                                            │
                                                                ▼
                                                       ┌──────────────────┐
                                                       │  Serverless API  │
                                                       │ (Express/Vercel) │
                                                       └──────────────────┘
                                                                │
                           2. callGeminiForCircuitJson(prompt)  │
                                                                ▼
                                                      ┌──────────────────────┐
                                                      │  Gemini API (LLM)    │
                                                      │ (v1beta generate)    │
                                                      └──────────────────────┘
                                                                │
                      3. Returns tscircuit JSON (parts + nets)   │
                                                                ▼
                                                    ┌────────────────────────┐
                                                    │  Write /tmp/circuit.json
                                                    │  ExecSync “tsci render schematic …”
                                                    │  ExecSync “tsci export pcb …”
                                                    └────────────────────────┘
                                                                │
                                             4. Generate schematic.svg   &   board.kicad_pcb
                                                                │
                                                                ▼
                                                      ┌──────────────────┐
                                                      │   Read files      │
                                                      │ (SVG + KiCad PCB) │
                                                      └──────────────────┘
                                                                │
                                                                ▼
                                                5. API responds with { schematicSvg, pcbFileContent }
                                                                │
                                                                ▼
                                                   Frontend displays SVG; user downloads PCB
```

---

## Getting Started

### Prerequisites

1. **Node.js v16+**

2. **Bun** (for installing and running tscircuit):

   ```bash
   curl -fsSL https://bun.sh/install | bash
   source ~/.zshrc    # or your shell’s RC file
   bun --version      # must print a version
   ```

3. **Install tscircuit CLI globally** (via Bun):

   ```bash
   bun add -g tscircuit
   tscircuit --help   # should show usage
   ```

4. **Obtain a Gemini API key** (Google Generative Language).

---

### Installation

1. Clone the repository:

   ```bash
   git clone  
   cd llm-circuit-mvp
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Create a file named `.env` at the project root with:

   ```
   GEMINI_API_KEY=sk-…YOUR_API_KEY…
   ```

   > **Do not commit** `.env` to version control.

---

### Configuration

* The only required environment variable is `GEMINI_API_KEY`.
* By default, the Express server runs on port 3000. You can override it by setting `PORT` in your shell:

  ```bash
  export PORT=4000
  ```

---

### Running Locally

1. Ensure `tscircuit` is in your `PATH` (via Bun).

2. Start the server:

   ```bash
   npm start
   ```

3. You should see:

   ```
   Listening on http://localhost:3000
   ```

4. Test with `curl` (or Postman):

   ```bash
   curl -X POST http://localhost:3000/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt":"Design a 5V buck converter from 12V input at 2A"}'
   ```

   * **Expected response** (JSON):

     ```json
     {
       "schematicSvg": "<svg xmlns=\"http://www.w3.org/2000/svg\" ...>…</svg>",
       "pcbFileContent": "(kicad_pcb (version 20240108) (generator \"tscircuit\") … )"
     }
     ```

   * Save the `"schematicSvg"` into `schematic.svg` to view the schematic.

   * Copy `"pcbFileContent"` into `board.kicad_pcb` and open in KiCad’s PCB Editor to inspect the board layout.

---

## Usage

### API Endpoint

#### `POST /generate`

* **Request Body** (JSON):

  ```json
  {
    "prompt": "Design a 5V buck converter from 12V input at 2A"
  }
  ```

* **Response** (200 OK):

  ```json
  {
    "schematicSvg": "<svg ...>…</svg>",
    "pcbFileContent": "(kicad_pcb (version …) … )"
  }
  ```

* You can embed `schematicSvg` in an HTML page or open as an SVG file.

* You can save `pcbFileContent` to `board.kicad_pcb` and open it with KiCad (version 7 or later).

---

## Design Flow Mapping

Below is how each step in the canonical electronics design flow is addressed by this MVP:

1. **Requirements / Specification**

   * The user’s natural-language prompt captures inputs, outputs, power, etc.

2. **Schematic Design**

   * Gemini generates a structured tscircuit JSON (parts + nets) representing the logical schematic.

3. **Component Selection**

   * The tscircuit JSON includes `ref`, `type`, and `footprint` for each part (e.g., `Regulator_Boards/LM2676S_PowerPad`).

4. **Netlist Generation**

   * The tscircuit JSON’s `nets` section lists each net name with its connected `partRef` and `pin`.

5. **PCB Layout Design**

   * The `tsci export pcb` command converts tscircuit JSON → KiCad PCB file (`.kicad_pcb`), which includes component footprints + nets.

6. **DRC**

   * While KiCad’s own DRC is not run automatically, the exported `.kicad_pcb` can be opened in KiCad to perform DRC.

7. **ERC**

   * The tool does not perform an ERC automatically. KiCad’s built-in ERC can be run on the schematic if you choose to generate one (MVP focuses on layout).

8. **Simulation & Signal Integrity**

   * Out of scope for this MVP. You can optionally export a SPICE netlist from tscircuit JSON or generate a SPICE file manually.

9. **Generate Gerber Files**

   * Not covered directly. You can open the exported `.kicad_pcb` in KiCad and use KiCad’s “Plot” to generate Gerbers.

---

## Troubleshooting

* **“unknown command” errors**

  * Verify that `tscircuit` (or `tsci`) is installed and on your `PATH`.
  * Run `tsci --help` to confirm.

* **“Missing GEMINI\_API\_KEY”**

  * Ensure `.env` exists at project root and contains `GEMINI_API_KEY=…`.
  * Run `node server.js` in the same directory as `.env`.

* **Invalid JSON from Gemini**

  * Examine console output; the raw Gemini response is logged when JSON.parse fails.
  * Adjust the `systemPrompt` text in `api/generate.js` to clarify the expected schema.

* **Permissions on `/tmp`**

  * On macOS/Linux, `/tmp` is writable. If you get a permission error, check your OS settings or change the temp path.

---

 
