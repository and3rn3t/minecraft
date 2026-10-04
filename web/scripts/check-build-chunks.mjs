// Fails when the production build no longer produces the vendor chunks.
//
// vite.config.js splits React and Socket.IO out through Rolldown's codeSplitting
// groups. A group that stops matching (a renamed option, a package that moves) does
// not fail the build; the code just falls back into the main chunk and the caching
// benefit is lost without a sign. The build runs in memory, so nothing is written.
//
// Every package below that the build includes must sit in its own vendor chunk. The
// lists are deliberately a separate copy of the ones in vite.config.js: if the check
// read the config's lists, a typo or a dropped package there would change what the
// check expects and it would pass. When a vendor package is added to the config, add
// it here too. (A listed package the app does not bundle is skipped, not an error.)
//
// Run from web/: npm run check:chunks

import { fileURLToPath } from 'node:url';
import { build } from 'vite';

const configFile = fileURLToPath(new URL('../vite.config.js', import.meta.url));

// chunk name -> { anchor, packages }. `packages` are all the packages that belong in the
// chunk; `anchor` is one of them that the app certainly bundles, so an empty or missing
// chunk cannot pass just because nothing was found to check. One structure on purpose: a
// chunk added without its anchor is caught below, not by a confusing error later.
const VENDOR_CHUNKS = {
  'react-vendor': {
    anchor: 'react-dom',
    packages: ['react', 'react-dom', 'scheduler', 'react-router', 'react-router-dom'],
  },
  'socket-vendor': {
    anchor: 'socket.io-client',
    packages: [
      'socket.io-client',
      'socket.io-parser',
      'engine.io-client',
      'engine.io-parser',
      '@socket.io/component-emitter',
    ],
  },
};

for (const [name, { anchor, packages }] of Object.entries(VENDOR_CHUNKS)) {
  if (typeof anchor !== 'string' || !Array.isArray(packages) || !packages.includes(anchor)) {
    console.error(
      `check-build-chunks.mjs is misconfigured: "${name}" needs an anchor package that is also in its packages list.`
    );
    process.exit(2);
  }
}

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
for (const [name, { anchor, packages }] of Object.entries(VENDOR_CHUNKS)) {
  const vendorChunk = chunks.find(c => c.name === name);
  if (!vendorChunk) {
    problems.push(`no "${name}" chunk was produced`);
  } else if (!vendorChunk.modules.some(m => inPackage(m, anchor))) {
    problems.push(`the "${name}" chunk does not contain ${anchor}`);
  }

  for (const pkg of packages) {
    for (const chunk of chunks.filter(
      c => c.name !== name && c.modules.some(m => inPackage(m, pkg))
    )) {
      problems.push(`${pkg} ended up in the "${chunk.name}" chunk instead of "${name}"`);
    }
  }
}

if (problems.length > 0) {
  console.error('Vendor chunk check failed:');
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}
console.log(`Vendor chunks present: ${Object.keys(VENDOR_CHUNKS).join(', ')}`);
