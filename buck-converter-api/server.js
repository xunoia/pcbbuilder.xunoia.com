// import express from 'express';
// import dotenv from 'dotenv';
// import { convertCircuitJsonToSchematicSvg } from 'circuit-to-svg';

// dotenv.config();

// const app = express();
// app.use(express.json());

// const PORT = process.env.PORT || 4000;
// const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

// if (!GEMINI_API_KEY) {
//   console.error('ERROR: Please set the GEMINI_API_KEY environment variable.');
//   process.exit(1);
// }

// // Helper: call Gemini to generate circuit soup
// async function generateCircuitSoup(userPrompt) {
//   const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

//   const body = {
//     contents: [
//       {
//         parts: [{ text: userPrompt }],
//       },
//     ],
//   };

//   const response = await fetch(url, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify(body),
//   });

//   if (!response.ok) {
//     const text = await response.text();
//     throw new Error(`Gemini API error: ${response.status} – ${text}`);
//   }

//   const data = await response.json();
//   let contentString = '';

//   try {
//     if (data.candidates?.[0]?.content?.parts?.[0]?.text) {
//       contentString = data.candidates[0].content.parts[0].text.trim();
//     } else if (data.candidates?.[0]?.content?.text) {
//       contentString = data.candidates[0].content.text.trim();
//     } else {
//       throw new Error('Gemini returned an unexpected response format.');
//     }

//     // Sanitize content: remove ```json and ``` if present
//     contentString = contentString.replace(/^```json\s*/i, '').replace(/```$/, '').trim();

//     console.log('contentString', contentString);
//     return JSON.parse(contentString);

//   } catch (err) {
//     console.error('Failed to extract or parse JSON from Gemini response:', data);
//     throw new Error('Invalid JSON in Gemini response');
//   }
// }


// // POST /api/generate-svg
// app.post('/api/generate-svg', async (req, res) => {
//   try {
//     const { prompt } = req.body;
//     if (typeof prompt !== 'string' || prompt.trim().length === 0) {
//       return res.status(400).json({ error: 'Prompt is required.' });
//     }

//     const instruction = `Generate a valid circuit-description JSON for the following: "${prompt}". 
// Include top-level keys "components" (array of { type, ref, value, nodes }) 
// and "nets" (array of { name, connections }).`;

//     const soupJson = await generateCircuitSoup(instruction);

//     console.log('Parsed soupJson:', JSON.stringify(soupJson, null, 2));

//     if (!soupJson || !Array.isArray(soupJson.components) || !Array.isArray(soupJson.nets)) {
//       return res.status(500).json({ error: 'Invalid circuit JSON structure from Gemini.' });
//     }
// console.log('soupJson',soupJson)
//     const svg = convertCircuitJsonToSchematicSvg(soupJson);

//     return res.json({ svg });
//   } catch (err) {
//     console.error('Error in /api/generate-svg:', err);
//     return res.status(500).json({ error: err.message || 'Unknown error' });
//   }
// });


// app.listen(PORT, () => {
//   console.log(`🚀 Server running at http://localhost:${PORT}`);
// });


import express from 'express';
import dotenv from 'dotenv';
import { convertCircuitJsonToSchematicSvg } from 'circuit-to-svg';

dotenv.config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 4000;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

if (!GEMINI_API_KEY) {
  console.error('ERROR: Please set the GEMINI_API_KEY environment variable.');
  process.exit(1);
}

// Helper: call Gemini to generate circuit soup
async function generateCircuitSoup(userPrompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

  const body = {
    contents: [
      {
        parts: [{ text: userPrompt }],
      },
    ],
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Gemini API error: ${response.status} – ${text}`);
  }

  const data = await response.json();
  let contentString = '';

  try {
    if (data.candidates?.[0]?.content?.parts?.[0]?.text) {
      contentString = data.candidates[0].content.parts[0].text.trim();
    } else if (data.candidates?.[0]?.content?.text) {
      contentString = data.candidates[0].content.text.trim();
    } else {
      throw new Error('Gemini returned an unexpected response format.');
    }

    // Sanitize content: remove ```json and ``` if present
    contentString = contentString.replace(/^```json\s*/i, '').replace(/```$/, '').trim();

    console.log('contentString', contentString);
    return JSON.parse(contentString);

  } catch (err) {
    console.error('Failed to extract or parse JSON from Gemini response:', data);
    throw new Error('Invalid JSON in Gemini response');
  }
}

// Helper: Convert and fix circuit soup format for circuit-to-svg library
function fixCircuitSoupFormat(circuitArray) {
  return circuitArray.map(item => {
    if (item.type === 'schematic_component') {
      // Add missing properties required by circuit-to-svg
      const fixedItem = {
        ...item,
        // Add size information that the library expects
        size: item.size || { width: 20, height: 10 },
        // Ensure pins have proper format
        pins: item.pins?.map(pin => ({
          ...pin,
          // Ensure pin has all required properties
          pin_number: pin.pin_number || pin.number || 1,
          center: pin.center || { x: 0, y: 0 }
        })) || []
      };

      // Add component-specific size defaults
      switch (item.component_name) {
        case 'resistor':
          fixedItem.size = { width: 20, height: 8 };
          break;
        case 'capacitor':
          fixedItem.size = { width: 12, height: 20 };
          break;
        case 'vsource':
          fixedItem.size = { width: 20, height: 20 };
          break;
        case 'gnd':
          fixedItem.size = { width: 10, height: 10 };
          break;
        default:
          fixedItem.size = { width: 20, height: 10 };
      }

      return fixedItem;
    }
    return item;
  });
}

// Helper: Convert object format to array format expected by circuit-to-svg
function convertToCircuitSoupArray(circuitObj) {
  const soupArray = [];
  
  // Add components to soup array
  if (circuitObj.components && Array.isArray(circuitObj.components)) {
    circuitObj.components.forEach(component => {
      soupArray.push({
        type: 'schematic_component',
        schematic_component_id: component.ref || `comp_${soupArray.length}`,
        component_name: component.type,
        symbol_name: component.type,
        center: { x: 0, y: 0 }, // Default position, will be auto-placed
        rotation: 0,
        value: component.value || '',
        size: { width: 20, height: 10 }, // Add default size
        pins: component.pins || [],
        ...component
      });
    });
  }
  
  // Add nets/connections to soup array
  if (circuitObj.nets && Array.isArray(circuitObj.nets)) {
    circuitObj.nets.forEach(net => {
      if (net.connections && Array.isArray(net.connections)) {
        net.connections.forEach(connection => {
          soupArray.push({
            type: 'schematic_net_label',
            center: { x: 0, y: 0 },
            text: net.name || 'NET',
            anchor: 'middle_left',
            ...connection
          });
        });
      }
    });
  }
  
  return soupArray;
}

// POST /api/generate-svg
app.post('/api/generate-svg', async (req, res) => {
  try {
    const { prompt } = req.body;
    if (typeof prompt !== 'string' || prompt.trim().length === 0) {
      return res.status(400).json({ error: 'Prompt is required.' });
    }

    const instruction = `Generate a valid circuit-description JSON for the following: "${prompt}". 
Return a JSON array directly (not an object with components/nets keys). Each array item should be a circuit element with properties like:
- type: "schematic_component" for components
- schematic_component_id: unique identifier
- component_name: component type (resistor, capacitor, etc.)
- symbol_name: same as component_name
- center: {x: number, y: number} for position
- rotation: 0 for rotation (in degrees)
- value: component value as string
- size: {width: number, height: number} - component dimensions
- pins: array of pin objects with pin_number and center coordinates relative to component center

Example format:
[
  {
    "type": "schematic_component",
    "schematic_component_id": "R1",
    "component_name": "resistor",
    "symbol_name": "resistor", 
    "center": {"x": 0, "y": 0},
    "rotation": 0,
    "value": "1k",
    "size": {"width": 20, "height": 8},
    "pins": [
      {"pin_number": 1, "center": {"x": -10, "y": 0}},
      {"pin_number": 2, "center": {"x": 10, "y": 0}}
    ]
  }
]

Include proper connections between components by making sure pin positions align properly.`;

    const soupJson = await generateCircuitSoup(instruction);

    console.log('Parsed soupJson:', JSON.stringify(soupJson, null, 2));

    let circuitSoupArray;
    
    // Handle both array and object formats from Gemini
    if (Array.isArray(soupJson)) {
      circuitSoupArray = soupJson;
    } else if (soupJson && typeof soupJson === 'object') {
      // Convert object format to array format
      circuitSoupArray = convertToCircuitSoupArray(soupJson);
    } else {
      return res.status(500).json({ error: 'Invalid circuit JSON structure from Gemini.' });
    }

    // Fix the circuit soup format to include required properties
    circuitSoupArray = fixCircuitSoupFormat(circuitSoupArray);

    console.log('Fixed circuitSoupArray:', JSON.stringify(circuitSoupArray, null, 2));

    // circuit-to-svg expects an array, not an object
    const svg = convertCircuitJsonToSchematicSvg(circuitSoupArray);

    return res.json({ svg });
  } catch (err) {
    console.error('Error in /api/generate-svg:', err);
    return res.status(500).json({ error: err.message || 'Unknown error' });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});