import importlib
import inspect
import os
import sys

import pydot
from loguru import logger
from statemachine import StateMachine
from statemachine.contrib.diagram import DotGraphMachine

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Module holding the meeting state machines (validators, I/O-less).
STATE_MACHINE_MODULE = "mcr_meeting.app.domain.meeting_state_machine"

# Terminal states drawn muted and pushed to the bottom of the graph.
GLOBAL_STATES = ["DELETED"]

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "state_machine")


def create_graph_with_hidden_states(
    machine: type[StateMachine] | StateMachine,
    hidden_states: list[str] | set[str] | None = None,
) -> pydot.Dot:
    """Generate a diagram with the given states visually minimized and positioned
    as sink nodes."""
    hidden_states = set(hidden_states or [])
    dot_graph = DotGraphMachine(machine)()

    if not hidden_states:
        return dot_graph

    sink_subgraph = pydot.Subgraph(rank="sink")

    for node in dot_graph.get_nodes():
        node_name = node.get_name().strip('"')
        if node_name in hidden_states:
            node.set_style("filled")
            node.set_fillcolor("#eeeeee")
            node.set_color("gray")
            node.set_fontcolor("gray")
            sink_subgraph.add_node(node)

    dot_graph.add_subgraph(sink_subgraph)

    for edge in dot_graph.get_edges():
        source = edge.get_source().strip('"')
        dest = edge.get_destination().strip('"')
        if source in hidden_states or dest in hidden_states:
            edge.set_style("dotted")
            edge.set_color("gray")
            edge.set_constraint("false")

    return dot_graph


def main() -> None:
    _import_env()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    module = importlib.import_module(STATE_MACHINE_MODULE)

    total_graphs = 0
    for name, obj in inspect.getmembers(module, inspect.isclass):
        is_local_state_machine = (
            issubclass(obj, StateMachine)
            and obj is not StateMachine
            and obj.__module__ == module.__name__
        )
        if not is_local_state_machine:
            continue

        try:
            graph = create_graph_with_hidden_states(obj(), hidden_states=GLOBAL_STATES)
            output_file = os.path.join(OUTPUT_DIR, f"{name}.png")
            graph.write_png(path=output_file)
            logger.info("Graph generated successfully for {}: {}", name, output_file)
            total_graphs += 1
        except Exception as e:
            logger.error("Error generating graph for {}: {}", name, e)

    logger.info("Summary: {} graph(s) generated in {}.", total_graphs, OUTPUT_DIR)


def _import_env() -> None:
    os.environ.setdefault("DISABLE_DB", "1")
    os.environ.setdefault("POSTGRES_USER", "dummy")
    os.environ.setdefault("POSTGRES_PASSWORD", "dummy")
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_DB", "dummy")
    os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
    os.environ.setdefault("S3_EXTERNAL_ENDPOINT", "http://localhost:9000")
    os.environ.setdefault("S3_ACCESS_KEY", "dummy")
    os.environ.setdefault("S3_SECRET_KEY", "localhost")
    os.environ.setdefault("S3_REGION", "dummy")
    os.environ.setdefault("MCR_FRONTEND_URL", "http://localhost:8080")
    os.environ.setdefault("ENV_MODE", "DEV")
    os.environ.setdefault("REDIS_HOST", "redis")
    os.environ.setdefault("REDIS_PORT", "1234")


if __name__ == "__main__":
    main()
