def compute(graph, src):
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, u = pq.pop(0)
        for v, w in graph.get(u, []):
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                pq.append((nd, v))
    return dist
