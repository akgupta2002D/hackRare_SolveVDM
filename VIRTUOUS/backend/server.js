// backend/server.js
// VIRTUOUS backend: Express + CORS + dotenv + simple plain-text routes + request logging

require("dotenv").config();

const express = require("express");
const cors = require("cors");

const app = express();

// ----------- Config -----------
const PORT = Number(process.env.PORT) || 5050;
const CLIENT_ORIGIN = process.env.CLIENT_ORIGIN || "http://localhost:5173";

// ----------- Middleware -----------

// Basic request logger (method, path, status, duration)
app.use((req, res, next) => {
  const start = Date.now();

  res.on("finish", () => {
    const ms = Date.now() - start;
    console.log(
      `[${new Date().toISOString()}] ${req.method} ${req.originalUrl} -> ${res.statusCode} (${ms}ms)`
    );
  });

  next();
});

// CORS for dev frontend
app.use(
  cors({
    origin: CLIENT_ORIGIN,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  })
);

// Parse incoming JSON if/when you start sending it later (safe to keep)
app.use(express.json());

// ----------- Routes -----------

app.get("/", (req, res) => {
  res.status(200).send("VIRTUOUS backend is running.");
});

app.get("/ping", (req, res) => {
  res.status(200).send("pong from VIRTUOUS backend");
});

app.get("/vdm", (req, res) => {
  res.status(200).send("VIRTUOUS is live for VDM.");
});

// Helpful debug route (no secrets)
app.get("/debug/env", (req, res) => {
  res.status(200).send(
    `PORT=${PORT}\nCLIENT_ORIGIN=${CLIENT_ORIGIN}\nNODE_ENV=${process.env.NODE_ENV || ""}\n`
  );
});

// 404 handler (plain text)
app.use((req, res) => {
  res.status(404).send(`Not Found: ${req.method} ${req.originalUrl}`);
});

// Global error handler (plain text)
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err);
  res.status(500).send("Internal Server Error");
});

// ----------- Start -----------

app.listen(PORT, () => {
  console.log("=======================================");
  console.log("VIRTUOUS backend started ✅");
  console.log(`Listening on: http://localhost:${PORT}`);
  console.log(`CORS allowed origin: ${CLIENT_ORIGIN}`);
  console.log("=======================================");
});