import fs from 'fs';
import { convertCircuitJsonToKiCadPcb } from 'kicad-converter';
import path from 'path';

const main = () => {
    try {
      const jsonPath = './buck_converter.json';
      const jsonData = fs.readFileSync(jsonPath, 'utf-8');
      const parsed = JSON.parse(jsonData);
    //   const circuitElements = parsed.children;
      const kicadPcbContent = convertCircuitJsonToKiCadPcb(parsed); // fixed here
  
      const outputPath = path.join('output.kicad_pcb');
      fs.writeFileSync(outputPath, typeof kicadPcbContent === 'string' ? kicadPcbContent : JSON.stringify(kicadPcbContent, null, 2), 'utf-8');

  
      console.log('✅ KiCad PCB file generated:', outputPath);
    } catch (err) {
      console.error('❌ Error:', err);
    }
  };

main();