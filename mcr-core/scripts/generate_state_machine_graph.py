import importlib
import inspect
import os
import sys

from loguru import logger
from statemachine import StateMachine
from statemachine.contrib.diagram import DotGraphMachine

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


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
                            output_file = os.path.join(graph_dir, f"{name}.png")
                            graph().write_png(path=output_file)
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
