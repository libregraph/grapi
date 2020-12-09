"""Graph and topological sort module.

In this library we have Adjacency Matrix for graph representation and also
We're using topological sort to get list of vertices which should be executed.
It's useful for batch processing which has "dependsOn" key in the request.
"""
from collections import defaultdict
from queue import Queue


def topological_sort(graph):
    """Topological sort implementation.

    This implementation, iterate over all vertices, if a vertex has "0" in-degree,
    then we put them in the queue and we'll count it as an item in the result, then
    we start getting its adjacent vertices and deducting them by 1 in the in-degree
    table. Then, if any of the adjacent vertices has "0" in-degree (after the deduction),
    then we put it in the queue and then we'll count it as an item in the result.

    Args:
        graph (AdjacencyMatrix): instance of a graph.

    Returns:
        List: list of sorted vertices.

    Raises:
        ValueError: when graph has a cycle.
    """
    zero_indegree_vertices = Queue()
    indegree_table = {}

    # Store in-degrees in a table.
    for i in range(graph.num_vertices):
        indegree_table[i] = graph.get_indegree(i)

        if indegree_table[i] == 0:
            zero_indegree_vertices.put(i)

    # We expect to have at least one "0" in-degree.
    if zero_indegree_vertices.qsize() == 0:
        raise ValueError("graph has cycle")

    result = []
    while not zero_indegree_vertices.empty():
        vertex_id = zero_indegree_vertices.get()
        result.append(vertex_id)

        for adjacent_vertex_id in graph.get_adjacent_vertices(vertex_id):
            # In-degree is getting closer.
            indegree_table[adjacent_vertex_id] -= 1

            if indegree_table[adjacent_vertex_id] == 0:
                zero_indegree_vertices.put(adjacent_vertex_id)

    if len(result) != graph.num_vertices:
        raise ValueError("graph has cycle")

    return result


class AdjacencyMatrix:
    """Adjacency Matrix implementation."""

    def __init__(self, num_vertices):
        """Initialize the class.

        Args:
            num_vertices (int): number of vertices.

        Raises:
            ValueError: invalid range of number.
        """
        if num_vertices <= 0:
            raise ValueError("invalid range of number")

        self.num_vertices = num_vertices

        # creating an empty matrix [x,x]
        self.matrix = [
            [False for _ in range(self.num_vertices)] for _ in range(self.num_vertices)
        ]

    def add_edge(self, v1_id, v2_id):
        """Add edge between 2 vertices.

        Args:
            v1_id (int): first vertex ID.
            v2_id (int): second vertex ID.

        Raises:
            ValueError: when find indirect connection or vertex ID is outbound.
        """
        if v1_id >= self.num_vertices or v2_id >= self.num_vertices or v1_id < 0 or v2_id < 0:
            raise ValueError("vertex ID is outbound")

        if self.matrix[v1_id][v2_id]:
            raise ValueError("find indirect connection")

        self.matrix[v1_id][v2_id] = True

    def get_indegree(self, v_id):
        """Return in-degree of a vertex.

        For example, in-degree of vertex "1", by counting vertically, will be 2.
        +---+---+---+---+
        | * | 0 | 1 | 2 |
        | 0 | F | T | F |
        | 1 | F | F | T |
        | 2 | F | T | F |
        +---+---+---+---+
                  ^

        Args:
            v_id (int): vertex ID.

        Returns:
            int: indegree of the vertex.

        Raises:
            ValueError: vertex ID is outbound.
        """
        if v_id >= self.num_vertices or v_id < 0:
            raise ValueError("vertex ID is outbound")

        in_degree = 0
        for i in range(self.num_vertices):
            if self.matrix[i][v_id]:
                in_degree += 1

        return in_degree

    def get_adjacent_vertices(self, v_id):
        """Return list of adjacent vertices of a specific vertex.

        For example, vertices of vertex "1", by getting horizontally, will be "0" and "2".
          +---+---+---+---+
          | * | 0 | 1 | 2 |
          | 0 | F | F | F |
        > | 1 | T | F | T |
          | 2 | F | T | F |
          +---+---+---+---+

        Args:
            v_id (int): vertex ID.

        Returns:
            Iterable[int]: adjacent vertex ID.

        Raises:
            ValueError: vertex ID is outbound.
        """
        if v_id >= self.num_vertices or v_id < 0:
            raise ValueError("vertex ID is outbound")

        for i in range(self.num_vertices):
            if self.matrix[v_id][i]:
                yield i

    def _get_vertices_connections(self, v_id, result):
        """Get vertices connections and add them to the list.

        Args:
            v_id (int): vertex ID.
            result (Dict[int,Set]): set of vertices connections with associated vertex ID.

        Raises:
            ValueError: vertex ID is outbound.
        """
        if v_id >= self.num_vertices or v_id < 0:
            raise ValueError("vertex ID is outbound")

        for adjacent_v_id in self.get_adjacent_vertices(v_id):
            if adjacent_v_id:
                result[v_id].add(adjacent_v_id)
                self._get_vertices_connections(adjacent_v_id, result)

    def get_vertices_chain(self, v_id):
        """Return list of vertices chain.

        Args:
            v_id (int): vertex ID.

        Returns:
            Dict[int,Set]: chain of vertices.

        Raises:
            ValueError: vertex ID is outbound.
        """
        if v_id >= self.num_vertices or v_id < 0:
            raise ValueError("vertex ID is outbound")

        result = defaultdict(set)
        self._get_vertices_connections(v_id, result)
        return result

    def get_sorted_vertices(self):
        """Return sorted vertices by using topological sorted.

        Returns:
            List: sorted vertices.
        """
        return topological_sort(self)
