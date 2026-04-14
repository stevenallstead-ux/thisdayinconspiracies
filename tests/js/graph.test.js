// Tests for js/graph.js — Dijkstra + neighbors.
// Covers cases spec'd in the eng review issue 3E + CEO review section 6:
//   happy path, disconnected, self-loop (A === B), weight-tie lex-min,
//   NaN/Infinity weight throws, neighbors top-N by weight, neighbors on
//   zero-edge node, missing endpoint id throws.

import { describe, expect, it } from 'vitest';

import { createGraph } from '../../js/graph.js';

function edge(to, weight, via = []) {
  return { to, weight, via_entity_ids: via };
}

describe('createGraph input validation', () => {
  it('throws on non-object adjacency', () => {
    expect(() => createGraph(null)).toThrow(TypeError);
    expect(() => createGraph(undefined)).toThrow(TypeError);
    expect(() => createGraph(42)).toThrow(TypeError);
  });

  it('accepts an empty adjacency', () => {
    const g = createGraph({});
    expect(g.has('anything')).toBe(false);
  });
});

describe('shortestPath — happy path', () => {
  it('finds the only path on a two-hop chain', () => {
    // A --(2)-- B --(3)-- C
    const g = createGraph({
      A: [edge('B', 2, ['x'])],
      B: [edge('A', 2, ['x']), edge('C', 3, ['y'])],
      C: [edge('B', 3, ['y'])],
    });
    const result = g.shortestPath('A', 'C');
    expect(result).not.toBeNull();
    expect(result.events).toEqual(['A', 'B', 'C']);
    expect(result.cost).toBe(5);
    expect(result.edges).toEqual([
      { from: 'A', to: 'B', via_entity_ids: ['x'] },
      { from: 'B', to: 'C', via_entity_ids: ['y'] },
    ]);
  });

  it('picks the lower-cost route when two options exist', () => {
    // A -(1)- B -(1)- C  (total 2)
    // A -(5)- C           (direct 5)
    const g = createGraph({
      A: [edge('B', 1), edge('C', 5)],
      B: [edge('A', 1), edge('C', 1)],
      C: [edge('B', 1), edge('A', 5)],
    });
    const r = g.shortestPath('A', 'C');
    expect(r.cost).toBe(2);
    expect(r.events).toEqual(['A', 'B', 'C']);
  });
});

describe('shortestPath — disconnected', () => {
  it('returns null when no path exists', () => {
    const g = createGraph({
      A: [edge('B', 1)],
      B: [edge('A', 1)],
      X: [edge('Y', 1)],
      Y: [edge('X', 1)],
    });
    expect(g.shortestPath('A', 'X')).toBeNull();
  });
});

describe('shortestPath — self-loop (A === B)', () => {
  it('returns length-0 path with 0 cost', () => {
    const g = createGraph({ A: [edge('B', 1)], B: [edge('A', 1)] });
    const r = g.shortestPath('A', 'A');
    expect(r).toEqual({ events: ['A'], edges: [], cost: 0 });
  });
});

describe('shortestPath — weight ties broken deterministically', () => {
  it('prefers fewer hops when total cost ties', () => {
    // A -(4)- C            (1 hop, cost 4)
    // A -(2)- B -(2)- C    (2 hops, cost 4)
    // Both cost 4; should prefer the 1-hop direct edge.
    const g = createGraph({
      A: [edge('B', 2), edge('C', 4)],
      B: [edge('A', 2), edge('C', 2)],
      C: [edge('B', 2), edge('A', 4)],
    });
    const r = g.shortestPath('A', 'C');
    expect(r.cost).toBe(4);
    expect(r.events).toEqual(['A', 'C']);
  });

  it('breaks hop ties via lex-min path (determinism)', () => {
    // A -(1)- M -(1)- Z  (path A|M|Z)
    // A -(1)- N -(1)- Z  (path A|N|Z)
    // Both cost 2, both 2 hops. Lex-min on pathKey picks A|M|Z.
    const g = createGraph({
      A: [edge('M', 1), edge('N', 1)],
      M: [edge('A', 1), edge('Z', 1)],
      N: [edge('A', 1), edge('Z', 1)],
      Z: [edge('M', 1), edge('N', 1)],
    });
    const r = g.shortestPath('A', 'Z');
    expect(r.events).toEqual(['A', 'M', 'Z']);
  });
});

describe('shortestPath — malformed weight', () => {
  it('throws a named error on NaN weight', () => {
    const g = createGraph({ A: [edge('B', NaN)], B: [] });
    expect(() => g.shortestPath('A', 'B')).toThrow(/weight is not a finite number/);
  });

  it('throws a named error on Infinity weight', () => {
    const g = createGraph({ A: [edge('B', Infinity)], B: [] });
    expect(() => g.shortestPath('A', 'B')).toThrow(/weight is not a finite number/);
  });
});

describe('shortestPath — missing endpoint', () => {
  it('throws on unknown fromId', () => {
    const g = createGraph({ A: [] });
    expect(() => g.shortestPath('BOGUS', 'A')).toThrow(/unknown endpoint/);
  });

  it('throws on unknown toId', () => {
    const g = createGraph({ A: [] });
    expect(() => g.shortestPath('A', 'BOGUS')).toThrow(/unknown endpoint/);
  });
});

describe('neighbors — top-N by weight', () => {
  it('returns up to limit neighbors sorted by weight asc', () => {
    const g = createGraph({
      A: [edge('X', 5), edge('Y', 1), edge('Z', 3)],
      X: [], Y: [], Z: [],
    });
    expect(g.neighbors('A', 3).map((n) => n.id)).toEqual(['Y', 'Z', 'X']);
    expect(g.neighbors('A', 2).map((n) => n.id)).toEqual(['Y', 'Z']);
    expect(g.neighbors('A', 1).map((n) => n.id)).toEqual(['Y']);
  });

  it('tie-breaks equal weights by id ascending', () => {
    const g = createGraph({
      A: [edge('zebra', 1), edge('alpha', 1), edge('middle', 1)],
      alpha: [], middle: [], zebra: [],
    });
    expect(g.neighbors('A', 3).map((n) => n.id)).toEqual(['alpha', 'middle', 'zebra']);
  });

  it('returns empty array for node with zero edges', () => {
    const g = createGraph({ A: [] });
    expect(g.neighbors('A')).toEqual([]);
  });

  it('throws on unknown id', () => {
    const g = createGraph({ A: [] });
    expect(() => g.neighbors('BOGUS')).toThrow(/unknown id/);
  });

  it('includes via_entity_ids in the returned shape', () => {
    const g = createGraph({
      A: [edge('B', 2, ['shared-entity'])],
      B: [],
    });
    expect(g.neighbors('A', 1)).toEqual([
      { id: 'B', weight: 2, via_entity_ids: ['shared-entity'] },
    ]);
  });
});

describe('shortestPaths — K-shortest path enumeration', () => {
  it('returns optimal-only when no alternates are within tolerance', () => {
    // A→B→C is the only path (cost 2); no other route exists.
    const g = createGraph({
      A: [edge('B', 1)],
      B: [edge('A', 1), edge('C', 1)],
      C: [edge('B', 1)],
    });
    const result = g.shortestPaths('A', 'C');
    expect(result.paths).toHaveLength(1);
    expect(result.paths[0].events).toEqual(['A', 'B', 'C']);
    expect(result.optimalCost).toBe(2);
  });

  it('returns multiple paths when costs tie (within tolerance)', () => {
    const g = createGraph({
      A: [edge('M', 1), edge('N', 1)],
      M: [edge('A', 1), edge('Z', 1)],
      N: [edge('A', 1), edge('Z', 1)],
      Z: [edge('M', 1), edge('N', 1)],
    });
    const result = g.shortestPaths('A', 'Z');
    expect(result.paths.length).toBeGreaterThanOrEqual(2);
    const eventStrings = result.paths.map((p) => p.events.join('|'));
    expect(eventStrings).toContain('A|M|Z');
    expect(eventStrings).toContain('A|N|Z');
  });

  it('respects maxPaths cap', () => {
    const adj = {
      A: [edge('B', 1), edge('C', 1), edge('D', 1), edge('E', 1)],
      B: [edge('A', 1), edge('Z', 1)],
      C: [edge('A', 1), edge('Z', 1)],
      D: [edge('A', 1), edge('Z', 1)],
      E: [edge('A', 1), edge('Z', 1)],
      Z: [edge('B', 1), edge('C', 1), edge('D', 1), edge('E', 1)],
    };
    const g = createGraph(adj);
    const result = g.shortestPaths('A', 'Z', { maxPaths: 2 });
    expect(result.paths).toHaveLength(2);
  });

  it('respects tolerance for sub-optimal paths', () => {
    // A→Z direct (cost 10). A→B→Z (cost 11). Tolerance 0.15 accepts both.
    // Tolerance 0.05 rejects the longer route.
    const g = createGraph({
      A: [edge('B', 1), edge('Z', 10)],
      B: [edge('A', 1), edge('Z', 10)],
      Z: [edge('B', 10), edge('A', 10)],
    });
    const wide = g.shortestPaths('A', 'Z', { tolerance: 0.15 });
    expect(wide.paths.length).toBeGreaterThanOrEqual(2);
    const tight = g.shortestPaths('A', 'Z', { tolerance: 0.05 });
    expect(tight.paths).toHaveLength(1);
  });

  it('returns null for disconnected endpoints', () => {
    const g = createGraph({ A: [edge('B', 1)], B: [edge('A', 1)], X: [] });
    expect(g.shortestPaths('A', 'X')).toBeNull();
  });

  it('handles self-loop as single 0-cost path', () => {
    const g = createGraph({ A: [edge('B', 1)], B: [] });
    const result = g.shortestPaths('A', 'A');
    expect(result.paths).toHaveLength(1);
    expect(result.paths[0]).toEqual({ events: ['A'], edges: [], cost: 0 });
    expect(result.optimalCost).toBe(0);
  });
});

describe('pickPath — deterministic seed selection', () => {
  it('returns paths[0] for seed=0 (default)', () => {
    const g = createGraph({
      A: [edge('M', 1), edge('N', 1)],
      M: [edge('A', 1), edge('Z', 1)],
      N: [edge('A', 1), edge('Z', 1)],
      Z: [edge('M', 1), edge('N', 1)],
    });
    const { paths } = g.shortestPaths('A', 'Z');
    expect(g.pickPath(paths)).toBe(paths[0]);
    expect(g.pickPath(paths, 0)).toBe(paths[0]);
  });

  it('different seeds pick different paths when alternates exist', () => {
    const g = createGraph({
      A: [edge('M', 1), edge('N', 1)],
      M: [edge('A', 1), edge('Z', 1)],
      N: [edge('A', 1), edge('Z', 1)],
      Z: [edge('M', 1), edge('N', 1)],
    });
    const { paths } = g.shortestPaths('A', 'Z');
    expect(paths.length).toBeGreaterThanOrEqual(2);
    const a = g.pickPath(paths, 0);
    const b = g.pickPath(paths, 1);
    expect(a).not.toBe(b);
    expect(a.events).not.toEqual(b.events);
  });

  it('seed wraps modulo paths.length (deterministic)', () => {
    const g = createGraph({
      A: [edge('M', 1), edge('N', 1)],
      M: [edge('A', 1), edge('Z', 1)],
      N: [edge('A', 1), edge('Z', 1)],
      Z: [edge('M', 1), edge('N', 1)],
    });
    const { paths } = g.shortestPaths('A', 'Z');
    expect(g.pickPath(paths, paths.length)).toBe(paths[0]);
    expect(g.pickPath(paths, 99)).toBe(paths[99 % paths.length]);
    expect(g.pickPath(paths, -1)).toBe(paths[paths.length - 1]);
  });

  it('returns null for empty paths list', () => {
    const g = createGraph({ A: [] });
    expect(g.pickPath([], 0)).toBeNull();
    expect(g.pickPath(null, 0)).toBeNull();
  });
});

describe('shortestPath backward compatibility', () => {
  it('shortestPath returns the same path as shortestPaths(...).paths[0]', () => {
    const g = createGraph({
      A: [edge('B', 2, ['x'])],
      B: [edge('A', 2, ['x']), edge('C', 3, ['y'])],
      C: [edge('B', 3, ['y'])],
    });
    const single = g.shortestPath('A', 'C');
    const multi = g.shortestPaths('A', 'C');
    expect(single).toEqual(multi.paths[0]);
  });
});

describe('addVirtualNode / removeVirtualNode (entity-level Connect prep)', () => {
  it('routes through virtual source to any target via zero-cost edge', () => {
    const g = createGraph({
      A: [edge('B', 2)],
      B: [edge('A', 2), edge('C', 3)],
      C: [edge('B', 3)],
    });
    g.addVirtualNode('entity:cia', ['A', 'C']);
    const r = g.shortestPath('entity:cia', 'B');
    expect(r).not.toBeNull();
    expect(r.cost).toBe(2); // 0 (entity->A) + 2 (A->B)
    expect(r.events[0]).toBe('entity:cia');
    expect(r.events[r.events.length - 1]).toBe('B');
    g.removeVirtualNode('entity:cia');
    expect(g.has('entity:cia')).toBe(false);
  });

  it('removeVirtualNode is idempotent for unknown ids', () => {
    const g = createGraph({ A: [] });
    expect(() => g.removeVirtualNode('nope')).not.toThrow();
  });
});
