import pytest


from .test_helpers import fixture_cpu as cpu
from .test_helpers import assert_cpu_flags, assert_cpu_register


@pytest.mark.parametrize("register_name, opcode", [
    ["B", 0x0],
    ["C", 0x1],
    ["D", 0x2],
    ["E", 0x3],
    ["H", 0x4],
    ["L", 0x5],
])
def test_cb_rlc_register(cpu, register_name, opcode):
    cpu.load_program(bytes([0xCB, opcode]))
    setattr(cpu._state, register_name, 0x80)
    cpu.run_next_instruction()

    assert_cpu_flags(cpu._state, cf=1, zf=0)

def test_cb_rlc_memory_variant(cpu):
    pytest.fail('Not implemented yet')

