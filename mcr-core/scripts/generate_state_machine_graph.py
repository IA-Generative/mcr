import importlib
import inspect
import os
import sys
from typing import Union, List, Set

from loguru import logger
from statemachine import StateMachine
from statemachine.contrib.diagram import DotGraphMachine
import pydot

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

GLOBAL_STATES = ["DELETED"]


def create_graph_with_hidden_states(
    machine: Union[type[StateMachine], StateMachine],
    hidden_states: Union[List[str], Set[str]] = None,
) -> pydot.Dot:
    """
    Generate a state machine diagram with specific states visually minimized
    and positioned as sink nodes.
    """
    hidden_states = set(hidden_states or [])
    graph_generator = DotGraphMachine(machine)
    dot_graph = graph_generator()

    if not hidden_states:
        return dot_graph

    # hidden states subgraph
    sink_subgraph = pydot.Subgraph(rank="sink")

    for node in dot_graph.get_nodes():
        node_name = node.get_name().strip('"')

        if node_name in hidden_states:
            # muted styles
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


def main():
    _import_env()

    base_dir = os.path.join("mcr_meeting", "app", "state_machine")
    graph_dir = os.path.join(base_dir, "graph")

    if not os.path.exists(graph_dir):
        os.makedirs(graph_dir)

    total_graphs = 0

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, start=os.getcwd())
                module_path = rel_path[:-3].replace(os.sep, ".")

                try:
                    module = importlib.import_module(module_path)
                except Exception as e:
                    logger.error("Error importing module {}: {}", module_path, e)
                    continue

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, StateMachine) and obj is not StateMachine:
                        try:
                            sm = obj()
                            graph = DotGraphMachine(sm)
                            graph = create_graph_with_hidden_states(
                                sm, hidden_states=GLOBAL_STATES
                            )
                            output_file = os.path.join(graph_dir, f"{name}.png")
                            graph.write_png(path=output_file)
                            logger.info(
                                "Graph generated successfully for {}: {}",
                                name,
                                output_file,
                            )
                            total_graphs += 1
                        except Exception as e:
                            logger.error(
                                "Error generating graph for {} in {}: {}",
                                name,
                                module_path,
                                e,
                            )

    logger.info("Summary: {} graph(s) generated.", total_graphs)


def _import_env():
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
    os.environ.setdefault("MCR_FRONTEND_URL", "http://localhost:8881")
    os.environ.setdefault("ENV_MODE", "DEV")
    os.environ.setdefault("REDIS_HOST", "redis")
    os.environ.setdefault("REDIS_PORT", "1234")


if __name__ == "__main__":
    main()
