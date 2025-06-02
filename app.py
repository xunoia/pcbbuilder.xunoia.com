# app.py

import os
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from scripts.parser import call_gemini_for_spec
from scripts.template_matcher import match_and_fill_template
from scripts.kicad_generator import generate_kicad_schematic

# 1) Load environment variables from .env
load_dotenv()  

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    prompt = data.get("prompt")
    if not prompt or not isinstance(prompt, str):
        return jsonify({"error": "Missing or invalid 'prompt'."}), 400

    # 2) Parse prompt → spec
    try:
        spec = call_gemini_for_spec(prompt)
    except Exception as e:
        return jsonify({"error": f"Parsing error: {str(e)}"}), 500

    # 3) Spec → Filled JSON template
    try:
        filled = match_and_fill_template(spec)
    except Exception as e:
        return jsonify({"error": f"Template matching error: {str(e)}"}), 500

    # 4) Filled JSON → KiCad schematic
    try:
        schem_path = generate_kicad_schematic(filled, spec)
    except Exception as e:
        return jsonify({"error": f"KiCad generation error: {str(e)}"}), 500

    filename = os.path.basename(schem_path)
    download_url = f"/download/{filename}"

    return jsonify({
        "spec": spec.dict(),
        "filledTemplate": filled,
        "kicad_sch_url": download_url
    })

@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    output_dir = os.getenv("KICAD_OUTPUT_PATH", "./output")
    filepath = os.path.join(output_dir, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": f"File '{filename}' not found."}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    # For local debugging; in Docker, we’ll use gunicorn
    app.run(host="0.0.0.0", port=8080, debug=True)
