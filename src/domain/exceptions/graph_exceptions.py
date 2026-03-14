class GraphNotFoundError(Exception):
    def __init__(self, graph_id: str) -> None:
        super().__init__(f"Graph not found: {graph_id}")
        self.graph_id = graph_id
