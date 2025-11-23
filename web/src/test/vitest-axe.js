/**
 * Vitest-compatible accessibility testing utilities
 * Replaces jest-axe functionality for Vitest
 */
// Import axe-core - it's a CommonJS module
// Use require for CommonJS compatibility in Vitest
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const axeCore = require('axe-core');

/**
 * Run axe-core accessibility tests on a container
 * @param {HTMLElement} container - The container element to test
 * @param {object} options - Axe-core options
 * @returns {Promise<object>} Axe results
 */
export async function axe(container, options = {}) {
  if (!container) {
    throw new Error('Container element is required');
  }

  // Configure axe-core
  const defaultOptions = {
    rules: {
      // Disable color-contrast rule for now as it can be flaky
      'color-contrast': { enabled: false },
    },
    ...options,
  };

  try {
    // Access the run method from axe-core
    const run = axeCore.run || (axeCore.default && axeCore.default.run);
    if (!run || typeof run !== 'function') {
      throw new Error('axe-core run method not found');
    }
    const results = await run(container, defaultOptions);
    return results;
  } catch (error) {
    throw new Error(`Axe-core error: ${error.message}`);
  }
}

/**
 * Custom Vitest matcher to check for accessibility violations
 * Usage: expect(axeResults).toHaveNoViolations()
 */
export function toHaveNoViolations(received) {
  const { pass, message } = checkViolations(received);
  return {
    pass,
    message: () => message,
    actual: received,
    expected: 'no violations',
  };
}

function checkViolations(results) {
  if (!results || typeof results !== 'object') {
    return {
      pass: false,
      message: () => `Expected axe results object, but received: ${typeof results}`,
    };
  }

  const violations = results.violations || [];

  if (violations.length === 0) {
    return {
      pass: true,
      message: () => 'Expected violations, but found none',
    };
  }

  const violationMessages = violations
    .map(violation => {
      const nodes = violation.nodes
        .map(node => {
          const target = node.target.join(', ');
          const failureSummary = node.failureSummary || '';
          return `  - ${target}\n    ${failureSummary}`;
        })
        .join('\n');

      return `${violation.id}: ${violation.description}\n${nodes}`;
    })
    .join('\n\n');

  return {
    pass: false,
    message: () =>
      `Expected no accessibility violations but found ${violations.length}:\n\n${violationMessages}`,
  };
}
