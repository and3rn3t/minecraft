// Loaded before setup.js. Under pool: 'vmThreads' each test file runs in a VM
// context whose globals come from jsdom, which has no web streams; MSW's fetch
// interceptor needs them at import time. Node's implementations are
// spec-compliant, so they are borrowed only where jsdom leaves a gap.
import * as streams from 'node:stream/web';

for (const name of ['ReadableStream', 'WritableStream', 'TransformStream', 'TextDecoderStream', 'TextEncoderStream']) {
  if (!(name in globalThis)) {
    globalThis[name] = streams[name];
  }
}
