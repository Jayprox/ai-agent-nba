// run_all_checks.js
import { execSync } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log("\n🚀 Running Full Project Preflight Check...\n");

// Helper to run a command safely
const runCommand = (cmd, cwd) => {
  try {
    console.log(`\n🔹 Executing: ${cmd} (${cwd || "current directory"})\n`);
    const output = execSync(cmd, { cwd, stdio: "inherit" });
    return output?.toString() ?? "";
  } catch (err) {
    console.error(`❌ Error running: ${cmd}`);
    console.error(err.message || err);
  }
};

// --- Paths ---
const frontendDir = path.join(__dirname, "ai_agent_app");
const backendDir = path.join(__dirname, "backend");
const frontendCheck = path.join(frontendDir, "sanity_check.js");
const backendCheck = path.join(__dirname, "backend_sanity_check.py");

// --- Validate presence ---
if (!fs.existsSync(frontendCheck)) {
  console.warn(`⚠️  Missing frontend sanity check: ${frontendCheck}`);
}
if (!fs.existsSync(backendCheck)) {
  console.warn(`⚠️  Missing backend sanity check: ${backendCheck}`);
}

// --- Run checks ---
if (fs.existsSync(frontendCheck)) {
  console.log("\n🧩 [1/2] Running Frontend Sanity Check (Node/Vite)\n");
  runCommand(`node ${frontendCheck}`, frontendDir);
}

if (fs.existsSync(backendCheck)) {
  console.log("\n🧠 [2/2] Running Backend Sanity Check (FastAPI)\n");
  runCommand(`python3 ${backendCheck}`, backendDir);
}

console.log("\n✅ All checks completed.\n");
