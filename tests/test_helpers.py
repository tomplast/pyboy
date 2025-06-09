import logging
import pytest
from pyboy.cpu import CPU, CPUState


@pytest.fixture
def fixture_cpu():
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)
    return CPU(logger)


def assert_cpu_register(state: CPUState, register_name: str, value: int):
    assert getattr(state, register_name) == value

def assert_cpu_flags(state: CPUState, cf=None, hf=None, nf=None, zf=None):
    if cf is not None:
        assert state.cf == cf
    if hf is not None:
        assert state.hf == hf
    if nf is not None:
        assert state.nf == nf
    if zf is not None:
        assert state.zf == zf
