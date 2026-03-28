import heapq

DATA_PATH = '/Users/student/Desktop/private/input.csv'


def run_full_pipeline():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def dijkstra(graph, src):
    dist = {node: float('inf') for node in graph}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


if __name__ == '__main__':
    print(run_full_pipeline())
