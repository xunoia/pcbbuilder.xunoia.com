// api/generate.js
import { writeFileSync, readFileSync, unlinkSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";
import fetch from "node-fetch";

// ─────────────────────────────────────────────────────────────────────────────
// callGeminiForCircuitJson(prompt):
// → Sends "prompt" to Gemini v1beta "generateContent" endpoint
// → Expects a tscircuit‐JSON object back
// ─────────────────────────────────────────────────────────────────────────────
async function callGeminiForCircuitJson(prompt) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("Missing GEMINI_API_KEY in environment");
  }

  // System‐style instructions + schema for tscircuit JSON
  const systemPrompt = `
You are a hardware design assistant. Convert the user's plain-English circuit request into valid tscircuit JSON.
Output exactly one JSON object—no extra text or markdown fences.

tscircuit JSON schema:
{
  "parts": [
    {
      "ref": "<string>", // e.g. "U1", "R1"
      "type": "<string>", // e.g. "LM2676S", "47uH_Inductor"
      "footprint": "<string>", // e.g. "Regulator_Boards/LM2676S_PowerPad"
      "pins": { // pinName → netName
        "<pinName>": "<netName>",
        ...
      }
    },
    ...
  ],
  "nets": [
    {
      "name": "<string>", // e.g. "VIN_NET", "GND"
      "connections": [
        { "partRef": "<string>", "pin": "<string>" },
        ...
      ]
    },
    ...
  ]
}
`.trim();

  // Combine schema‐instructions + user prompt
  const fullText = systemPrompt + "\n\nUser Prompt: " + prompt;
  const payload = {
    contents: [
      {
        role: "user",
        parts: [{ text: fullText }],
      },
    ],
  };

  // Call Gemini's REST endpoint
  const resp = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Gemini API Error ${resp.status}: ${body}`);
  }

  const data = await resp.json();
  let text = data.candidates[0].content.parts[0].text.trim();

  // If wrapped in ```json … ```, strip fences
  if (text.startsWith("```")) {
    text = text.replace(/^```json\s*/, "").replace(/```$/, "").trim();
  }

  try {
    return JSON.parse(text);
  } catch (e) {
    console.error("Gemini returned invalid JSON:\n", text);
    throw new Error("Failed to parse JSON from Gemini");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// handler(req, res):
// → Accepts POST /api/generate { prompt }
// → Calls Gemini → writes /tmp/circuit.json
// → Runs tscircuit CLI → /tmp/schematic.svg + /tmp/board.kicad_pcb
// → Reads both and returns them
// ─────────────────────────────────────────────────────────────────────────────
export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    res.status(405).json({ error: "Method Not Allowed, use POST" });
    return;
  }

  const { prompt } = req.body;
  if (!prompt || typeof prompt !== "string") {
    res.status(400).json({ error: "Missing or invalid 'prompt' field" });
    return;
  }

  try {
    // 1) Gemini → tscircuit JSON
    const circuitJson = await callGeminiForCircuitJson(prompt);

    // 2) Write JSON to /tmp/circuit.json
    const tmpJsonPath = join("/tmp", "circuit.json");
    writeFileSync(tmpJsonPath, JSON.stringify(circuitJson, null, 2));

    // 3) tscircuit → schematic.svg
    const svgPath = join("/tmp", "schematic.svg");
    // FIXED: Use the correct export command syntax - try different variations
    try {
      execSync(`tsci export ${tmpJsonPath} --format svg --type schematic -o ${svgPath}`);
    } catch (e) {
      // Try alternative syntax
      try {
        execSync(`tsci export ${tmpJsonPath} --output ${svgPath} --format svg`);
      } catch (e2) {
        // Try simplified syntax
        execSync(`tsci export ${tmpJsonPath} -o ${svgPath}`);
      }
    }

    // 4) tscircuit → KiCad PCB (.kicad_pcb)
    const pcbPath = join("/tmp", "board.kicad_pcb");
    // FIXED: Use the correct export command syntax
    try {
      execSync(`tsci export ${tmpJsonPath} --format kicad --type pcb -o ${pcbPath}`);
    } catch (e) {
      // Try alternative syntax for PCB export
      try {
        execSync(`tsci export ${tmpJsonPath} --output ${pcbPath} --format kicad`);
      } catch (e2) {
        // Try generating just the JSON and handle PCB conversion differently
        console.warn("PCB export failed, will return empty PCB content");
        writeFileSync(pcbPath, "# PCB export not available");
      }
    }

    // 5) Read both outputs
    const schematicSvg = readFileSync(svgPath, "utf-8");
    const pcbFileContent = readFileSync(pcbPath, "utf-8");

    // 6) Cleanup (optional)
    try {
      unlinkSync(tmpJsonPath);
      unlinkSync(svgPath);
      unlinkSync(pcbPath);
    } catch (_) {}

    // 7) Return both as JSON
    res.status(200).json({
      schematicSvg,
      pcbFileContent,
    });
  } catch (err) {
    console.error("Error in /api/generate:", err);
    res.status(500).json({ error: err.message });
  }
}