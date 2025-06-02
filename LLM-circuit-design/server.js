// server.js
import express from "express";
import dotenv from "dotenv";
import bodyParser from "body-parser";
import generateHandler from "./api/generate.js";

dotenv.config(); // loads GEMINI_API_KEY from .env

const app = express();
app.use(bodyParser.json());

// Mount our handler at POST /generate
app.post("/generate", (req, res) => {
  generateHandler(req, res);
});

// Health‐check
app.get("/", (req, res) => {
  res.send("🚀 LLM Circuit API running locally. POST to /generate.");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Listening on http://localhost:${PORT}`));
