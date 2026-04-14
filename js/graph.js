// js/graph.js — Dijkstra shortest-path + neighbors on the prebuilt edges graph.
//
// Input shape (from dist/edges.json):
//   { "<event_id>": [{ to: "<event_id>", weight: number, via_entity_ids: [...] }, ...], ... }
//
// Weight convention (locked by eng review): LOWER weight = STRONGER edge.
// `weight` is a Dijkstra cost, so summing along a path gives total cost.
// Prefer paths with lower total cost; tie-break on hop-count then
// lex-min of concatenated event IDs (deterministic, hash-stable).
//
// Public API:
//   createGraph(adjacency) -> Graph
//     .shortestPath(fromId, toId) -> { events, edges, cost } | null
//         (alias for shortestPaths(...).paths[0] — backward-compatible single-path call)
//     .shortestPaths(fromId, toId, opts?) -> { paths: [{events,edges,cost},...], optimalCost } | null
//         opts.tolerance (default 0.15) — accept paths with cost <= optimalCost * (1 + tolerance)
//         opts.maxPaths  (default 8)    — cap enumerated alternatives
//         Returns paths sorted by (cost asc, hops asc, lex-min pathKey).
//     .pickPath(paths, seed=0) -> single path | null  — paths[seed % paths.length]
//     .neighbors(id, limit=3) -> [{id, weight, via_entity_ids}, ...]  // 1-hop sort by weight asc
//     .has(id) -> boolean
//     .addVirtualNode(id, targets) -> void  // entity-level Connect support (Stage 4)
//     .removeVirtualNode(id) -> void

// Binary min-heap keyed on .cost (ties broken by .hops then .pathKey).
class MinHeap {
  constructor() {
    this.items = [];
  }

  push(item) {
    this.items.push(item);
    this._bubbleUp(this.items.length - 1);
  }

  pop() {
    if (this.items.length === 0) return null;
    const top = this.items[0];
    const last = this.items.pop();
    if (this.items.length > 0) {
      this.items[0] = last;
      this._sinkDown(0);
    }
    return top;
  }

  get size() {
    return this.items.length;
  }

  _less(a, b) {
    // Primary: cost. Tie: hops. Tie: pathKey lexicographic.
    if (a.cost !== b.cost) return a.cost < b.cost;
    if (a.hops !== b.hops) return a.hops < b.hops;
    return a.pathKey < b.pathKey;
  }

  _bubbleUp(i) {
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this._less(this.items[i], this.items[parent])) {
        [this.items[i], this.items[parent]] = [this.items[parent], this.items[i]];
        i = parent;
      } else {
        break;
      }
    }
  }

  _sinkDown(i) {
    const n = this.items.length;
    while (true) {
      const l = 2 * i + 1;
      const r = 2 * i + 2;
      let smallest = i;
      if (l < n && this._less(this.items[l], this.items[smallest])) smallest = l;
      if (r < n && this._less(this.items[r], this.items[smallest])) smallest = r;
      if (smallest === i) break;
      [this.items[i], this.items[smallest]] = [this.items[smallest], this.items[i]];
      i = smallest;
    }
  }
}

export function createGraph(adjacency) {
  if (!adjacency || typeof adjacency !== 'object') {
    throw new TypeError('createGraph expected adjacency object, got ' + typeof adjacency);
  }

  // Clone so addVirtualNode / removeVirtualNode don't mutate the source.
  const adj = Object.create(null);
  for (const [k, v] of Object.entries(adjacency)) {
    adj[k] = Array.isArray(v) ? [...v] : [];
  }

  const has = (id) => Object.prototype.hasOwnProperty.call(adj, id);

  function shortestPath(fromId, toId) {
    if (typeof fromId !== 'string' || typeof toId !== 'string') {
      throw new TypeError('shortestPath: endpoint ids must be strings');
    }
    if (!has(fromId)) throw new Error(`shortestPath: unknown endpoint ${fromId}`);
    if (!has(toId)) throw new Error(`shortestPath: unknown endpoint ${toId}`);

    // Self-loop: 0-cost path of length 0, just the endpoint.
    if (fromId === toId) {
      return { events: [fromId], edges: [], cost: 0 };
    }

    const best = new Map(); // id -> { cost, hops, pathKey, prev, viaFromPrev }
    const heap = new MinHeap();
    heap.push({ id: fromId, cost: 0, hops: 0, pathKey: fromId, prev: null, viaFromPrev: null });

    while (heap.size > 0) {
      const cur = heap.pop();
      const prior = best.get(cur.id);
      if (prior && !(
        cur.cost < prior.cost ||
        (cur.cost === prior.cost && cur.hops < prior.hops) ||
        (cur.cost === prior.cost && cur.hops === prior.hops && cur.pathKey < prior.pathKey)
      )) {
        continue;
      }
      best.set(cur.id, { cost: cur.cost, hops: cur.hops, pathKey: cur.pathKey, prev: cur.prev, viaFromPrev: cur.viaFromPrev });

      if (cur.id === toId) break;

      for (const edge of adj[cur.id] || []) {
        const w = edge.weight;
        if (typeof w !== 'number' || !Number.isFinite(w)) {
          throw new Error(`graph weight is not a finite number: ${cur.id} -> ${edge.to} has weight ${w}`);
        }
        const nextCost = cur.cost + w;
        const nextHops = cur.hops + 1;
        const nextKey = cur.pathKey + '|' + edge.to;
        const existing = best.get(edge.to);
        if (existing) {
          if (
            nextCost > existing.cost ||
            (nextCost === existing.cost && nextHops > existing.hops) ||
            (nextCost === existing.cost && nextHops === existing.hops && nextKey >= existing.pathKey)
          ) {
            continue;
          }
        }
        heap.push({
          id: edge.to,
          cost: nextCost,
          hops: nextHops,
          pathKey: nextKey,
          prev: cur.id,
          viaFromPrev: edge.via_entity_ids || [],
        });
      }
    }

    if (!best.has(toId)) return null;

    // Reconstruct path.
    const events = [];
    const edges = [];
    let cursor = toId;
    while (cursor !== null) {
      events.unshift(cursor);
      const node = best.get(cursor);
      if (node.prev !== null) {
        edges.unshift({ from: node.prev, to: cursor, via_entity_ids: node.viaFromPrev || [] });
      }
      cursor = node.prev;
    }
    return { events, edges, cost: best.get(toId).cost };
  }

  // K-shortest paths via cost-bounded DFS enumeration.
  // After Dijkstra finds the optimal cost C*, walk every simple path from
  // fromId to toId whose total cost is <= C* * (1 + tolerance). Cap at
  // maxPaths to bound runtime — at our scale (avg degree ~5-6, diameter
  // ~6) this is sub-millisecond. For a small static corpus, this is far
  // simpler than Yen's algorithm and produces the same result.
  function shortestPaths(fromId, toId, opts = {}) {
    if (typeof fromId !== 'string' || typeof toId !== 'string') {
      throw new TypeError('shortestPaths: endpoint ids must be strings');
    }
    if (!has(fromId)) throw new Error(`shortestPaths: unknown endpoint ${fromId}`);
    if (!has(toId)) throw new Error(`shortestPaths: unknown endpoint ${toId}`);

    const tolerance = typeof opts.tolerance === 'number' ? opts.tolerance : 0.15;
    const maxPaths = typeof opts.maxPaths === 'number' ? opts.maxPaths : 8;

    // Self-loop (A === B) is always a single-path 0-cost result.
    if (fromId === toId) {
      const onlyPath = { events: [fromId], edges: [], cost: 0 };
      return { paths: [onlyPath], optimalCost: 0 };
    }

    const optimal = shortestPath(fromId, toId);
    if (!optimal) return null;

    const optimalCost = optimal.cost;
    // Cost ceiling. Add 1e-9 epsilon for floating-point safety on equal-cost ties.
    const costCeiling = optimalCost * (1 + tolerance) + 1e-9;

    const found = [optimal]; // optimal always included
    const optimalKey = optimal.events.join('|');

    // DFS state: stack of { id, cost, hops, events, edges, visited }
    // visited is a Set checked + mutated during DFS to enforce simple paths.
    const visited = new Set([fromId]);
    const eventsStack = [fromId];
    const edgesStack = [];

    function dfs(currentId, currentCost) {
      if (found.length >= maxPaths) return;

      // Prune: remaining cost must be >= 0, so if currentCost > ceiling, drop.
      if (currentCost > costCeiling) return;

      if (currentId === toId) {
        const key = eventsStack.join('|');
        // Skip the optimal path — already in `found`.
        if (key !== optimalKey) {
          found.push({
            events: [...eventsStack],
            edges: [...edgesStack],
            cost: currentCost,
          });
        }
        return;
      }

      for (const edge of adj[currentId] || []) {
        const w = edge.weight;
        if (typeof w !== 'number' || !Number.isFinite(w)) continue;
        if (visited.has(edge.to)) continue;
        const nextCost = currentCost + w;
        if (nextCost > costCeiling) continue;

        visited.add(edge.to);
        eventsStack.push(edge.to);
        edgesStack.push({
          from: currentId,
          to: edge.to,
          via_entity_ids: edge.via_entity_ids || [],
        });

        dfs(edge.to, nextCost);

        edgesStack.pop();
        eventsStack.pop();
        visited.delete(edge.to);
      }
    }

    dfs(fromId, 0);

    // Sort by (cost asc, hops asc, lex-min pathKey).
    found.sort((a, b) => {
      if (a.cost !== b.cost) return a.cost - b.cost;
      if (a.events.length !== b.events.length) return a.events.length - b.events.length;
      const ak = a.events.join('|');
      const bk = b.events.join('|');
      return ak < bk ? -1 : ak > bk ? 1 : 0;
    });

    return { paths: found.slice(0, maxPaths), optimalCost };
  }

  function pickPath(paths, seed = 0) {
    if (!Array.isArray(paths) || paths.length === 0) return null;
    const idx = ((seed % paths.length) + paths.length) % paths.length;
    return paths[idx];
  }

  function neighbors(id, limit = 3) {
    if (!has(id)) throw new Error(`neighbors: unknown id ${id}`);
    const list = (adj[id] || []).slice();
    list.sort((a, b) => {
      if (a.weight !== b.weight) return a.weight - b.weight;
      return a.to < b.to ? -1 : a.to > b.to ? 1 : 0;
    });
    return list.slice(0, limit).map((e) => ({
      id: e.to,
      weight: e.weight,
      via_entity_ids: e.via_entity_ids || [],
    }));
  }

  // Stage 4 helpers: temporarily add a virtual super-source/super-sink node
  // connected by zero-weight edges to a set of real event ids. Used for
  // entity-level Connect (one Dijkstra run, not enumeration).
  function addVirtualNode(id, targets) {
    if (has(id)) throw new Error(`addVirtualNode: id already exists: ${id}`);
    const out = [];
    for (const t of targets) {
      if (!has(t)) continue; // skip unknown targets rather than throw
      out.push({ to: t, weight: 0, via_entity_ids: [] });
      adj[t] = [...adj[t], { to: id, weight: 0, via_entity_ids: [] }];
    }
    adj[id] = out;
  }

  function removeVirtualNode(id) {
    if (!has(id)) return;
    delete adj[id];
    for (const k of Object.keys(adj)) {
      adj[k] = adj[k].filter((e) => e.to !== id);
    }
  }

  return { shortestPath, shortestPaths, pickPath, neighbors, has, addVirtualNode, removeVirtualNode };
}
