from collections import deque

def topological_sort(graph):
    in_degree = {u: 0 for u in graph}  # determine in-degree of each node
    for u in graph:  # for each node
        for v in graph[u]:  # for each neighbor
            in_degree[v] += 1  # increment in-degree

    Q = deque()  # collect nodes with zero in-degree
    for u in in_degree:
        if in_degree[u] == 0:
            Q.appendleft(u)

    L = []  # list for order of nodes

    while Q:
        u = Q.pop()  # choose node of zero in-degree
        L.append(u)  # add it to the list
        for v in graph[u]:  # for each neighbor
            in_degree[v] -= 1  # decrement in-degree
            if in_degree[v] == 0:
                Q.appendleft(v)  # add neighbor of zero in-degree to queue

    if len(L) == len(graph):
        return L  # if graph has a cycle
    else:  # pragma: no cover
        return []  # a topological sort is not possible.
