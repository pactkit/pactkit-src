from langgraph.graph import StateGraph, END  # noqa: F401

class State:
    messages: list

def researcher_fn(state): ...  # noqa: E704
def writer_fn(state): ...  # noqa: E704
def reviewer_fn(state): ...  # noqa: E704
def route_review(state): ...  # noqa: E704

graph = StateGraph(State)
graph.add_node("researcher", researcher_fn)
graph.add_node("writer", writer_fn)
graph.add_node("reviewer", reviewer_fn)
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "reviewer")
graph.add_conditional_edges(
    "reviewer",
    route_review,
    {"approve": END, "revise": "writer"},
)
app = graph.compile()
