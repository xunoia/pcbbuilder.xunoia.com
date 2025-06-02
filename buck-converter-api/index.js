// server.js

// ─── 1) Dependencies ───────────────────────────────────────────────────────────
const express    = require('express');
const cors       = require('cors');
const axios      = require('axios');
const fs         = require('fs');
const path       = require('path');
const netlistsvg = require('netlistsvg');

// ─── IMPORTANT: Correct ELK import for Node ────────────────────────────────────
const ELK = require('elkjs/lib/elk.bundled.js');

// ─── 2) Configuration / Constants ───────────────────────────────────────────────

// Read the Gemini key from an environment variable (recommended)
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'AIzaSyAFslBuQg-mcLatzHPfMrYGDIDM1z6Q52Q';

if (!GEMINI_API_KEY || GEMINI_API_KEY === '<YOUR_HARDCODED_API_KEY_GOES_HERE>') {
  console.error(
    'ERROR: You must set a valid Gemini API key. Either:\n' +
    '  • Export GEMINI_API_KEY as an environment variable, or\n' +
    '  • Replace <YOUR_HARDCODED_API_KEY_GOES_HERE> with your real key.'
  );
  process.exit(1);
}

// Gemini's generateContent endpoint:
const GEMINI_URL =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

// Load netlistsvg's default "digital" skin from node_modules:
// Try multiple possible paths for the skin file
const POSSIBLE_SKIN_PATHS = [
  path.join(__dirname, 'node_modules', 'netlistsvg', 'lib', 'default.svg'),
  path.join(__dirname, 'node_modules', 'netlistsvg', 'built', 'default.svg'),
  path.join(__dirname, 'node_modules', 'netlistsvg', 'lib', 'analog.svg'),
  path.join(__dirname, 'node_modules', 'netlistsvg', 'built', 'analog.svg')
];

let DIGITAL_SKIN_SVG;
let skinPath;

for (const tryPath of POSSIBLE_SKIN_PATHS) {
  try {
    DIGITAL_SKIN_SVG = fs.readFileSync(tryPath, 'utf8');
    skinPath = tryPath;
    console.log(`✅ Successfully loaded skin from: ${tryPath}`);
    break;
  } catch (err) {
    console.log(`❌ Could not load skin from: ${tryPath}`);
  }
}

if (!DIGITAL_SKIN_SVG) {
  console.error('Could not find any valid skin file. Available files in netlistsvg:');
  try {
    const netlistDir = path.join(__dirname, 'node_modules', 'netlistsvg');
    const findFiles = (dir, files = []) => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          findFiles(fullPath, files);
        } else if (entry.name.endsWith('.svg')) {
          files.push(fullPath);
        }
      }
      return files;
    };
    const svgFiles = findFiles(netlistDir);
    console.log('Found SVG files:', svgFiles);
    
    // Use the first available SVG as fallback
    if (svgFiles.length > 0) {
      DIGITAL_SKIN_SVG = fs.readFileSync(svgFiles[0], 'utf8');
      skinPath = svgFiles[0];
      console.log(`Using fallback skin: ${svgFiles[0]}`);
    }
  } catch (searchErr) {
    console.error('Error searching for skin files:', searchErr);
  }
}

if (!DIGITAL_SKIN_SVG) {
  console.error('No valid skin file found. netlistsvg may not be properly installed.');
  process.exit(1);
}

// ─── 3) Helper: Extract the First JSON Object from a String ────────────────────

function extractFirstJsonObject(text) {
  const firstBraceIdx = text.indexOf('{');
  if (firstBraceIdx < 0) {
    throw new Error('No "{" found in text.');
  }

  let depth = 0;
  for (let i = firstBraceIdx; i < text.length; i++) {
    if (text[i] === '{') {
      depth++;
    } else if (text[i] === '}') {
      depth--;
      if (depth === 0) {
        return text.slice(firstBraceIdx, i + 1);
      }
    }
  }

  throw new Error('Could not find matching closing brace for JSON.');
}

// ─── 4) Set Up Express App ─────────────────────────────────────────────────────
const app = express();

// Enable CORS (adjust origin in production as needed)
app.use(cors());

// Accept JSON bodies up to 5 MB
app.use(express.json({ limit: '5mb' }));

// ─── 5) GET /debug-netlistsvg ─────────────────────────────────────────────────
// Debug endpoint to check netlistsvg setup
app.get('/debug-netlistsvg', (req, res) => {
  const debugInfo = {
    skinPath: skinPath,
    skinLoaded: !!DIGITAL_SKIN_SVG,
    skinPreview: DIGITAL_SKIN_SVG ? DIGITAL_SKIN_SVG.substring(0, 200) + '...' : 'Not loaded',
    netlistsvgVersion: require('netlistsvg/package.json').version,
    elkVersion: require('elkjs/package.json').version
  };
  
  res.json(debugInfo);
});

// ─── 6) GET /test-simple ───────────────────────────────────────────────────────
// Test with a very simple circuit that should definitely work
app.get('/test-simple', async (req, res) => {
  try {
    // Simple test circuit with basic digital components
    const simpleTest = {
      "modules": {
        "simple_test": {
          "ports": {
            "A": {"direction": "input", "bits": [2]},
            "B": {"direction": "input", "bits": [3]},
            "Y": {"direction": "output", "bits": [4]}
          },
          "cells": {
            "gate1": {
              "type": "$and",
              "port_directions": {
                "A": "input",
                "B": "input", 
                "Y": "output"
              },
              "connections": {
                "A": [2],
                "B": [3],
                "Y": [4]
              }
            }
          }
        }
      }
    };

    console.log('\n=== Testing simple circuit ===');
    console.log('JSON:', JSON.stringify(simpleTest, null, 2));

    const svgString = await netlistsvg.render(DIGITAL_SKIN_SVG, simpleTest, {
      elkInstance: new ELK()
    });

    console.log('SVG preview:', svgString.substring(0, 300) + '...');
    
    res.setHeader('Content-Type', 'image/svg+xml');
    return res.send(svgString);

  } catch (err) {
    console.error('Error in simple test:', err);
    return res.status(500).json({ 
      error: 'Failed to generate simple test: ' + err.message,
      stack: err.stack 
    });
  }
});

// ─── 7) GET /test-circuit ──────────────────────────────────────────────────────
// Test endpoint with analog components
app.get('/test-circuit', async (req, res) => {
  try {
    // Use standard netlistsvg component types
    const testBuckConverter = {
      "modules": {
        "buck_converter": {
          "ports": {
            "VIN": {"direction": "input", "bits": [2]},
            "VOUT": {"direction": "output", "bits": [3]},  
            "GND": {"direction": "input", "bits": [1]}
          },
          "cells": {
            "R1": {
              "type": "r_v",
              "connections": {
                "A": [3],
                "B": [4]
              },
              "attributes": {
                "value": "10k"
              }
            },
            "R2": {
              "type": "r_v", 
              "connections": {
                "A": [4],
                "B": [1]
              },
              "attributes": {
                "value": "3.3k"
              }
            },
            "C1": {
              "type": "c_v",
              "connections": {
                "A": [3],
                "B": [1]
              },
              "attributes": {
                "value": "220uF"
              }
            },
            "L1": {
              "type": "l_v",
              "connections": {
                "A": [5],
                "B": [3]
              },
              "attributes": {
                "value": "22uH"
              }
            },
            "VIN_SOURCE": {
              "type": "v_v",
              "connections": {
                "A": [2],
                "B": [1]
              },
              "attributes": {
                "value": "12V"
              }
            }
          }
        }
      }
    };

    console.log('\n=== Testing buck converter circuit ===');
    console.log('JSON:', JSON.stringify(testBuckConverter, null, 2));

    const svgString = await netlistsvg.render(DIGITAL_SKIN_SVG, testBuckConverter, {
      elkInstance: new ELK()
    });

    console.log('SVG generated successfully, length:', svgString.length);
    console.log('SVG preview:', svgString.substring(0, 300) + '...');

    res.setHeader('Content-Type', 'image/svg+xml');
    return res.send(svgString);

  } catch (err) {
    console.error('Error in test circuit:', err);
    return res.status(500).json({ 
      error: 'Failed to generate test circuit: ' + err.message,
      stack: err.stack
    });
  }
});

// ─── 8) POST /generate-svg ──────────────────────────────────────────────────────
// Body: { "prompt": "Design a 5V buck converter from 12V input at 2A" }
app.post('/generate-svg', async (req, res) => {
  try {
    const { prompt } = req.body;
    if (!prompt || typeof prompt !== 'string') {
      return res.status(400).json({ error: '`prompt` field is required and must be a string.' });
    }

    // 5.1) Build the Gemini request payload with better prompt
    const geminiRequest = {
      contents: [
        {
          parts: [
            {
              text: `You are an electronics engineer assistant. A user says:
"${prompt}"

Generate a Yosys JSON netlist for a buck converter circuit. The netlist must follow this exact structure:

{
  "modules": {
    "buck_converter": {
      "ports": {
        "VIN": {"direction": "input", "bits": [2]},
        "VOUT": {"direction": "output", "bits": [3]},
        "GND": {"direction": "input", "bits": [1]},
        "EN": {"direction": "input", "bits": [4]}
      },
      "cells": {
        // Include these component types with proper connections:
        // - "l" (inductor) with value attribute
        // - "c" (capacitor) with value attribute  
        // - "r" (resistor) with value attribute
        // - "d" (diode) 
        // - "nmos" (MOSFET) with G/D/S connections
        // - Control circuitry as needed
      }
    }
  }
}

Requirements:
1. Use realistic component values for 12V→5V at 2A
2. Each connection uses unique bit numbers [1], [2], [3], etc.
3. All cells must have proper "connections" objects
4. Return ONLY the JSON - no explanations or markdown`
            }
          ]
        }
      ]
    };

    // 5.2) Call Gemini's generateContent API
    let geminiResponse;
    try {
      geminiResponse = await axios.post(
        `${GEMINI_URL}?key=${GEMINI_API_KEY}`,
        geminiRequest,
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
    } catch (apiErr) {
      console.error('❌ Failed to reach Gemini API:', apiErr.response?.data || apiErr.message);
      return res.status(502).json({
        error: 'Error calling Gemini API. See server logs for details.'
      });
    }

    // 5.3) Extract the text from Gemini's response
    const candidates = geminiResponse.data?.candidates;
    if (!Array.isArray(candidates) || candidates.length === 0) {
      return res.status(502).json({ error: 'Gemini returned no candidates.' });
    }

    const firstCandidate = candidates[0];
    let rawText;

    // Handle either the old `output.parts` shape or the new `content.parts` shape:
    if (firstCandidate.output?.parts?.[0]?.text) {
      rawText = firstCandidate.output.parts[0].text.trim();
    } else if (firstCandidate.content?.parts?.[0]?.text) {
      rawText = firstCandidate.content.parts[0].text.trim();
    } else {
      console.error('No .output.parts or .content.parts in first candidate:', firstCandidate);
      return res.status(502).json({
        error: 'Gemini returned an unexpected response format.'
      });
    }

    // (Optional) Log raw LLM output for debugging:
    console.log('--- Gemini raw output start ---');
    console.log(rawText);
    console.log('--- Gemini raw output end   ---');

    // 5.4) Extract the first JSON object block (in case of backticks or stray text)
    let jsonText;
    try {
      jsonText = extractFirstJsonObject(rawText);
    } catch (extractErr) {
      console.error('Error extracting JSON from Gemini output:', extractErr.message);
      return res.status(500).json({
        error: 'Gemini output was not valid JSON. Check server logs for raw output.'
      });
    }

    // 5.5) Parse the JSON text
    let yosysJson;
    try {
      yosysJson = JSON.parse(jsonText);
    } catch (parseErr) {
      console.error('Failed to parse JSON:', parseErr);
      console.error('JSON string that failed:', jsonText);
      return res.status(500).json({
        error: 'Failed to parse JSON from LLM. See server logs for details.'
      });
    }

    // 5.6) Basic sanity-check: must have at least one module
    if (
      !yosysJson.modules ||
      typeof yosysJson.modules !== 'object' ||
      Object.keys(yosysJson.modules).length === 0
    ) {
      console.error('Parsed JSON does not contain a valid "modules" object:', yosysJson);
      return res.status(500).json({
        error: '"modules" field missing or invalid in netlist JSON.'
      });
    }

    // 5.7) Generate the SVG using netlistsvg
    let svgString;
    try {
      // Pass a fresh ELK() instance so netlistsvg can compute layout
      svgString = await netlistsvg.render(DIGITAL_SKIN_SVG, yosysJson, {
        elkInstance: new ELK()
      });
    } catch (svgErr) {
      console.error('Error generating SVG with netlistsvg:', svgErr);
      return res.status(500).json({
        error: 'Failed to generate SVG schematic. See server logs for details.'
      });
    }
console.log('svgString',svgString)
    // 5.8) Return the SVG to the client
    res.setHeader('Content-Type', 'image/svg+xml');
    return res.send(svgString);
  } catch (err) {
    console.error('Unexpected error in /generate-svg route:', err);
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

// ─── 9) Start the Server ────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server is listening on http://localhost:${PORT}`);
  console.log(`🔧 Debug netlistsvg: http://localhost:${PORT}/debug-netlistsvg`);
  console.log(`🔧 Test simple circuit: http://localhost:${PORT}/test-simple`);
  console.log(`🔧 Test buck circuit: http://localhost:${PORT}/test-circuit`);
});