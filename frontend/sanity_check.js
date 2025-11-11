// sanity_check.js
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

console.log("\n🧠 Running AI Agent Setup Sanity Check...\n");

// --- Resolve current directory and find package.json root ---
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let projectRoot = __dirname;
while (!fs.existsSync(path.join(projectRoot, "package.json"))) {
  const parent = path.resolve(projectRoot, "..");
  if (parent === projectRoot) break; // stop if at filesystem root
  projectRoot = parent;
}

if (!fs.existsSync(path.join(projectRoot, "package.json"))) {
  console.error("❌ Could not find package.json in this or any parent directory.");
  process.exit(1);
}

console.log(`📁 Detected project root: ${projectRoot}\n`);
process.chdir(projectRoot);

// --- Paths to check ---
const requiredDirs = ["src", "src/components"];
const requiredFiles = [
  "src/App.jsx",
  "src/main.jsx",
  "vite.config.js",
  "package.json",
];
const requiredPkgs = ["react", "react-dom", "vite", "react-router-dom"];

// --- Check directories ---
for (const dir of requiredDirs) {
  const dirPath = path.join(projectRoot, dir);
  if (!fs.existsSync(dirPath)) {
    console.warn(`⚠️  Missing directory: ${dir}`);
  } else {
    console.log(`✅ Found directory: ${dir}`);
  }
}

// --- Check files ---
for (const file of requiredFiles) {
  const filePath = path.join(projectRoot, file);
  if (!fs.existsSync(filePath)) {
    console.warn(`⚠️  Missing file: ${file}`);
  } else {
    console.log(`✅ Found file: ${file}`);
  }
}

// --- Check packages ---
console.log("\n📦 Checking installed dependencies...\n");
const pkg = JSON.parse(fs.readFileSync(path.join(projectRoot, "package.json")));
const deps = { ...pkg.dependencies, ...pkg.devDependencies };

for (const p of requiredPkgs) {
  if (!deps[p]) {
    console.warn(`❌ Missing dependency: ${p}`);
  } else {
    console.log(`✅ ${p} v${deps[p]}`);
  }
}

// --- Quick version summary ---
try {
  const nodeVer = execSync("node -v").toString().trim();
  const npmVer = execSync("npm -v").toString().trim();
  console.log(`\n🧩 Node version: ${nodeVer}`);
  console.log(`🧩 NPM version: ${npmVer}`);
} catch (error) {
  console.warn(`⚠️ Could not check Node/NPM versions: ${error.message || error}`);
}

console.log("\n✅ Sanity Check Complete.\n");
