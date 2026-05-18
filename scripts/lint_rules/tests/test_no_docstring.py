from __future__ import annotations

import textwrap
from pathlib import Path

from no_docstring import RULE_NAME, Violation, collect_violations, format_for_cli, main


def _write(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    file_path = tmp_path / name
    file_path.write_text(textwrap.dedent(source).lstrip("\n"))
    return file_path


def test_bare_def_with_docstring_is_violation(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        def helper():
            \"\"\"explains the helper.\"\"\"
            return 1
        """,
    )

    violations = collect_violations(file_path)

    assert [v.symbol for v in violations] == ["helper"]


def test_router_get_decorated_def_is_public(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @router.get(\"/x\")
        def list_things():
            \"\"\"List things.\"\"\"
            return []
        """,
    )

    assert collect_violations(file_path) == []


def test_custom_router_instance_is_public(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @meeting_scoped_router.post(\"/x\")
        def create():
            \"\"\"Create.\"\"\"
            return None
        """,
    )

    assert collect_violations(file_path) == []


def test_celery_signal_handler_is_public(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @task_success.connect
        def on_success(sender, result, **kwargs):
            \"\"\"Handle success.\"\"\"
            return None
        """,
    )

    assert collect_violations(file_path) == []


def test_celery_task_is_public(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @celery_app.task(name=\"x\")
        def run():
            \"\"\"Run.\"\"\"
            return None
        """,
    )

    assert collect_violations(file_path) == []


def test_line_marker_suppresses_violation(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        def helper():  # lint-ignore: no-docstring
            \"\"\"genuinely-complex helper.\"\"\"
            return 1
        """,
    )

    assert collect_violations(file_path) == []


def test_module_docstring_is_violation(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        '''
        """Module-level docstring."""

        x = 1
        ''',
    )

    violations = collect_violations(file_path)

    assert [(v.symbol, v.lineno) for v in violations] == [("<module>", 1)]


def test_module_oneline_docstring_with_inline_marker_is_clean(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        '''
        """Module-level docstring."""  # lint-ignore: no-docstring

        x = 1
        ''',
    )

    assert collect_violations(file_path) == []


def test_module_multiline_docstring_with_marker_above_is_clean(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        '''
        # lint-ignore: no-docstring
        """Multi-line module docstring.

        Second paragraph explaining things.
        """

        x = 1
        ''',
    )

    assert collect_violations(file_path) == []


def test_file_level_marker_disables_check_everywhere(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        '''
        # lint-ignore-file: no-docstring
        """Module docstring is fine."""


        def foo():
            """Private docstring is also fine."""
            return 1


        class Bar:
            """Class docstring is fine too."""

            def baz(self):
                """Method docstring is fine."""
                return 1
        ''',
    )

    assert collect_violations(file_path) == []


def test_file_level_marker_works_anywhere_in_the_file(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        '''
        """Module docstring."""

        # lint-ignore-file: no-docstring


        def foo():
            """still allowed."""
            return 1
        ''',
    )

    assert collect_violations(file_path) == []


def test_underscore_method_without_decorator_is_violation(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        class Foo:
            def _helper(self):
                \"\"\"x\"\"\"
                return 1
        """,
    )

    violations = collect_violations(file_path)

    assert [v.symbol for v in violations] == ["_helper"]


def test_class_with_no_docstring_is_clean(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        class Foo:
            def method(self):
                return 1
        """,
    )

    assert collect_violations(file_path) == []


def test_dataclass_with_docstring_is_violation(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @dataclass
        class Foo:
            \"\"\"Internal record.\"\"\"
            x: int
        """,
    )

    violations = collect_violations(file_path)

    assert [v.symbol for v in violations] == ["Foo"]


def test_async_def_is_handled(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        async def helper():
            \"\"\"x\"\"\"
            return 1
        """,
    )

    assert [v.symbol for v in collect_violations(file_path)] == ["helper"]


def test_nested_def_inside_public_route_is_still_private(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        """
        @router.get(\"/x\")
        def endpoint():
            def inner():
                \"\"\"this is private even though parent is public.\"\"\"
                return 1
            return inner()
        """,
    )

    violations = collect_violations(file_path)

    assert [v.symbol for v in violations] == ["inner"]


def test_main_returns_1_when_violations_found(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
        def helper():
            \"\"\"x\"\"\"
        """,
    )

    assert main([str(tmp_path)]) == 1


def test_main_returns_0_on_clean_dir(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
        @router.get(\"/x\")
        def endpoint():
            \"\"\"x\"\"\"
        """,
    )

    assert main([str(tmp_path)]) == 0


def test_excluded_dirs_are_skipped(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text('def t():\n    """x"""\n')

    assert main([str(tmp_path)]) == 0


def test_violation_carries_rule_name() -> None:
    v = Violation(path=Path("a.py"), lineno=3, symbol="foo")

    assert v.rule == RULE_NAME == "no-docstring"


def test_format_for_cli_no_color_includes_path_line_rule_and_explainer() -> None:
    v = Violation(path=Path("a.py"), lineno=3, symbol="foo")

    msg = format_for_cli(v, use_color=False)

    assert msg.startswith("a.py:3: no-docstring: ")
    assert "foo" in msg
    assert "lint-ignore: no-docstring" in msg
    assert "\033[" not in msg


def test_format_for_cli_with_color_wraps_line_in_bold_and_rule_in_red() -> None:
    v = Violation(path=Path("a.py"), lineno=42, symbol="foo")

    msg = format_for_cli(v, use_color=True)

    assert "\033[1m42\033[0m" in msg
    assert "\033[31mno-docstring\033[0m" in msg
    assert "foo" in msg
    assert "lint-ignore: no-docstring" in msg


