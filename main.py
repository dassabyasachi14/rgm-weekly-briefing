from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph
from state import RGMState
from nodes.load_data import load_data
from nodes.compute_metrics import compute_metrics
from nodes.generate_narrative import generate_narrative
from nodes.evaluate_narratives import evaluate_narratives
from nodes.revise_narratives import revise_narratives
from nodes.format_output import format_output


def build_graph():
    graph = StateGraph(RGMState)

    graph.add_node("load_data", load_data)
    graph.add_node("compute_metrics", compute_metrics)
    graph.add_node("generate_narrative", generate_narrative)
    graph.add_node("evaluate_narratives", evaluate_narratives)
    graph.add_node("revise_narratives", revise_narratives)
    graph.add_node("format_output", format_output)

    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "compute_metrics")
    graph.add_edge("compute_metrics", "generate_narrative")
    graph.add_edge("generate_narrative", "evaluate_narratives")
    graph.add_edge("evaluate_narratives", "revise_narratives")
    graph.add_edge("revise_narratives", "format_output")

    return graph.compile()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    app = build_graph()
    app.invoke({})
