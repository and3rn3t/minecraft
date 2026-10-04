// Fails when the production build no longer produces the vendor chunks.
//
// vite.config.js splits React and Socket.IO out through Rolldown's codeSplitting
// groups. A group that stops matching (a renamed option, a package that moves) does
// not fail the build; the code just falls back into the main chunk and the caching
// benefit is lost without a sign. The build runs in memory, so nothing is written.
//
// Run from web/: npm run check:chunks

import { fileURLToPath } from 'node:url';
import { build } from 'vite';

const configFile = fileURLToPath(new URL('../vite.config.js', import.meta.url));

// chunk name -> a package that must be inside it
const EXPECTED = {
  'react-vendor': 'react-dom',
  'socket-vendor': 'socket.io-client',
};

const inPackage = (modulePath, pkg) =>
  new RegExp(`node_modules[\\\\/]${pkg.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\\\/]`).test(
    modulePath
  );

const result = await build({ configFile, logLevel: 'silent', build: { write: false } });
const chunks = (Array.isArray(result) ? result : [result])
  .flatMap(r => r.output)
  .filter(output => output.type === 'chunk')
  .map(chunk => ({ name: chunk.name, modules: Object.keys(chunk.modules) }));

const problems = [];
for (const [name, pkg] of Object.entries(EXPECTED)) {
  const chunk = chunks.find(c => c.name === name);
  if (!chunk) {
    problems.push(`no "${name}" chunk was produced`);
  } else if (!chunk.modules.some(m => inPackage(m, pkg))) {
    problems.push(`the "${name}" chunk does not contain ${pkg}`);
  }
}
for (const chunk of chunks.filter(c => !(c.name in EXPECTED))) {
  for (const pkg of Object.values(EXPECTED)) {
    if (chunk.modules.some(m => inPackage(m, pkg))) {
      problems.push(`${pkg} ended up in the "${chunk.name}" chunk instead of its vendor chunk`);
    }
  }
}

if (problems.length > 0) {
  console.error('Vendor chunk check failed:');
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}
console.log(`Vendor chunks present: ${Object.keys(EXPECTED).join(', ')}`);
