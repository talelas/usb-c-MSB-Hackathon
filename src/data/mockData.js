import { getExtIcon } from "./theme";

// ─── FILE SYSTEM TREE (for left sidebar) ────────────────────────────
export const fileTree = [
  {
    id: "project-alpha",
    name: "Project Alpha",
    type: "folder",
    ext: "folder",
    importance: 1.0,
    group: "alpha",
    children: [
      { id: "main-script", name: "main.py", type: "file", ext: "py", importance: 0.95, group: "alpha", path: "/Project Alpha/main.py" },
      { id: "alpha-utils", name: "utils.py", type: "file", ext: "py", importance: 0.75, group: "alpha", path: "/Project Alpha/utils.py" },
      { id: "alpha-tests", name: "tests.py", type: "file", ext: "py", importance: 0.5, group: "alpha", path: "/Project Alpha/tests.py" },
      { id: "alpha-readme", name: "README.md", type: "file", ext: "md", importance: 0.7, group: "alpha", path: "/Project Alpha/README.md" },
      { id: "alpha-config", name: "config.json", type: "file", ext: "json", importance: 0.6, group: "alpha", path: "/Project Alpha/config.json" },
      { id: "alpha-data", name: "dataset.csv", type: "file", ext: "csv", importance: 0.65, group: "alpha", path: "/Project Alpha/dataset.csv" },
      { id: "alpha-report", name: "report.pdf", type: "file", ext: "pdf", importance: 0.55, group: "alpha", path: "/Project Alpha/report.pdf" },
      { id: "alpha-diagram", name: "architecture.svg", type: "file", ext: "svg", importance: 0.45, group: "alpha", path: "/Project Alpha/architecture.svg" },
      { id: "alpha-notes", name: "dev-notes.txt", type: "file", ext: "txt", importance: 0.3, group: "alpha", path: "/Project Alpha/dev-notes.txt" },
    ],
  },
  {
    id: "project-beta",
    name: "Project Beta",
    type: "folder",
    ext: "folder",
    importance: 0.8,
    group: "beta",
    children: [
      { id: "beta-index", name: "index.jsx", type: "file", ext: "jsx", importance: 0.85, group: "beta", path: "/Project Beta/index.jsx" },
      { id: "beta-api", name: "api.ts", type: "file", ext: "ts", importance: 0.7, group: "beta", path: "/Project Beta/api.ts" },
      { id: "beta-styles", name: "styles.css", type: "file", ext: "css", importance: 0.4, group: "beta", path: "/Project Beta/styles.css" },
      { id: "beta-logo", name: "logo.png", type: "file", ext: "png", importance: 0.25, group: "beta", path: "/Project Beta/logo.png" },
      { id: "beta-spec", name: "spec.pdf", type: "file", ext: "pdf", importance: 0.5, group: "beta", path: "/Project Beta/spec.pdf" },
      { id: "beta-readme", name: "README.md", type: "file", ext: "md", importance: 0.55, group: "beta", path: "/Project Beta/README.md" },
    ],
  },
  {
    id: "project-gamma",
    name: "Project Gamma",
    type: "folder",
    ext: "folder",
    importance: 0.6,
    group: "gamma",
    children: [
      { id: "gamma-script", name: "deploy.js", type: "file", ext: "js", importance: 0.55, group: "gamma", path: "/Project Gamma/deploy.js" },
      { id: "gamma-doc", name: "manual.docx", type: "file", ext: "docx", importance: 0.45, group: "gamma", path: "/Project Gamma/manual.docx" },
      { id: "gamma-data", name: "metrics.json", type: "file", ext: "json", importance: 0.4, group: "gamma", path: "/Project Gamma/metrics.json" },
      { id: "gamma-video", name: "demo.mp4", type: "file", ext: "mp4", importance: 0.35, group: "gamma", path: "/Project Gamma/demo.mp4" },
      { id: "gamma-archive", name: "legacy.zip", type: "file", ext: "zip", importance: 0.2, group: "gamma", path: "/Project Gamma/legacy.zip" },
      { id: "gamma-photo", name: "screenshot.jpg", type: "file", ext: "jpg", importance: 0.15, group: "gamma", path: "/Project Gamma/screenshot.jpg" },
    ],
  },
  {
    id: "shared-folder",
    name: "Shared",
    type: "folder",
    ext: "folder",
    importance: 0.65,
    group: "shared",
    children: [
      { id: "shared-lib", name: "shared-lib.py", type: "file", ext: "py", importance: 0.7, group: "shared", path: "/Shared/shared-lib.py" },
      { id: "shared-types", name: "types.ts", type: "file", ext: "ts", importance: 0.6, group: "shared", path: "/Shared/types.ts" },
    ],
  },
];

// ─── Flatten tree into nodes list for graph ─────────────────────────
const flattenTree = (tree) => {
  const nodes = [];
  tree.forEach((item) => {
    const { children, path, ...nodeData } = item;
    nodes.push({ ...nodeData, path: path || `/${item.name}` });
    if (children) {
      children.forEach((child) => {
        nodes.push(child);
      });
    }
  });
  return nodes;
};

export const graphNodes = flattenTree(fileTree);

export const graphLinks = [
  // Alpha hierarchy
  { source: "project-alpha", target: "main-script" },
  { source: "project-alpha", target: "alpha-readme" },
  { source: "project-alpha", target: "alpha-config" },
  { source: "project-alpha", target: "alpha-utils" },
  { source: "project-alpha", target: "alpha-tests" },
  { source: "project-alpha", target: "alpha-data" },
  { source: "project-alpha", target: "alpha-report" },
  { source: "project-alpha", target: "alpha-diagram" },
  { source: "project-alpha", target: "alpha-notes" },
  { source: "main-script", target: "alpha-utils" },
  { source: "main-script", target: "alpha-config" },
  { source: "alpha-utils", target: "alpha-data" },
  { source: "alpha-tests", target: "main-script" },
  // Beta hierarchy
  { source: "project-beta", target: "beta-index" },
  { source: "project-beta", target: "beta-styles" },
  { source: "project-beta", target: "beta-api" },
  { source: "project-beta", target: "beta-logo" },
  { source: "project-beta", target: "beta-spec" },
  { source: "project-beta", target: "beta-readme" },
  { source: "beta-index", target: "beta-api" },
  { source: "beta-index", target: "beta-styles" },
  // Gamma hierarchy
  { source: "project-gamma", target: "gamma-video" },
  { source: "project-gamma", target: "gamma-archive" },
  { source: "project-gamma", target: "gamma-doc" },
  { source: "project-gamma", target: "gamma-script" },
  { source: "project-gamma", target: "gamma-photo" },
  { source: "project-gamma", target: "gamma-data" },
  // Cross-links
  { source: "alpha-utils", target: "beta-api" },
  { source: "main-script", target: "gamma-script" },
  { source: "alpha-report", target: "beta-spec" },
  { source: "gamma-data", target: "alpha-data" },
  { source: "beta-api", target: "gamma-script" },
  // Shared
  { source: "shared-lib", target: "main-script" },
  { source: "shared-lib", target: "alpha-utils" },
  { source: "shared-lib", target: "beta-api" },
  { source: "shared-types", target: "beta-api" },
  { source: "shared-types", target: "beta-index" },
  { source: "shared-types", target: "gamma-script" },
];

// ─── Mock file content for preview ──────────────────────────────────
export const mockFileContent = {
  "main-script": `#!/usr/bin/env python3
"""Main entry point for Project Alpha."""

import sys
from utils import load_config, preprocess
from shared_lib import initialize

def main():
    config = load_config("config.json")
    data = preprocess("dataset.csv")
    
    print(f"Processing {len(data)} records...")
    results = analyze(data, config)
    
    generate_report(results, "report.pdf")
    print("Done!")

if __name__ == "__main__":
    main()`,

  "alpha-utils": `"""Utility functions for Project Alpha."""

import csv
import json

def load_config(path):
    with open(path) as f:
        return json.load(f)

def preprocess(csv_path):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        return list(reader)

def validate_schema(data, schema):
    """Validate data against schema."""
    pass`,

  "alpha-config": `{
  "project": "Alpha",
  "version": "2.1.0",
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "alpha_db"
  },
  "features": {
    "auth": true,
    "caching": true,
    "logging": "verbose"
  }
}`,

  "beta-index": `import React from 'react';
import { ApiClient } from './api';
import './styles.css';

export default function App() {
  const [data, setData] = React.useState(null);
  
  React.useEffect(() => {
    ApiClient.fetchAll()
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div className="app">
      <h1>Project Beta</h1>
      {data ? <DataGrid data={data} /> : <Spinner />}
    </div>
  );
}`,

  "beta-api": `import type { Config, Response } from './types';

export class ApiClient {
  static baseUrl = '/api/v2';
  
  static async fetchAll(): Promise<Response[]> {
    const res = await fetch(\`\${this.baseUrl}/items\`);
    return res.json();
  }
  
  static async update(id: string, data: Partial<Config>): Promise<void> {
    await fetch(\`\${this.baseUrl}/items/\${id}\`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }
}`,

  "gamma-script": `// Deploy script for Project Gamma
const { execSync } = require('child_process');

async function deploy(env = 'staging') {
  console.log(\`Deploying to \${env}...\`);
  
  execSync('npm run build', { stdio: 'inherit' });
  execSync(\`rsync -avz dist/ server:/app/\${env}/\`);
  
  console.log('Deploy complete!');
}

deploy(process.argv[2]);`,

  "shared-lib": `"""Shared library used across projects."""

def initialize(config=None):
    """Initialize shared resources."""
    print("Initializing shared library...")
    return {"status": "ready"}

def format_output(data, fmt="json"):
    """Format data for output."""
    import json
    if fmt == "json":
        return json.dumps(data, indent=2)
    return str(data)`,

  "shared-types": `export interface Config {
  project: string;
  version: string;
  database: DatabaseConfig;
  features: Record<string, boolean | string>;
}

export interface Response {
  id: string;
  status: 'active' | 'archived';
  data: unknown;
  createdAt: string;
}

export interface DatabaseConfig {
  host: string;
  port: number;
  name: string;
}`,

  "alpha-readme": `# Project Alpha

> Data processing pipeline for analytics.

## Features
- CSV/JSON data ingestion
- Schema validation
- Automated report generation
- Cross-project shared utilities

## Quick Start
\`\`\`bash
python main.py
\`\`\`

## Architecture
See \`architecture.svg\` for system diagram.`,

  "beta-readme": `# Project Beta

> React frontend for data visualization.

## Stack
- React 18 + TypeScript
- Vite build system
- Shared type definitions

## Development
\`\`\`bash
npm install
npm run dev
\`\`\``,

  "alpha-tests": `"""Tests for Project Alpha."""
import unittest
from utils import load_config, preprocess

class TestUtils(unittest.TestCase):
    def test_load_config(self):
        config = load_config("test_config.json")
        self.assertIn("project", config)
    
    def test_preprocess(self):
        data = preprocess("test_data.csv")
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

if __name__ == "__main__":
    unittest.main()`,
};

// ─── Neighbor map builder ───────────────────────────────────────────
export const buildNeighborMap = (links) => {
  const map = new Map();
  links.forEach((l) => {
    const sid = typeof l.source === "object" ? l.source.id : l.source;
    const tid = typeof l.target === "object" ? l.target.id : l.target;
    if (!map.has(sid)) map.set(sid, new Set());
    if (!map.has(tid)) map.set(tid, new Set());
    map.get(sid).add(tid);
    map.get(tid).add(sid);
  });
  return map;
};
