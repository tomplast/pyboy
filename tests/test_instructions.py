import pytest

from pyboy.opcodes import execute_opcode

from .test_helpers import fixture_cpu as cpu
from .test_cb_instructions import assert_cpu_register, assert_cpu_flags


# 0x0
def test_nop(cpu):
    cpu.load_program(bytes([0x0]))
    cpu.run_next_instruction()


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x04],
        ["C", 0x0C],
        ["D", 0x14],
        ["E", 0x1C],
        ["H", 0x24],
        ["L", 0x2C],
        ["A", 0x3C],
    ],
)
def test_inc_registers_normal(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0x80)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x81)
    assert_cpu_flags(cpu._state, hf=0, nf=0, zf=0)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x04],
        ["C", 0x0C],
        ["D", 0x14],
        ["E", 0x1C],
        ["H", 0x24],
        ["L", 0x2C],
        ["A", 0x3C],
    ],
)
def test_inc_registers_half_carry(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0x0F)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x10)
    assert_cpu_flags(cpu._state, hf=1, nf=0, zf=0)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x04],
        ["C", 0x0C],
        ["D", 0x14],
        ["E", 0x1C],
        ["H", 0x24],
        ["L", 0x2C],
        ["A", 0x3C],
    ],
)
def test_inc_registers_zero_flag(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0xFF)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x00)
    assert_cpu_flags(cpu._state, nf=0, hf=1, zf=1)


@pytest.mark.parametrize(
    "dest_reg, source_reg, opcode",
    [
        ["B", "B", 0x40],
        ["B", "C", 0x41],
        ["B", "D", 0x42],
        ["B", "E", 0x43],
        ["B", "H", 0x44],
        ["B", "L", 0x45],
        ["B", "A", 0x47],
        ["C", "B", 0x48],
        ["C", "C", 0x49],
        ["C", "D", 0x4A],
        ["C", "E", 0x4B],
        ["C", "H", 0x4C],
        ["C", "L", 0x4D],
        ["C", "A", 0x4F],
        ["D", "B", 0x50],
        ["D", "C", 0x51],
        ["D", "D", 0x52],
        ["D", "E", 0x53],
        ["D", "H", 0x54],
        ["D", "L", 0x55],
        ["D", "A", 0x57],
        ["E", "B", 0x58],
        ["E", "C", 0x59],
        ["E", "D", 0x5A],
        ["E", "E", 0x5B],
        ["E", "H", 0x5C],
        ["E", "L", 0x5D],
        ["E", "A", 0x5F],
        ["H", "B", 0x60],
        ["H", "C", 0x61],
        ["H", "D", 0x62],
        ["H", "E", 0x63],
        ["H", "H", 0x64],
        ["H", "L", 0x65],
        ["H", "A", 0x67],
        ["L", "B", 0x68],
        ["L", "C", 0x69],
        ["L", "D", 0x6A],
        ["L", "E", 0x6B],
        ["L", "H", 0x6C],
        ["L", "L", 0x6D],
        ["L", "A", 0x6F],
        ["A", "B", 0x78],
        ["A", "C", 0x79],
        ["A", "D", 0x7A],
        ["A", "E", 0x7B],
        ["A", "H", 0x7C],
        ["A", "L", 0x7D],
        ["A", "A", 0x7F],
    ],
)
def test_ld_reg8_with_reg8(cpu, dest_reg, source_reg, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, source_reg, 0xFA)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, dest_reg, 0xFA)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x05],
        ["C", 0x0D],
        ["D", 0x15],
        ["E", 0x1D],
        ["H", 0x25],
        ["L", 0x2D],
        ["A", 0x3D],
    ],
)
def test_dec_registers_normal(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0x81)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x80)
    assert_cpu_flags(cpu._state, hf=0, nf=1, zf=0)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x05],
        ["C", 0x0D],
        ["D", 0x15],
        ["E", 0x1D],
        ["H", 0x25],
        ["L", 0x2D],
        ["A", 0x3D],
    ],
)
def test_dec_registers_zero_flag(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0x01)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x00)
    assert_cpu_flags(cpu._state, nf=1, hf=0, zf=1)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0x05],
        ["C", 0x0D],
        ["D", 0x15],
        ["E", 0x1D],
        ["H", 0x25],
        ["L", 0x2D],
        ["A", 0x3D],
    ],
)
def test_dec_registers_half_carry(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, 0x10)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0x0F)
    assert_cpu_flags(cpu._state, hf=1, nf=1, zf=0)


@pytest.mark.parametrize(
    "register_name, opcode",
    [
        ["B", 0xB0],
        ["C", 0xB1],
        ["D", 0xB2],
        ["E", 0xB3],
        ["H", 0xB4],
        ["L", 0xB5],
        ["A", 0xB7],
    ],
)
def test_or_register(cpu, register_name, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, "A", 0xAF)
    setattr(cpu._state, register_name, 0xD4)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, 0xD4)
    assert_cpu_flags(cpu._state, nf=0, hf=0, cf=0, zf=0)


@pytest.mark.parametrize(
    "dest_reg, source_reg, opcode",
    [
        ["B", "B", 0x40],
        ["B", "C", 0x41],
        ["B", "D", 0x42],
        ["B", "E", 0x43],
        ["B", "H", 0x44],
        ["B", "L", 0x45],
        ["B", "A", 0x47],
        ["C", "B", 0x48],
        ["C", "C", 0x49],
        ["C", "D", 0x4A],
        ["C", "E", 0x4B],
        ["C", "H", 0x4C],
        ["C", "L", 0x4D],
        ["C", "A", 0x4F],
    ],
)
def test_ld_reg8_reg8(cpu, dest_reg, source_reg, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, source_reg, 0xA3)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, dest_reg, 0xA3)


@pytest.mark.parametrize(
    "source_reg, opcode",
    [
        ["B", 0x70],
        ["C", 0x71],
        ["D", 0x72],
        ["E", 0x73],
        ["H", 0x74],
        ["L", 0x75],
        ["A", 0x77],
    ],
)
def test_ld_mem_hl(cpu, source_reg, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, source_reg, 0xC0)
    cpu._state.HL = 0xC010
    cpu.run_next_instruction()

    value = cpu._state.memory.read(cpu._state.HL)
    expected = 0xC0 if source_reg != "L" else 0x0F
    assert value == expected


@pytest.mark.parametrize(
    "source_reg, opcode",
    [
        ["B", 0xA8],
        ["C", 0xA9],
        ["D", 0xAA],
        ["E", 0xAB],
        ["H", 0xAC],
        ["L", 0xAD],
        ["A", 0xAF],
    ],
)
def test_xor_a(cpu, source_reg, opcode):
    cpu.load_program(bytes([opcode]))
    cpu._state.A = 0xFA
    setattr(cpu._state, source_reg, 0x8E)
    cpu.run_next_instruction()

    expected_value = 0x74 if source_reg != "A" else 0x0
    assert_cpu_register(cpu._state, "A", expected_value)


@pytest.mark.parametrize("register_name, initial_value, final_value, opcode", [
    ['HL', 0x0, 0x1, 0x23],
    ['HL', 0xFFFF, 0x00, 0x23],
    ['sp', 0x0, 0x1, 0x33],
    ['sp', 0xFFFF, 0x00, 0x33],
    ['BC', 0x0, 0x1, 0x03],
    ['BC', 0xFFFF, 0x00, 0x03],
])
def test_inc_reg16(cpu, register_name, initial_value, final_value, opcode):
    cpu.load_program(bytes([opcode]))
    setattr(cpu._state, register_name, initial_value)
    cpu.run_next_instruction()

    assert_cpu_register(cpu._state, register_name, final_value)



def test_interrupt_timing_and_handler_execution(cpu):
    # 1. Lägg ett program i minnet som gör EI följt av NOP
    # 0xFB = EI (Enable Interrupts)
    # 0x00 = NOP
    program = bytearray([0x00] * 0x100) + bytearray([0xFB, 0x00])
    cpu.load_program(program)
    cpu.set_addresses(pc=0x0100)

    # 2. Ställ in en interrupt (t.ex. VBlank)
    mem = cpu._state.memory
    mem.write(0xFFFF, 0b00000001)  # Enable VBlank
    mem.write(0xFF0F, 0b00000001)  # Request VBlank

    # 3. Kör EI → IME ska inte bli True direkt
    cpu.run_next_instruction()
    assert cpu._state.ime == 0
    assert cpu._state.enable_interrupts_after_next_instruction == True

    # 4. Kör nästa instruktion (NOP) → IME ska nu bli True
    cpu.run_next_instruction()
    assert cpu._state.ime == 1

    # 5. Kör en till cykel → Interrupt bör nu hanteras (hoppa till 0x40)
    cpu.run_next_instruction()
    assert cpu._state.pc == 0x0040  # VBlank vector
    assert cpu._state.sp == 0xFFFC  # SP bör minska med 2
    low = mem.read(cpu._state.sp)
    high = mem.read(cpu._state.sp + 1)
    return_addr = (high << 8) | low
    assert return_addr == 0x0102  # Return address (efter EI och NOP)

    # 6. Kontrollera att interrupt-flaggan är nollställd
    assert mem.read(0xFF0F) & 0x01 == 0

    # 7. Extra: skriv till RAM och läs tillbaka med cykler
    old_cycles = mem.CYCLES
    mem.write(0xC123, 0xAB)
    assert mem.read(0xC123) == 0xAB
    assert mem.CYCLES >= old_cycles  # Cykler bör ha ökat
