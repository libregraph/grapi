"""Test graph module."""
from collections import defaultdict

from grapi.api.v1.graph import AdjacencyMatrix


def test_graph():
    """Correct tests."""
    graph = AdjacencyMatrix(4)
    graph.add_edge(0, 1)
    graph.add_edge(1, 3)

    assert graph.num_vertices == 4

    assert graph.get_indegree(0) == 0
    assert graph.get_indegree(3) == 1
    assert graph.get_indegree(1) == 1

    assert list(graph.get_adjacent_vertices(0)) == [1]
    assert list(graph.get_adjacent_vertices(1)) == [3]
    assert list(graph.get_adjacent_vertices(2)) == []

    assert graph.get_vertices_chain(0) == defaultdict(set, {0: {1}, 1: {3}})
    assert graph.get_vertices_chain(1) == defaultdict(set, {1: {3}})
    assert graph.get_vertices_chain(2) == defaultdict(set)

    assert graph.get_sorted_vertices() == [0, 2, 1, 3]


def test_incorrect_data_graph():
    """Test graph with incorrect data."""
    try:
        AdjacencyMatrix(0)
    except ValueError:
        assert True

    graph = AdjacencyMatrix(4)

    try:
        graph.add_edge(1, 4)
    except ValueError:
        assert True

    try:
        graph.add_edge(-1, 3)
    except ValueError:
        assert True

    assert graph.get_indegree(0) == 0
    assert graph.get_indegree(1) == 0
    assert graph.get_indegree(2) == 0
    assert graph.get_indegree(3) == 0

    assert list(graph.get_adjacent_vertices(0)) == []
    assert list(graph.get_adjacent_vertices(1)) == []
    assert list(graph.get_adjacent_vertices(2)) == []
    assert list(graph.get_adjacent_vertices(3)) == []

    assert graph.get_vertices_chain(0) == defaultdict(set)
    assert graph.get_vertices_chain(1) == defaultdict(set)
    assert graph.get_vertices_chain(2) == defaultdict(set)
    assert graph.get_vertices_chain(3) == defaultdict(set)

    assert graph.get_sorted_vertices() == [0, 1, 2, 3]
