// Placeholder: gets replaced when js/graph.js lands in the next phase.
// For now, asserts the vitest harness itself works so CI is a meaningful
// green/red signal.

import { describe, expect, it } from 'vitest';

describe('vitest sanity', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2);
  });

  it('has jsdom environment', () => {
    expect(typeof document).toBe('object');
    expect(typeof window).toBe('object');
  });
});
