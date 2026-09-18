#!/usr/bin/env node
/**
 * scripts/assert-no-client-localhost.mjs
 *
 * CI/CD & Build Guard:
 * Scans all client-facing production code and bundles to ensure that no hardcoded
 * loopback URLs ('localhost', '127.0.0.1', '0.0.0.0') are present in production client files.
 *
 * Returns exit code 0 if all clean.
 * Returns exit code 1 if forbidden patterns are detected.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

// Scan targets
const TARGET_DIRS = [
  path.join(ROOT_DIR, 'frontend', 'admin'),
  path.join(ROOT_DIR, 'frontend', 'client'),
  path.join(ROOT_DIR, 'apps', 'web-admin', 'src'),
];

// If apps/web-admin/dist exists, scan it too
const DIST_DIR = path.join(ROOT_DIR, 'apps', 'web-admin', 'dist');
if (fs.existsSync(DIST_DIR)) {
  TARGET_DIRS.push(DIST_DIR);
}

// Patterns forbidden in production client code
const FORBIDDEN_PATTERNS = [
  /http:\/\/localhost:8000/g,
  /http:\/\/127\.0\.0\.1:8000/g,
  /http:\/\/0\.0\.0\.0:8000/g,
];

// Allowed exceptions (e.g., comments or guard checks that explicitly detect/reject localhost)
const ALLOWED_MATCHES = [
  'console.warn("[Admin API] Rejecting localhost',
  'console.warn("[Client API] Rejecting localhost',
  'Falling back to same-origin \'/api/v1\'',
  'window.location.hostname !== "localhost"',
  'FORBIDDEN_PROD_HOSTNAMES',
  'cleanUrl.toLowerCase().includes(forbidden)',
];

let totalViolations = 0;
const scannedFiles = [];

function scanFile(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (!['.js', '.mjs', '.ts', '.tsx', '.html', '.css'].includes(ext)) {
    return;
  }

  scannedFiles.push(filePath);
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  lines.forEach((line, lineIndex) => {
    // Check if line is an allowed exception
    if (ALLOWED_MATCHES.some((allowed) => line.includes(allowed))) {
      return;
    }

    FORBIDDEN_PATTERNS.forEach((pattern) => {
      pattern.lastIndex = 0;
      if (pattern.test(line)) {
        console.error(
          `\x1b[31m[FAIL]\x1b[0m ${path.relative(ROOT_DIR, filePath)}:${lineIndex + 1}`
        );
        console.error(`       \x1b[33m${line.trim()}\x1b[0m\n`);
        totalViolations++;
      }
    });
  });
}

function walkDir(dir) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== 'node_modules' && entry.name !== '.git') {
        walkDir(fullPath);
      }
    } else if (entry.isFile()) {
      scanFile(fullPath);
    }
  }
}

console.log('\n🔍 ========================================================');
console.log('   SCANNING CLIENT SOURCE CODE & BUNDLES FOR LOCALHOST');
console.log('   ========================================================\n');

for (const target of TARGET_DIRS) {
  if (fs.existsSync(target)) {
    console.log(`Scanning: ${path.relative(ROOT_DIR, target)}/`);
    walkDir(target);
  }
}

console.log(`\nTotal client files scanned: ${scannedFiles.length}`);

if (totalViolations > 0) {
  console.error(
    `\n❌ BUILD GUARD FAILED: Found ${totalViolations} instance(s) of forbidden loopback URLs in client code!`
  );
  console.error(
    '   Please use same-origin relative URLs (/api/v1) or centralized runtime configuration.'
  );
  process.exit(1);
} else {
  console.log('✅ BUILD GUARD PASSED: Zero forbidden loopback URLs detected in client code.\n');
  process.exit(0);
}
