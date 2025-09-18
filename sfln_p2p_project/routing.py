import heapq

def calculate_shortest_path(graph, start_node, end_node):
    """
    Calculates the shortest path between two nodes in a graph using Dijkstra's algorithm.

    Args:
        graph (dict): A dictionary representing the network graph.
                      e.g., {'A': {'B': 10, 'C': 20}, 'B': {'A': 10, 'C': 5}}
                      Keys are node names, values are dicts of neighbors and their latency (cost).
        start_node (str): The starting node name.
        end_node (str): The destination node name.

    Returns:
        A tuple containing (path, total_latency).
        Returns (None, float('inf')) if no path exists.
    """
    if start_node not in graph or end_node not in graph:
        return None, float('inf')

    distances = {node: float('inf') for node in graph}
    distances[start_node] = 0

    previous_nodes = {node: None for node in graph}

    pq = [(0, start_node)]

    while pq:
        current_distance, current_node = heapq.heappop(pq)

        if current_distance > distances[current_node]:
            continue

        if current_node == end_node:
            break

        for neighbor, weight in graph.get(current_node, {}).items():
            distance = current_distance + weight

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))

    path = []
    current = end_node
    if distances[current] == float('inf'):
        return None, float('inf')

    while current is not None:
        path.insert(0, current)
        current = previous_nodes.get(current)

    if path and path[0] == start_node:
        return path, distances[end_node]
    else:
        return None, float('inf')
