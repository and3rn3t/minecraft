"""The error-reporting hook the worker classes share.

Five classes used to carry their own copy of set_error_logger/_log_error. These tests
pin the one rule that matters about it: reporting a failure must never raise, because
it runs on threads that have to keep going.
"""

from pathlib import Path

import pytest

from api.bedtime import Bedtime
from api.error_reporting import ErrorReporting
from api.events import EventBus
from api.hall_of_deaths import HallOfDeaths
from api.oracle import Oracle
from api.pet_cemetery import PetCemetery

PROJECT_ROOT = Path(__file__).parent.parent.parent


class Worker(ErrorReporting):
    """The smallest thing that can report errors."""


class TestErrorReporting:
    def test_reporting_with_no_logger_does_nothing(self):
        Worker()._log_error("nobody is listening")  # must not raise

    def test_the_message_reaches_the_logger(self):
        seen = []
        worker = Worker()
        worker.set_error_logger(seen.append)

        worker._log_error("something broke")

        assert seen == ["something broke"]

    @pytest.mark.parametrize(
        "failure",
        [RuntimeError("logger exploded"), ValueError("I/O operation on closed file"), OSError("broken pipe")],
        ids=["RuntimeError", "closed-file ValueError", "OSError"],
    )
    def test_a_logger_that_fails_is_swallowed(self, failure):
        def broken_logger(_message):
            raise failure

        worker = Worker()
        worker.set_error_logger(broken_logger)

        worker._log_error("report this")  # reporting the failure must not become a second one

    def test_the_worker_keeps_reporting_after_a_logger_failure(self):
        calls = []

        def flaky_logger(message):
            calls.append(message)
            if len(calls) == 1:
                raise RuntimeError("first call fails")

        worker = Worker()
        worker.set_error_logger(flaky_logger)

        worker._log_error("one")
        worker._log_error("two")

        assert calls == ["one", "two"]

    def test_one_instances_logger_is_not_shared_with_another(self):
        first, second = Worker(), Worker()
        seen = []
        first.set_error_logger(seen.append)

        second._log_error("goes nowhere")
        first._log_error("goes to the first")

        assert seen == ["goes to the first"]


@pytest.mark.parametrize("cls", [Bedtime, EventBus, HallOfDeaths, Oracle, PetCemetery])
def test_the_worker_classes_use_the_shared_implementation(cls):
    assert issubclass(cls, ErrorReporting)
    # defined once, on the mixin, not copied into the class
    assert "set_error_logger" not in vars(cls)
    assert "_log_error" not in vars(cls)
