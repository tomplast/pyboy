from dataclasses import dataclass
from typing import Callable, Dict


@dataclass
class Instruction:
    instruction: int
    operand_count: int
    handler: Callable
    cycle_count: int


instruction_table: Dict[str, Instruction] = {}
cb_instruction_table: Dict[str, Instruction] = {}


def register_cb_instruction(instruction: int, operand_count: int, cycle_count: int = 4):
    def decorator(fn):
        cb_instruction_table[instruction] = Instruction(
            instruction, operand_count, fn, cycle_count
        )
        return fn

    return decorator


def register_instruction(instruction: int, operand_count: int, cycle_count: int = 4):
    def decorator(fn):
        instruction_table[instruction] = Instruction(
            instruction, operand_count, fn, cycle_count
        )
        return fn

    return decorator


def check_interrupts(logger, cpu):
    ie = cpu._state.memory.read(0xFFFF)  # IE
    interrupt_flags = cpu._state.memory.read(0xFF0F)  # IF

    if (ie & interrupt_flags) != 0:
        cpu._state._halted = False

    if cpu._state.ime and (ie & interrupt_flags) != 0:
        cpu._state.ime = 0

        # V-Blank
        if ie & interrupt_flags & 0x01:
            vector = 0x40

        # LCD STAT
        elif ie & interrupt_flags & 0x02:
            vector = 0x48

        # Timer
        elif ie & interrupt_flags & 0x04:
            vector = 0x50
            # logger.info(f'Timer interrupt was triggered. ie: {ie}, if: {interrupt_flags} ')

        # Serial
        elif ie & interrupt_flags & 0x08:
            vector = 0x58

        # Joypad
        elif ie & interrupt_flags & 0x10:
            vector = 0x60
        else:
            return

        cpu._state.memory.write(0xFF0F, interrupt_flags & ~(ie & interrupt_flags))
        cpu._state.SP -= 1
        cpu._state.memory.write(cpu._state.SP, (cpu._state.pc >> 8) & 0xFF)
        cpu._state.SP -= 1
        cpu._state.memory.write(cpu._state.SP, cpu._state.pc & 0xFF)

        cpu._state.pc = vector


def execute_opcode(self, logger, instruction):
    entry = None
    if instruction[0] == 0xCB:
        if instruction[1] not in cb_instruction_table:
            raise Exception(f"Unknown cb opcode {instruction[1]:01X}")
        entry = cb_instruction_table[instruction[1]]

    elif instruction[0] in instruction_table:
        entry = instruction_table[instruction[0]]
    else:
        raise Exception(f"Unknown opcode {instruction[0]:04X}")

    # TODO: NÄR MINNET LÄSES FRÅN FF00+80 så är värdet fel!
    # print(f'Will run {entry.handler.__name__}!')
    cycle_count = entry.handler(logger, self, instruction) or entry.cycle_count
    return cycle_count
    # print(f'Done running {entry.handler.__name__}!')
    # if new_address != old_address:
    #    print(f'{self._state.pc:02X} - Jumped from {old_address:02X} to {new_address:02X}!')


def push(state, low_byte: int, high_byte: int):
    state.SP -= 1
    state.memory.write(state.SP, low_byte & 0xFF)

    state.SP -= 1
    state.memory.write(state.SP, high_byte & 0xFF)

    # state.memory.add_cycles(4)


def pop(state) -> tuple[int, int]:
    low = state.memory.read(state.SP)  # F, C, L etc.
    state.SP += 1
    high = state.memory.read(state.SP)  # A, B, H etc.
    state.SP += 1
    return (low, high)


@register_cb_instruction(0x1B, 0, 8)
def handle_cb_rr_e(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "E")


def handle_generic_sbc_a(state, register_name):
    value = None
    if register_name == "(HL)":
        value = state.memory.read(state.HL)
    else:
        value = getattr(state, register_name)

    carry = state.cf

    result = state.A - value - carry

    state.zf = 1 if (result & 0xFF) == 0 else 0
    state.nf = 1
    state.hf = 1 if (state.A & 0xF) < ((value & 0xF) + carry) else 0
    state.cf = 1 if result < 0 else 0

    state.A = result & 0xFF


@register_instruction(0x98, 0, 4)
def handle_sbc_a_b(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "B")


@register_instruction(0x99, 0, 4)
def handle_sbc_a_c(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "C")


@register_instruction(0x9A, 0, 4)
def handle_sbc_a_d(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "D")


@register_instruction(0x9B, 0, 4)
def handle_sbc_a_e(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "E")


@register_instruction(0x9C, 0, 4)
def handle_sbc_a_h(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "H")


@register_instruction(0x9D, 0, 4)
def handle_sbc_a_l(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "L")


@register_instruction(0x9E, 0, 4)
def handle_sbc_a_hl_mem(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "(HL)")


@register_instruction(0x9F, 0, 4)
def handle_sbc_a_a(logger, cpu, instruction):
    handle_generic_sbc_a(cpu._state, "A")


@register_cb_instruction(0x19, 0, 8)
def handle_cb_rr_c(logger, cpu, instruction):
    old_carry = cpu._state.cf
    value = cpu._state.C

    new_carry = value & 0x01
    result = (value >> 1) | (old_carry << 7)

    cpu._state.C = result
    cpu._state.zf = 1 if result == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = new_carry


@register_cb_instruction(0x1A, 0, 8)
def handle_cb_rr_d(logger, cpu, instruction):
    old_carry = cpu._state.cf
    value = cpu._state.D

    new_carry = value & 0x01
    result = (value >> 1) | (old_carry << 7)

    cpu._state.D = result
    cpu._state.zf = 1 if result == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = new_carry


@register_instruction(0x0, 0, 4)
def handle_nop(logger, cpu, instruction):
    pass


def handle_cb_generic_rlc(state, register_name):
    old_bit7 = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        old_bit7 = (value >> 7) & 0x01
        result = ((value << 1) & 0xFF) | old_bit7
        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        old_bit7 = (value >> 7) & 0x01
        result = ((value << 1) & 0xFF) | old_bit7
        setattr(state, register_name, result)

    # state.B = result
    state.cf = old_bit7
    state.nf = 0
    state.hf = 0
    state.zf = 1 if result == 0 else 0


@register_cb_instruction(0x00, 8)
def handle_cb_rlcb(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "B")


@register_cb_instruction(0x01, 8)
def handle_cb_rlcc(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "C")


@register_cb_instruction(0x02, 8)
def handle_cb_rlcd(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "D")


@register_cb_instruction(0x03, 8)
def handle_cb_rlce(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "E")


@register_cb_instruction(0x04, 0, 8)
def handle_cb_rlch(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "H")


@register_cb_instruction(0x05, 0, 8)
def handle_cb_rlcl(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "L")


@register_cb_instruction(0x06, 0, 16)
def handle_cb_rlc_hl_mem(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "(HL)")


@register_cb_instruction(0x07, 0, 8)
def handle_cb_rlc_a(logger, cpu, instruction):
    handle_cb_generic_rlc(cpu._state, "A")


@register_instruction(0x1F, 0, 4)
def handle_rr_a(logger, cpu, instruction):
    old_carry = cpu._state.cf
    value = cpu._state.A

    new_carry = value & 0x01
    result = (value >> 1) | (old_carry << 7)

    cpu._state.A = result
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = new_carry
    cpu._state.zf = 0  # CHATGPU SUGGESTION


@register_instruction(0x27, 0, 4)
def handle_daa(logger, cpu, instruction):
    a = cpu._state.A
    adjust = 0
    carry = cpu._state.cf

    if not cpu._state.nf:  # after addition
        if cpu._state.hf or (a & 0x0F) > 9:
            adjust |= 0x06
        if carry or a > 0x99:
            adjust |= 0x60
            carry = 1
        a = (a + adjust) & 0xFF
    else:  # after subtraction
        if cpu._state.hf:
            adjust |= 0x06
        if cpu._state.cf:
            adjust |= 0x60
        a = (a - adjust) & 0xFF

    cpu._state.A = a
    cpu._state.zf = 1 if a == 0 else 0
    cpu._state.hf = 0
    cpu._state.cf = carry


@register_instruction(0x10, 0, 8)
def handle_stop(logger, cpu, instruction):
    logger.debug("STOP instruction executed")
    # STOP är två bytes: 0x10 + nästa byte (som oftast är 0x00)
    cpu._state.pc += 1  # hoppa över extra byte
    # Ingen flagga sätts, ingen effekt på register — bara ignorera


@register_instruction(0x07, 0, 4)
def handle_rlca(logger, cpu, instruction):
    value = cpu._state.A
    old_bit7 = (value >> 7) & 0x01
    result = ((value << 1) | old_bit7) & 0xFF

    cpu._state.A = result
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = old_bit7
    cpu._state.zf = 0  # CHATGPT SUGGESTION


@register_instruction(0xC3, 2, 16)
def handle_jp(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)
    # logger.debug(f"Setting PC to address {address:02X}")
    cpu._state.pc = address


@register_instruction(0x21, 2, 12)
def handle_ld_hl(logger, cpu, instruction):
    cpu._state.HL = instruction[1] | (instruction[2] << 8)


@register_instruction(0x47, 0, 4)
def handle_ld_b_a(logger, cpu, instruction):
    cpu._state.B = cpu._state.A


@register_instruction(0x4F, 0, 4)
def handle_ld_c_a(logger, cpu, instruction):
    cpu._state.C = cpu._state.A


@register_instruction(0x11, 2, 12)
def handle_ld_de(logger, cpu, instruction):
    value = instruction[1] | (instruction[2] << 8)
    cpu._state.DE = value


@register_instruction(0x0E, 1, 8)
def handle_ld_c_n8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.C = value


@register_instruction(0x6E, 0, 8)
def handle_ld_l_hl_mem_address(logger, cpu, instruction):
    cpu._state.L = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x4E, 0, 8)
def handle_ld_c_hl_mem_address(logger, cpu, instruction):
    cpu._state.C = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x2A, 0, 8)
def handle_ld_a_hl_increment(logger, cpu, instruction):
    cpu._state.A = cpu._state.memory.read(cpu._state.HL)
    cpu._state.HL = (cpu._state.HL + 1) & 0xFFFF


@register_instruction(0x3A, 0, 8)
def handle_ld_a_hl_decrement(logger, cpu, instruction):
    cpu._state.A = cpu._state.memory.read(cpu._state.HL)
    cpu._state.HL = (cpu._state.HL - 1) & 0xFFFF


@register_instruction(0x46, 0, 8)
def handle_ld_b_hl_mem_address(logger, cpu, instruction):
    cpu._state.B = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x23, 0, 8)
def handle_inc_hl(logger, cpu, instruction):
    cpu._state.HL = (cpu._state.HL + 1) & 0xFFFF


def handle_generic_inc(state, register_name):
    old_value = None
    new_value = None

    if register_name == "(HL)":
        old_value = state.memory.read(state.HL)
        new_value = (old_value + 1) & 0xFF
        state.memory.write(state.HL, new_value)
    else:
        old_value = getattr(state, register_name)
        new_value = (old_value + 1) & 0xFF
        setattr(state, register_name, new_value)

    state.zf = 1 if new_value == 0 else 0
    state.nf = 0
    state.hf = 1 if (old_value & 0x0F) == 0x0F else 0


@register_instruction(0x3C, 0, 4)
def handle_inc_a(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "A")


@register_instruction(0x0C, 0, 4)
def handle_inc_c(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "C")


@register_instruction(0x04, 0, 4)
def handle_inc_b(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "B")


@register_instruction(0x2C, 0, 4)
def handle_inc_l(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "L")


@register_instruction(0x24, 0, 4)
def handle_inc_h(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "_h")


@register_instruction(0x34, 0, 12)
def handle_inc_hl_mem(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "(HL)")


def handle_generic_dec(state, register_name):
    old_value = None
    new_value = None

    if register_name == "(HL)":
        old_value = state.memory.read(state.HL)
        new_value = (old_value - 1) & 0xFF
        state.memory.write(state.HL, new_value)
    else:
        old_value = getattr(state, register_name)
        new_value = (old_value - 1) & 0xFF
        setattr(state, register_name, new_value)

    state.zf = 1 if new_value == 0 else 0
    state.nf = 1
    state.hf = 1 if (old_value & 0x0F) == 0 else 0


@register_instruction(0x3D, 0, 4)
def handle_dec_a(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "A")


@register_instruction(0x35, 0, 12)
def handle_dec_hl_mem(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "(HL)")


@register_instruction(0x1A, 0, 8)
def handle_ld_a_de_mem(logger, cpu, instruction):
    cpu._state.A = cpu._state.memory.read(cpu._state.DE)


@register_instruction(0x12, 0, 8)
def handle_ld_mem_de_a(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.DE, cpu._state.A)


@register_instruction(0x1C, 0, 4)
def handle_inc_e(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "E")


@register_instruction(0x30, 1, 12)
def handle_jr_nc_r8(logger, cpu, instruction):
    value = instruction[1]
    if value & 0x80:
        value = value - 0x100

    if not cpu._state.cf:
        cpu._state.pc = (cpu._state.pc + value) & 0xFFFF
    else:
        return 8


@register_instruction(0x20, 1, 12)
def handle_jr_nz(logger, cpu, instruction):
    value = instruction[1]
    if value & 0x80:
        value = value - 0x100

    if not cpu._state.zf:
        cpu._state.pc += value
    else:
        return 8


@register_instruction(0x38, 1, 12)
def handle_jr_c(logger, cpu, instruction):
    value = instruction[1]
    if value & 0x80:
        value = value - 0x100

    if cpu._state.cf:
        cpu._state.pc += value
    else:
        return 8


@register_instruction(0x28, 1, 12)
def handle_jr_z(logger, cpu, instruction):
    value = instruction[1]
    if value & 0x80:
        value = value - 0x100

    if cpu._state.zf:
        cpu._state.pc += value
    else:
        return 8


@register_instruction(0x32, 0, 8)
def handle_ld_hdl_a(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.A)
    cpu._state.HL = (cpu._state.HL - 1) & 0xFFFF


def handle_generic_sub_a(state, register_name):
    value = None
    if register_name == "(HL)":
        value = state.memory.read(state.HL)
    else:
        value = getattr(state, register_name)

    result = state.A - value
    state.zf = 1 if (result & 0xFF) == 0 else 0
    state.nf = 1
    state.hf = 1 if (state.A & 0xF) < (value & 0xF) else 0
    state.cf = 1 if state.A < value else 0
    state.A = result & 0xFF


@register_instruction(0x90, 0, 4)
def handle_sub_a_b(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "B")


@register_instruction(0x91, 0, 4)
def handle_sub_a_c(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "C")


@register_instruction(0x92, 0, 4)
def handle_sub_a_d(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "D")


@register_instruction(0x93, 0, 4)
def handle_sub_a_e(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "E")


@register_instruction(0x94, 0, 4)
def handle_sub_a_h(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "H")


@register_instruction(0x95, 0, 4)
def handle_sub_a_l(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "L")


@register_instruction(0x96, 0, 8)
def handle_sub_a_hl_mem(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "(HL)")


@register_instruction(0x97, 0, 4)
def handle_sub_a_a(logger, cpu, instruction):
    handle_generic_sub_a(cpu._state, "A")


@register_instruction(0xD6, 1, 8)
def handle_sub_a_d8(logger, cpu, instruction):
    value = instruction[1]
    result = cpu._state.A - value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (cpu._state.A & 0xF) < (value & 0xF) else 0
    cpu._state.cf = 1 if result < 0 else 0
    cpu._state.A = result & 0xFF


@register_instruction(0xB7, 0, 4)
def handle_or_a(logger, cpu, instruction):
    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0xB6, 0, 8)
def handle_or_hl_mem(logger, cpu, instruction):
    value = cpu._state.memory.read(cpu._state.HL)
    cpu._state.A = cpu._state.A | value

    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0x35, 0, 12)
def handle_dec_hl_mem(logger, cpu, instruction):
    address = cpu._state.HL
    value = cpu._state.memory.read(address)
    old_value = value

    value = (value - 1) & 0xFF
    cpu._state.memory.write(address, value)

    cpu._state.zf = 1 if value == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (old_value & 0x0F) == 0 else 0


@register_instruction(0xD2, 2, 16)
def handle_jp_nc_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.cf == 0:
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xDA, 2, 16)
def handle_jp_c_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.cf == 1:
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xCC, 2, 24)
def handle_call_z_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.zf == 1:
        push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xF2, 0, 8)
def handle_ld_a_c_mem(logger, cpu, instruction):
    value = cpu._state.memory.read(0xFF00 + cpu._state.C)
    cpu._state.A = value


@register_instruction(0xE2, 0, 8)
def handle_ld_c_mem_a(logger, cpu, instruction):
    cpu._state.memory.write(0xFF00 + cpu._state.C, cpu._state.A)


@register_instruction(0x2F, 0, 4)
def handle_cpl_a(logger, cpu, instruction):
    cpu._state.A ^= 0xFF
    cpu._state.nf = 1
    cpu._state.hf = 1


@register_instruction(0x37, 0, 4)
def handle_scf(logger, cpu, instruction):
    cpu._state.cf = 1
    cpu._state.nf = 0
    cpu._state.hf = 0


@register_instruction(0x3F, 0, 4)
def handle_ccf(logger, cpu, instruction):
    cpu._state.cf ^= 1
    cpu._state.nf = 0
    cpu._state.hf = 0


@register_instruction(0xC2, 2, 16)
def handle_jp_nz_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.zf == 0:
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xCA, 2, 16)
def handle_jp_z_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.zf == 1:
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xC6, 1, 8)
def handle_add_a_a8(logger, cpu, instruction):
    value = instruction[1]
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x80, 0, 8)
def handle_add_a_b(logger, cpu, instruction):
    value = cpu._state.B
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x81, 0, 8)
def handle_add_a_c(logger, cpu, instruction):
    value = cpu._state.C
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x82, 0, 8)
def handle_add_a_d(logger, cpu, instruction):
    value = cpu._state.D
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x83, 0, 8)
def handle_add_a_e(logger, cpu, instruction):
    value = cpu._state.E
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x84, 0, 8)
def handle_add_a_h(logger, cpu, instruction):
    value = cpu._state.H
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x86, 0, 8)
def handle_add_a_hl_mem(logger, cpu, instruction):
    value = cpu._state.memory.read(cpu._state.HL)
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x85, 0, 8)
def handle_add_a_l(logger, cpu, instruction):
    value = cpu._state.L
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x87, 0, 8)
def handle_add_a_a(logger, cpu, instruction):
    value = cpu._state.A
    result = cpu._state.A + value
    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


@register_instruction(0x22, 0, 8)
def handle_ld_hl_mem_a(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.A)
    cpu._state.HL += 1


@register_instruction(0x13, 0, 8)
def handle_inc_de(logger, cpu, instruction):
    cpu._state.DE = (cpu._state.DE + 1) & 0xFFFF


@register_instruction(0x26, 1, 8)
def handle_ld_h_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    cpu._state.H = value


@register_instruction(0xAE, 0, 8)
def handle_a_xor_hl_mem_address(logger, cpu, instruction):
    value = cpu._state.memory.read(cpu._state.HL)
    cpu._state.A ^= value
    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


def handle_generic_xor_a(state, register_name):
    value = getattr(state, register_name)
    state.A = state.A ^ value
    state.zf = 1 if state.A == 0 else 0
    state.nf = 0
    state.hf = 0
    state.cf = 0


@register_instruction(0x17, 0, 4)
def handle_rla(logger, cpu, instruction):
    a = cpu._state.A
    carry_in = cpu._state.cf
    carry_out = (a >> 7) & 0x01
    result = ((a << 1) & 0xFF) | carry_in

    cpu._state.A = result
    cpu._state.cf = carry_out
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.zf = 0  # CHATGPU SUGGESTION


@register_instruction(0xAD, 0, 4)
def handle_a_xor_l(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "L")


@register_instruction(0xA8, 0, 4)
def handle_a_xor_b(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "B")


@register_instruction(0xA9, 0, 4)
def handle_a_xor_c(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "C")


@register_instruction(0xAF, 0, 4)
def handle_xor_a(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "A")


@register_instruction(0xAA, 0, 4)
def handle_xor_d(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "D")


@register_instruction(0xAB, 0, 4)
def handle_xor_e(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "E")


@register_instruction(0xAC, 0, 4)
def handle_xor_h(logger, cpu, instruction):
    handle_generic_xor_a(cpu._state, "H")


@register_instruction(0xEE, 1, 8)
def handle_a_xor_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    cpu._state.A ^= value
    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0x14, 0, 4)
def handle_inc_d(logger, cpu, instruction):
    handle_generic_inc(cpu._state, "D")


@register_instruction(0x15, 0, 4)
def handle_dec_d(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "D")


@register_instruction(0x25, 0, 4)
def handle_dec_h(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "H")


@register_instruction(0x6F, 0, 4)
def handle_ld_l_a(logger, cpu, instruction):
    cpu._state.L = cpu._state.A


@register_instruction(0x67, 0, 4)
def handle_ld_h_a(logger, cpu, instruction):
    cpu._state.H = cpu._state.A


@register_instruction(0x62, 0, 4)
def handle_ld_h_d(logger, cpu, instruction):
    cpu._state.H = cpu._state.D


@register_instruction(0x6B, 0, 4)
def handle_ld_l_e(logger, cpu, instruction):
    cpu._state.L = cpu._state.E


@register_instruction(0x68, 0, 4)
def handle_ld_l_b(logger, cpu, instruction):
    cpu._state.L = cpu._state.B


@register_instruction(0x09, 0, 8)
def handle_add_hl_bc(logger, cpu, instruction):
    hl = cpu._state.HL
    bc = cpu._state.BC
    result = hl + bc

    cpu._state.nf = 0
    cpu._state.hf = 1 if ((hl & 0x0FFF) + (bc & 0x0FFF)) > 0x0FFF else 0
    cpu._state.cf = 1 if result > 0xFFFF else 0

    cpu._state.HL = result & 0xFFFF  # mask to 16-bit


@register_instruction(0x19, 0, 8)
def handle_add_hl_de(logger, cpu, instruction):
    hl = cpu._state.HL
    de = cpu._state.DE
    result = hl + de

    cpu._state.nf = 0
    cpu._state.hf = 1 if ((hl & 0x0FFF) + (de & 0x0FFF)) > 0x0FFF else 0
    cpu._state.cf = 1 if result > 0xFFFF else 0

    cpu._state.HL = result & 0xFFFF  # mask to 16-bit


@register_instruction(0x29, 0, 8)
def handle_add_hl_hl(logger, cpu, instruction):
    hl = cpu._state.HL
    result = hl + hl

    cpu._state.nf = 0
    cpu._state.hf = 1 if ((hl & 0x0FFF) + (hl & 0x0FFF)) > 0x0FFF else 0
    cpu._state.cf = 1 if result > 0xFFFF else 0

    cpu._state.HL = result & 0xFFFF  # mask to 16-bit


@register_instruction(0x40, 0, 4)
def handle_ld_b_b(logger, cpu, instruction):
    cpu._state.B = cpu._state.B


@register_instruction(0x41, 0, 4)
def handle_ld_b_c(logger, cpu, instruction):
    cpu._state.B = cpu._state.C


@register_instruction(0x42, 0, 4)
def handle_ld_b_d(logger, cpu, instruction):
    cpu._state.B = cpu._state.D


@register_instruction(0x43, 0, 4)
def handle_ld_b_e(logger, cpu, instruction):
    cpu._state.B = cpu._state.E


@register_instruction(0x44, 0, 4)
def handle_ld_b_h(logger, cpu, instruction):
    cpu._state.B = cpu._state.H


@register_instruction(0x45, 0, 4)
def handle_ld_b_l(logger, cpu, instruction):
    cpu._state.B = cpu._state.L


@register_instruction(0x5D, 0, 4)
def handle_ld_e_l(logger, cpu, instruction):
    cpu._state.E = cpu._state.L


@register_instruction(0x5F, 0, 4)
def handle_ld_e_a(logger, cpu, instruction):
    cpu._state.E = cpu._state.A


@register_instruction(0x5E, 0, 8)
def handle_ld_e_hl_mem_address(logger, cpu, instruction):
    cpu._state.E = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x2D, 0, 4)
def handle_dec_l(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "L")


@register_instruction(0x1D, 0, 4)
def handle_dec_e(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "E")


@register_instruction(0x0B, 0, 8)
def handle_dec_bc(logger, cpu, instruction):
    cpu._state.BC = (cpu._state.BC - 1) & 0xFFFF


@register_instruction(0x1B, 0, 8)
def handle_dec_de(logger, cpu, instruction):
    cpu._state.DE = (cpu._state.DE - 1) & 0xFFFF


@register_instruction(0x2B, 0, 8)
def handle_dec_hl(logger, cpu, instruction):
    cpu._state.HL = (cpu._state.HL - 1) & 0xFFFF


@register_instruction(0x3B, 0, 8)
def handle_dec_sp(logger, cpu, instruction):
    cpu._state.SP = (cpu._state.SP - 1) & 0xFFFF


@register_instruction(0x0D, 0, 4)
def handle_dec_c(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "C")


@register_instruction(0xE9, 0, 4)
def handle_jp_hl(logger, cpu, instruction):
    cpu._state.pc = cpu._state.HL


@register_instruction(0x05, 0, 4)
def handle_dec_b(logger, cpu, instruction):
    handle_generic_dec(cpu._state, "B")


@register_instruction(0x7E, 0, 8)
def handle_ld_a_hl_mem_address(logger, cpu, instruction):
    cpu._state.A = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x77, 0, 8)
def handle_ld_mem_hl_a(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.A)


@register_instruction(0x73, 0, 8)
def handle_ld_mem_hl_e(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.E)


@register_instruction(0x70, 0, 8)
def handle_ld_mem_hl_b(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.B)


@register_instruction(0x71, 0, 8)
def handle_ld_mem_hl_c(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.C)


@register_instruction(0x72, 0, 8)
def handle_ld_mem_hl_d(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.HL, cpu._state.D)


@register_instruction(0x78, 0, 4)
def handle_ld_a_b(logger, cpu, instruction):
    cpu._state.A = cpu._state.B


@register_instruction(0x0A, 0, 8)
def handle_ld_a_bc_mem(logger, cpu, instruction):
    value = cpu._state.memory.read(cpu._state.BC)
    cpu._state.A = value


@register_instruction(0x02, 0, 8)
def handle_ld_bc_mem_with_a(logger, cpu, instruction):
    cpu._state.memory.write(cpu._state.BC, cpu._state.A)


@register_instruction(0x79, 0, 4)
def handle_ld_a_c(logger, cpu, instruction):
    cpu._state.A = cpu._state.C


@register_instruction(0xF5, 0, 16)
def handle_push_af(logger, cpu, instruction):
    flags = cpu._state.get_flags_byte()

    push(cpu._state, cpu._state.A, flags)
    # print(f'Pushing a={cpu._state.A} to memory! Current address: {cpu._state.SP:04X}')


@register_instruction(0xF1, 0, 12)
def handle_pop_af(logger, cpu, instruction):
    flags, value = pop(cpu._state)
    cpu._state.set_flags_from_byte(flags)
    cpu._state.A = value


@register_instruction(0xE0, 1, 12)
def handle_ldh_a8_a(logger, cpu, instruction):
    address_offset = instruction[1]
    address = 0xFF00 + address_offset
    cpu._state.memory.write(address, cpu._state.A)


@register_instruction(0xF0, 1, 12)
def handle_ldh_a_a8(logger, cpu, instruction):
    address_offset = instruction[1]
    address = 0xFF00 + address_offset
    cpu._state.A = cpu._state.memory.read(address)


@register_instruction(0xFA, 2, 16)
def handle_ld_a_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)
    cpu._state.A = cpu._state.memory.read(address)


@register_instruction(0xFB, 0, 4)
def handle_ei(logger, cpu, instruction):
    # cpu._state.enable_interrupts_after_next_instruction = True
    cpu._state._delay_enable_ime = True
    # logger.info('Setting delay_enable_ime to true!')


@register_instruction(0xF3, 0, 4)
def handle_di(logger, cpu, instruction):
    cpu._state.ime = 0


@register_instruction(0x31, 2, 12)
def handle_ld_sp_d16(logger, cpu, instruction):
    value = instruction[1] | (instruction[2] << 8)
    cpu._state.SP = value & 0xFFFF


@register_instruction(0x01, 2, 12)
def handle_ld_bc_d16(logger, cpu, instruction):
    value = instruction[1] | (instruction[2] << 8)
    cpu._state.BC = value & 0xFFFF


@register_instruction(0x33, 0, 8)
def inc_sp(logger, cpu, instruction):
    cpu._state.SP = (cpu._state.SP + 1) & 0xFFFF


@register_instruction(0x03, 0, 8)
def inc_bc(logger, cpu, instruction):
    cpu._state.BC = (cpu._state.BC + 1) & 0xFFFF


def handle_generic_or(state, register_name):
    or_value = getattr(state, register_name)

    state.A |= or_value
    state.zf = 1 if state.A == 0 else 0
    state.nf = 0
    state.hf = 0
    state.cf = 0


@register_instruction(0xDE, 1, 8)
def handle_sbc_a_with_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    carry = cpu._state.cf

    result = cpu._state.A - value - carry

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) - (value & 0xF) - carry) < 0 else 0
    cpu._state.cf = 1 if result < 0 else 0

    cpu._state.A = result & 0xFF


@register_instruction(0xF6, 1, 8)
def handle_or_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF

    cpu._state.A |= value
    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0xB0, 0, 4)
def handle_or_b(logger, cpu, instruction):
    handle_generic_or(cpu._state, "B")


@register_instruction(0xB2, 0, 4)
def handle_or_d(logger, cpu, instruction):
    handle_generic_or(cpu._state, "D")


@register_instruction(0xB3, 0, 4)
def handle_or_e(logger, cpu, instruction):
    handle_generic_or(cpu._state, "E")


@register_instruction(0xB4, 0, 4)
def handle_or_h(logger, cpu, instruction):
    handle_generic_or(cpu._state, "H")


@register_instruction(0xB5, 0, 4)
def handle_or_l(logger, cpu, instruction):
    handle_generic_or(cpu._state, "L")


@register_instruction(0xE8, 1, 16)
def handle_add_sp_r8(logger, cpu, instruction):
    sp = cpu._state.SP
    offset = instruction[1]

    # Sign extend
    if offset & 0x80:
        offset -= 0x100

    result = (sp + offset) & 0xFFFF

    cpu._state.zf = 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((sp & 0xF) + (offset & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if ((sp & 0xFF) + (offset & 0xFF)) > 0xFF else 0

    cpu._state.SP = result


@register_instruction(0x39, 0, 8)
def handle_add_hl_sp(logger, cpu, instruction):
    hl = cpu._state.HL
    sp = cpu._state.SP
    result = hl + sp

    cpu._state.nf = 0
    cpu._state.hf = 1 if ((hl & 0x0FFF) + (sp & 0x0FFF)) > 0x0FFF else 0
    cpu._state.cf = 1 if result > 0xFFFF else 0

    cpu._state.HL = result & 0xFFFF


@register_instruction(0xB1, 0, 4)
def handle_or_c(logger, cpu, instruction):
    cpu._state.A |= cpu._state.C
    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0x08, 2, 20)
def handle_ld_a16_sp(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)
    cpu._state.memory.write(address, cpu._state.SP & 0xFF)
    cpu._state.memory.write(address + 1, (cpu._state.SP >> 8))


@register_instruction(0xEA, 2, 16)
def handle_ld_a16_a(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)
    cpu._state.memory.write(address, cpu._state.A)


def handle_generic_and_(state, destination_register_name, value_register_name):
    value = getattr(state, value_register_name)
    new_value = getattr(state, destination_register_name) & value
    setattr(state, destination_register_name, new_value)

    state.zf = 1 if new_value == 0 else 0
    state.nf = 0
    state.hf = 1
    state.cf = 0


def handle_generic_and_a(state, register_name):
    value = getattr(state, register_name)
    state.A = state.A & value

    state.zf = 1 if state.A == 0 else 0
    state.nf = 0
    state.hf = 1
    state.cf = 0


@register_instruction(0xE6, 1, 8)
def handle_a_and_a8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    cpu._state.A = cpu._state.A & value

    cpu._state.zf = 1 if cpu._state.A == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1
    cpu._state.cf = 0


@register_instruction(0x36, 1, 8)
def handle_ld_hl_mem_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    cpu._state.memory.write(cpu._state.HL, value)


@register_instruction(0x16, 1, 8)
def handle_ld_d_d8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.D = value & 0xFF


@register_instruction(0x1E, 1, 8)
def handle_ld_e_d8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.E = value & 0xFF


@register_instruction(0x2E, 1, 8)
def handle_ld_l_d8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.L = value & 0xFF


@register_instruction(0x3E, 1, 8)
def handle_ld_a_d8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.A = value & 0xFF


@register_instruction(0x06, 1, 8)
def handle_ld_b_d8(logger, cpu, instruction):
    value = instruction[1]
    cpu._state.B = value & 0xFF


@register_instruction(0xCE, 1, 8)
def handle_adc_a_d8(logger, cpu, instruction):
    value = instruction[1]
    carry = cpu._state.cf
    result = cpu._state.A + value + carry

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.A & 0xF) + (value & 0xF) + carry) > 0xF else 0
    cpu._state.cf = 1 if result > 0xFF else 0
    cpu._state.A = result & 0xFF


def handle_generic_adc_a(state, register_name):
    value = None
    if register_name == "(HL)":
        value = state.memory.read(state.HL)
    else:
        value = getattr(state, register_name)
    carry = state.cf
    result = state.A + value + carry

    state.zf = 1 if (result & 0xFF) == 0 else 0
    state.nf = 0
    state.hf = 1 if ((state.A & 0xF) + (value & 0xF) + carry) > 0xF else 0
    state.cf = 1 if result > 0xFF else 0
    state.A = result & 0xFF


@register_instruction(0x88, 0, 8)
def handle_adc_a_b(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "B")


@register_instruction(0x89, 0, 8)
def handle_adc_a_c(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "C")


@register_instruction(0x8A, 0, 8)
def handle_adc_a_d(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "D")


@register_instruction(0x8B, 0, 8)
def handle_adc_a_e(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "E")


@register_instruction(0x8C, 0, 8)
def handle_adc_a_h(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "H")


@register_instruction(0x8D, 0, 8)
def handle_adc_a_l(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "L")


@register_instruction(0x8E, 0, 8)
def handle_adc_a_hl_mem(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "(HL)")


@register_instruction(0x8F, 0, 8)
def handle_adc_a_a(logger, cpu, instruction):
    handle_generic_adc_a(cpu._state, "A")


@register_instruction(0xD0, 0, 20)
def handle_ret_nc(logger, cpu, instruction):
    if cpu._state.cf != 0:
        return 8

    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address


@register_instruction(0xD8, 0, 20)
def handle_ret_cf(logger, cpu, instruction):
    if cpu._state.cf == 0:
        return 8

    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address


@register_instruction(0xD9, 0, 16)
def handle_reti(logger, cpu, instruction):
    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address
    cpu._state.ime = 1


@register_instruction(0xC8, 0, 20)
def handle_ret_z(logger, cpu, instruction):
    if cpu._state.zf == 0:
        return 8

    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address


@register_instruction(0xC0, 0, 20)
def handle_ret_nz(logger, cpu, instruction):
    if cpu._state.zf != 0:
        return 8

    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address


@register_instruction(0xC4, 2, 24)
def handle_call_nz_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.zf == 0:
        push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xD4, 2, 24)
def handle_call_nc_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.cf == 0:
        push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xDC, 2, 24)
def handle_call_c_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    if cpu._state.cf == 1:
        push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
        cpu._state.pc = address
    else:
        return 12


@register_instruction(0xC7, 0, 16)
def handle_rst_00h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x00


@register_instruction(0xCF, 0, 16)
def handle_rst_08h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x08


@register_instruction(0xD7, 0, 16)
def handle_rst_10h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x10


@register_instruction(0xDF, 0, 16)
def handle_rst_18h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x18


@register_instruction(0xE7, 0, 16)
def handle_rst_20h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x20


@register_instruction(0xEF, 0, 16)
def handle_rst_28h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x28


@register_instruction(0xF7, 0, 16)
def handle_rst_30h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x30


@register_instruction(0xFF, 0, 16)
def handle_rst_38h(logger, cpu, instruction):
    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)
    cpu._state.pc = 0x38


@register_instruction(0xCD, 2, 24)
def handle_call_a16(logger, cpu, instruction):
    address = instruction[1] | (instruction[2] << 8)

    push(cpu._state, cpu._state.pc >> 8, cpu._state.pc)

    cpu._state.pc = address


@register_instruction(0x7B, 0, 4)
def handle_ld_a_e(logger, cpu, instruction):
    cpu._state.A = cpu._state.E


@register_instruction(0x7D, 0, 4)
def handle_ld_a_l(logger, cpu, instruction):
    cpu._state.A = cpu._state.L


@register_instruction(0x57, 0, 4)
def handle_ld_d_a(logger, cpu, instruction):
    cpu._state.D = cpu._state.A


@register_instruction(0x48, 0, 4)
def handle_ld_c_b(logger, cpu, instruction):
    cpu._state.C = cpu._state.B


@register_instruction(0x49, 0, 4)
def handle_ld_c_c(logger, cpu, instruction):
    cpu._state.C = cpu._state.C


@register_instruction(0x4A, 0, 4)
def handle_ld_c_d(logger, cpu, instruction):
    cpu._state.C = cpu._state.D


@register_instruction(0x4B, 0, 4)
def handle_ld_c_e(logger, cpu, instruction):
    cpu._state.C = cpu._state.E


@register_instruction(0x4C, 0, 4)
def handle_ld_c_h(logger, cpu, instruction):
    cpu._state.C = cpu._state.H


@register_instruction(0x4D, 0, 4)
def handle_ld_c_l(logger, cpu, instruction):
    cpu._state.C = cpu._state.L


@register_instruction(0x50, 0, 4)
def handle_ld_d_b(logger, cpu, instruction):
    cpu._state.D = cpu._state.B


@register_instruction(0x51, 0, 4)
def handle_ld_d_c(logger, cpu, instruction):
    cpu._state.D = cpu._state.C


@register_instruction(0x52, 0, 4)
def handle_ld_d_d(logger, cpu, instruction):
    cpu._state.D = cpu._state.D


@register_instruction(0x53, 0, 4)
def handle_ld_d_e(logger, cpu, instruction):
    cpu._state.D = cpu._state.E


@register_instruction(0x54, 0, 4)
def handle_ld_d_h(logger, cpu, instruction):
    cpu._state.D = cpu._state.H


@register_instruction(0x55, 0, 4)
def handle_ld_d_l(logger, cpu, instruction):
    cpu._state.D = cpu._state.L


@register_instruction(0x58, 0, 4)
def handle_ld_e_b(logger, cpu, instruction):
    cpu._state.E = cpu._state.B


@register_instruction(0x59, 0, 4)
def handle_ld_e_c(logger, cpu, instruction):
    cpu._state.E = cpu._state.C


@register_instruction(0x5A, 0, 4)
def handle_ld_e_d(logger, cpu, instruction):
    cpu._state.E = cpu._state.D


@register_instruction(0x5B, 0, 4)
def handle_ld_e_e(logger, cpu, instruction):
    cpu._state.E = cpu._state.E


@register_instruction(0x5C, 0, 4)
def handle_ld_e_h(logger, cpu, instruction):
    cpu._state.E = cpu._state.H


@register_instruction(0x7F, 0, 4)
def handle_ld_a_a(logger, cpu, instruction):
    cpu._state.A = cpu._state.A


@register_instruction(0x60, 0, 4)
def handle_ld_h_b(logger, cpu, instruction):
    cpu._state.H = cpu._state.B


@register_instruction(0x61, 0, 4)
def handle_ld_h_c(logger, cpu, instruction):
    cpu._state.H = cpu._state.C


@register_instruction(0x63, 0, 4)
def handle_ld_h_e(logger, cpu, instruction):
    cpu._state.H = cpu._state.E


@register_instruction(0x64, 0, 4)
def handle_ld_h_h(logger, cpu, instruction):
    cpu._state.H = cpu._state.H


@register_instruction(0x65, 0, 4)
def handle_ld_h_l(logger, cpu, instruction):
    cpu._state.H = cpu._state.L


@register_instruction(0x69, 0, 4)
def handle_ld_l_c(logger, cpu, instruction):
    cpu._state.L = cpu._state.C


@register_instruction(0x6A, 0, 4)
def handle_ld_l_d(logger, cpu, instruction):
    cpu._state.L = cpu._state.D


@register_instruction(0x6C, 0, 4)
def handle_ld_l_h(logger, cpu, instruction):
    cpu._state.L = cpu._state.H


@register_instruction(0x6D, 0, 4)
def handle_ld_l_l(logger, cpu, instruction):
    cpu._state.L = cpu._state.L


@register_instruction(0x7A, 0, 4)
def handle_ld_a_d(logger, cpu, instruction):
    cpu._state.A = cpu._state.D


@register_instruction(0x7C, 0, 4)
def handle_ld_a_h(logger, cpu, instruction):
    cpu._state.A = cpu._state.H


@register_instruction(0x18, 1, 12)
def handle_jr_r8(logger, cpu, instruction):
    value = instruction[1]
    if value & 0x80:
        value = value - 0x100

    cpu._state.pc += value

    (f"JR R8: ZF={cpu._state.zf}, value={value}")


@register_instruction(0xC9, 0, 16)
def handle_ret(logger, cpu, instruction):
    address = 0

    low = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    high = cpu._state.memory.read(cpu._state.SP)
    cpu._state.SP += 1

    address = (high << 8) | low
    cpu._state.pc = address


@register_instruction(0xC5, 0, 16)
def handle_push_bc(logger, cpu, instruction):
    push(cpu._state, cpu._state.BC >> 8, cpu._state.BC)


@register_instruction(0xE5, 0, 16)
def handle_push_hl(logger, cpu, instruction):
    push(cpu._state, cpu._state.HL >> 8, cpu._state.HL)


@register_instruction(0xD5, 0, 16)
def handle_push_de(logger, cpu, instruction):
    push(cpu._state, cpu._state.DE >> 8, cpu._state.DE)


@register_instruction(0x76, 0, 4)
def handle_hlt(logger, cpu, instruction):
    cpu._state._halted = True


@register_instruction(0x56, 0, 8)
def handle_ld_d_hl_mem_address(logger, cpu, instruction):
    cpu._state.D = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0x66, 0, 8)
def handle_ld_h_hl_mem_address(logger, cpu, instruction):
    cpu._state.H = cpu._state.memory.read(cpu._state.HL)


@register_instruction(0xF9, 0, 8)
def handle_ld_sp_hl(logger, cpu, instruction):
    cpu._state.SP = cpu._state.HL


@register_instruction(0xE1, 0, 12)
def handle_pop_hl(logger, cpu, instruction):
    low, high = pop(cpu._state)

    value = (high << 8) | low
    cpu._state.HL = value


@register_instruction(0xC1, 0, 12)
def handle_pop_bc(logger, cpu, instruction):
    low, high = pop(cpu._state)

    value = (high << 8) | low
    cpu._state.BC = value


@register_instruction(0xD1, 0, 12)
def handle_pop_de(logger, cpu, instruction):
    low, high = pop(cpu._state)

    value = (high << 8) | low
    cpu._state.DE = value


@register_instruction(0xFE, 1, 8)
def handle_cp_d8(logger, cpu, instruction):
    value = instruction[1] & 0xFF
    cpu._state.zf = 1 if cpu._state.A == value else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (cpu._state.A & 0xF) < (value & 0xF) else 0
    cpu._state.cf = 1 if cpu._state.A < value else 0


@register_instruction(0xB8, 0, 4)
def handle_cp_b(logger, cpu, instruction):
    a = cpu._state.A
    b = cpu._state.B
    result = a - b

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (b & 0xF) else 0
    cpu._state.cf = 1 if a < b else 0


@register_instruction(0xBC, 0, 4)
def handle_cp_h(logger, cpu, instruction):
    a = cpu._state.A
    h = cpu._state.H
    result = a - h

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (h & 0xF) else 0
    cpu._state.cf = 1 if a < h else 0


@register_instruction(0xBD, 0, 4)
def handle_cp_l(logger, cpu, instruction):
    a = cpu._state.A
    l = cpu._state.L
    result = a - l

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (l & 0xF) else 0
    cpu._state.cf = 1 if a < l else 0


@register_instruction(0xBE, 0, 8)
def handle_cp_hl(logger, cpu, instruction):
    a = cpu._state.A
    l = cpu._state.memory.read(cpu._state.HL)
    result = a - l

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (l & 0xF) else 0
    cpu._state.cf = 1 if a < l else 0


@register_instruction(0xBF, 0, 8)
def handle_cp_a(logger, cpu, instruction):
    a = cpu._state.A
    result = a - a

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 0
    cpu._state.cf = 0


@register_instruction(0xB9, 0, 8)
def handle_cp_c(logger, cpu, instruction):
    a = cpu._state.A
    c = cpu._state.C
    result = a - c

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (c & 0xF) else 0
    cpu._state.cf = 1 if a < c else 0


@register_instruction(0xBA, 0, 8)
def handle_cp_d(logger, cpu, instruction):
    a = cpu._state.A
    d = cpu._state.D
    result = a - d

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (d & 0xF) else 0
    cpu._state.cf = 1 if a < d else 0


@register_instruction(0xBB, 0, 8)
def handle_cp_e(logger, cpu, instruction):
    a = cpu._state.A
    e = cpu._state.E
    result = a - e

    cpu._state.zf = 1 if (result & 0xFF) == 0 else 0
    cpu._state.nf = 1
    cpu._state.hf = 1 if (a & 0xF) < (e & 0xF) else 0
    cpu._state.cf = 1 if a < e else 0


@register_instruction(0xF8, 1, 8)
def handle_ld_hl_with_sp_plus_r8(logger, cpu, instruction):
    offset = instruction[1]
    if offset & 0x80:
        offset = offset - 0x100

    result = (cpu._state.SP + offset) & 0xFFFF
    cpu._state.HL = result

    cpu._state.zf = 0
    cpu._state.nf = 0
    cpu._state.hf = 1 if ((cpu._state.SP & 0xF) + (offset & 0xF)) > 0xF else 0
    cpu._state.cf = 1 if ((cpu._state.SP & 0xFF) + (offset & 0xFF)) > 0xFF else 0


def handle_cb_generic_swap(state, register_name):
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        result = ((value & 0x0F) << 4) | ((value & 0xF0) >> 4)
        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        result = ((value & 0x0F) << 4) | ((value & 0xF0) >> 4)
        setattr(state, register_name, result)

    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0
    state.cf = 0


@register_cb_instruction(0x30, 0, 8)
def handle_cb_swap_b(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "B")


@register_cb_instruction(0x31, 0, 8)
def handle_cb_swap_c(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "C")


@register_cb_instruction(0x32, 0, 8)
def handle_cb_swap_d(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "D")


@register_cb_instruction(0x33, 0, 8)
def handle_cb_swap_e(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "E")


@register_cb_instruction(0x34, 0, 8)
def handle_cb_swap_h(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "H")


@register_cb_instruction(0x35, 0, 8)
def handle_cb_swap_l(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "L")


@register_cb_instruction(0x36, 0, 16)
def handle_cb_swap_hl_mem(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "(HL)")


@register_cb_instruction(0x37, 0, 8)
def handle_cb_swap_a(logger, cpu, instruction):
    handle_cb_generic_swap(cpu._state, "A")


def handle_generic_rrc(state, register_name):
    carry_out = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        carry_out = value & 0x01
        result = ((carry_out << 7) | (value >> 1)) & 0xFF
        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        carry_out = value & 0x01
        result = ((carry_out << 7) | (value >> 1)) & 0xFF

        setattr(state, register_name, result)

    state.cf = carry_out
    state.zf = 1 if result == 0 else 0  # för CB-prefixerade RRC
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x08, 0, 8)
def handle_rrc_b(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "B")


@register_cb_instruction(0x09, 0, 8)
def handle_rrc_c(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "C")


@register_cb_instruction(0x0A, 0, 8)
def handle_rrc_d(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "D")


@register_cb_instruction(0x0B, 0, 8)
def handle_cb_rrc_e(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "E")


@register_cb_instruction(0x0C, 0, 8)
def handle_cb_rrc_h(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "H")


@register_cb_instruction(0x0D, 0, 8)
def handle_cb_rrc_l(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "L")


@register_cb_instruction(0x0E, 0, 16)
def handle_cb_rrc_hl_mem(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "(HL)")


@register_cb_instruction(0x0F, 0, 8)
def handle_cb_rrc_a(logger, cpu, instruction):
    handle_generic_rrc(cpu._state, "A")


@register_instruction(0x0F, 0, 4)
def handle_rrca(logger, cpu, instruction):
    value = cpu._state.A
    carry_out = value & 0x01
    result = ((carry_out << 7) | (value >> 1)) & 0xFF

    cpu._state.A = result
    cpu._state.cf = carry_out
    cpu._state.nf = 0
    cpu._state.hf = 0
    cpu._state.zf = 0  # CHATGPU SUGGESTION
    # OBS! cpu._state.zf påverkas INTE!


def handle_cb_generic_rl(state, register_name):
    new_carry = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        old_carry = state.cf
        new_carry = (value >> 7) & 0x01
        result = ((value << 1) & 0xFF) | old_carry

        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        old_carry = state.cf
        new_carry = (value >> 7) & 0x01
        result = ((value << 1) & 0xFF) | old_carry

        setattr(state, register_name, result)

    state.cf = new_carry
    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x10, 0, 8)
def handle_cb_rl_b(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "B")


@register_cb_instruction(0x11, 0, 8)
def handle_cb_rl_c(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "C")


@register_cb_instruction(0x12, 0, 8)
def handle_cb_rl_d(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "D")


@register_cb_instruction(0x13, 0, 8)
def handle_cb_rl_e(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "E")


@register_cb_instruction(0x14, 0, 8)
def handle_cb_rl_h(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "H")


@register_cb_instruction(0x15, 0, 8)
def handle_cb_rl_l(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "L")


@register_cb_instruction(0x16, 0, 16)
def handle_cb_rl_hl_mem(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "(HL)")


@register_cb_instruction(0x17, 0, 8)
def handle_cb_rl_a(logger, cpu, instruction):
    handle_cb_generic_rl(cpu._state, "A")


def handle_cb_generic_rr(state, register_name):
    new_carry = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        old_carry = state.cf
        new_carry = value & 0x01
        result = (value >> 1) | (old_carry << 7)

        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        old_carry = state.cf
        new_carry = value & 0x01
        result = (value >> 1) | (old_carry << 7)

        setattr(state, register_name, result)

    state.cf = new_carry
    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x18, 0, 8)
def handle_cb_rr_b(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "B")


@register_cb_instruction(0x19, 0, 8)
def handle_cb_rr_c(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "C")


@register_cb_instruction(0x1A, 0, 8)
def handle_cb_rr_d(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "D")


@register_cb_instruction(0x1B, 0, 8)
def handle_cb_rr_e(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "E")


@register_cb_instruction(0x1C, 0, 8)
def handle_cb_rr_h(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "H")


@register_cb_instruction(0x1D, 0, 8)
def handle_cb_rr_l(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "L")


@register_cb_instruction(0x1E, 0, 16)
def handle_cb_rr_hl_mem(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "(HL)")


@register_cb_instruction(0x1F, 0, 8)
def handle_cb_rr_a(logger, cpu, instruction):
    handle_cb_generic_rr(cpu._state, "A")


def handle_cb_generic_sla(state, register_name):
    new_carry = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        new_carry = (value >> 7) & 0x01
        result = (value << 1) & 0xFF

        state.memory.write(state.HL, result)

    else:
        value = getattr(state, register_name)
        new_carry = (value >> 7) & 0x01
        result = (value << 1) & 0xFF

        setattr(state, register_name, result)

    state.cf = new_carry
    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x20, 0, 8)
def handle_cb_sla_b(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "B")


@register_cb_instruction(0x21, 0, 8)
def handle_cb_sla_c(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "C")


@register_cb_instruction(0x22, 0, 8)
def handle_cb_sla_d(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "D")


@register_cb_instruction(0x23, 0, 8)
def handle_cb_sla_e(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "E")


@register_cb_instruction(0x24, 0, 8)
def handle_cb_sla_h(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "H")


@register_cb_instruction(0x25, 0, 8)
def handle_cb_sla_l(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "L")


@register_cb_instruction(0x26, 0, 16)
def handle_cb_sla_hl_mem(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "(HL)")


@register_cb_instruction(0x27, 0, 8)
def handle_cb_sla_a(logger, cpu, instruction):
    handle_cb_generic_sla(cpu._state, "A")


def handle_cb_generic_sra(state, register_name):
    new_carry = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        new_carry = value & 0x01
        bit7 = value & 0x80  # bevara sign-bit
        result = (value >> 1) | bit7

        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        new_carry = value & 0x01
        bit7 = value & 0x80  # bevara sign-bit
        result = (value >> 1) | bit7

        setattr(state, register_name, result)

    state.cf = new_carry
    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x28, 0, 8)
def handle_cb_sra_b(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "B")


@register_cb_instruction(0x29, 0, 8)
def handle_cb_sra_c(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "C")


@register_cb_instruction(0x2A, 0, 8)
def handle_cb_sra_d(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "D")


@register_cb_instruction(0x2B, 0, 8)
def handle_cb_sra_e(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "E")


@register_cb_instruction(0x2C, 0, 8)
def handle_cb_sra_h(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "H")


@register_cb_instruction(0x2D, 0, 8)
def handle_cb_sra_l(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "L")


@register_cb_instruction(0x2E, 0, 16)
def handle_cb_sra_hl_mem(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "(HL)")


@register_cb_instruction(0x2F, 0, 8)
def handle_cb_sra_a(logger, cpu, instruction):
    handle_cb_generic_sra(cpu._state, "A")


def handle_cb_generic_srl(state, register_name):
    carry = None
    result = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        carry = value & 0x01
        result = (value >> 1) & 0x7F  # bit 7 blir alltid 0

        state.memory.write(state.HL, result)
    else:
        value = getattr(state, register_name)
        carry = value & 0x01
        result = (value >> 1) & 0x7F  # bit 7 blir alltid 0

        setattr(state, register_name, result)

    state.cf = carry
    state.zf = 1 if result == 0 else 0
    state.nf = 0
    state.hf = 0


@register_cb_instruction(0x38, 0, 8)
def handle_cb_srl_b(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "B")


@register_cb_instruction(0x39, 0, 8)
def handle_cb_srl_c(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "C")


@register_cb_instruction(0x3A, 0, 8)
def handle_cb_srl_d(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "D")


@register_cb_instruction(0x3B, 0, 8)
def handle_cb_srl_e(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "E")


@register_cb_instruction(0x3C, 0, 8)
def handle_cb_srl_h(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "H")


@register_cb_instruction(0x3D, 0, 8)
def handle_cb_srl_l(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "L")


@register_cb_instruction(0x3E, 0, 16)
def handle_cb_srl_hl_mem(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "(HL)")


@register_cb_instruction(0x3F, 0, 8)
def handle_cb_srl_a(logger, cpu, instruction):
    handle_cb_generic_srl(cpu._state, "A")


def handle_cb_generic_bit(state, bit, register_name):
    value = None

    if register_name == "(HL)":
        value = state.memory.read(state.HL)
    else:
        value = getattr(state, register_name)

    state.zf = 0 if (value & (1 << bit)) else 1
    state.nf = 0
    state.hf = 1


@register_cb_instruction(0x40, 0, 8)
def handle_cb_bit_0_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "B")


@register_cb_instruction(0x41, 0, 8)
def handle_cb_bit_0_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "C")


@register_cb_instruction(0x42, 0, 8)
def handle_cb_bit_0_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "D")


@register_cb_instruction(0x43, 0, 8)
def handle_cb_bit_0_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "E")


@register_cb_instruction(0x44, 0, 8)
def handle_cb_bit_0_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "H")


@register_cb_instruction(0x45, 0, 8)
def handle_cb_bit_0_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "L")


@register_cb_instruction(0x46, 0, 16)
def handle_cb_bit_0_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "(HL)")


@register_cb_instruction(0x47, 0, 8)
def handle_cb_bit_0_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 0, "A")


@register_cb_instruction(0x48, 0, 8)
def handle_cb_bit_1_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "B")


@register_cb_instruction(0x49, 0, 8)
def handle_cb_bit_1_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "C")


@register_cb_instruction(0x4A, 0, 8)
def handle_cb_bit_1_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "D")


@register_cb_instruction(0x4B, 0, 8)
def handle_cb_bit_1_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "E")


@register_cb_instruction(0x4C, 0, 8)
def handle_cb_bit_1_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "H")


@register_cb_instruction(0x4D, 0, 8)
def handle_cb_bit_1_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "L")


@register_cb_instruction(0x4E, 0, 16)
def handle_cb_bit_1_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "(HL)")


@register_cb_instruction(0x4F, 0, 8)
def handle_cb_bit_1_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 1, "A")


@register_cb_instruction(0x50, 0, 8)
def handle_cb_bit_2_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "B")


@register_cb_instruction(0x51, 0, 8)
def handle_cb_bit_2_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "C")


@register_cb_instruction(0x52, 0, 8)
def handle_cb_bit_2_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "D")


@register_cb_instruction(0x53, 0, 8)
def handle_cb_bit_2_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "E")


@register_cb_instruction(0x54, 0, 8)
def handle_cb_bit_2_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "H")


@register_cb_instruction(0x55, 0, 8)
def handle_cb_bit_2_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "L")


@register_cb_instruction(0x56, 0, 16)
def handle_cb_bit_2_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "(HL)")


@register_cb_instruction(0x57, 0, 8)
def handle_cb_bit_2_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 2, "A")


@register_cb_instruction(0x58, 0, 8)
def handle_cb_bit_3_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "B")


@register_cb_instruction(0x59, 0, 8)
def handle_cb_bit_3_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "C")


@register_cb_instruction(0x5A, 0, 8)
def handle_cb_bit_3_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "D")


@register_cb_instruction(0x5B, 0, 8)
def handle_cb_bit_3_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "E")


@register_cb_instruction(0x5C, 0, 8)
def handle_cb_bit_3_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "H")


@register_cb_instruction(0x5D, 0, 8)
def handle_cb_bit_3_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "L")


@register_cb_instruction(0x5E, 0, 16)
def handle_cb_bit_3_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "(HL)")


@register_cb_instruction(0x5F, 0, 8)
def handle_cb_bit_3_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 3, "A")


@register_cb_instruction(0x60, 0, 8)
def handle_cb_bit_4_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "B")


@register_cb_instruction(0x61, 0, 8)
def handle_cb_bit_4_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "C")


@register_cb_instruction(0x62, 0, 8)
def handle_cb_bit_4_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "D")


@register_cb_instruction(0x63, 0, 8)
def handle_cb_bit_4_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "E")


@register_cb_instruction(0x64, 0, 8)
def handle_cb_bit_4_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "H")


@register_cb_instruction(0x65, 0, 8)
def handle_cb_bit_4_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "L")


@register_cb_instruction(0x66, 0, 16)
def handle_cb_bit_4_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "(HL)")


@register_cb_instruction(0x67, 0, 8)
def handle_cb_bit_4_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 4, "A")


@register_cb_instruction(0x68, 0, 8)
def handle_cb_bit_5_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "B")


@register_cb_instruction(0x69, 0, 8)
def handle_cb_bit_5_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "C")


@register_cb_instruction(0x6A, 0, 8)
def handle_cb_bit_5_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "D")


@register_cb_instruction(0x6B, 0, 8)
def handle_cb_bit_5_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "E")


@register_cb_instruction(0x6C, 0, 8)
def handle_cb_bit_5_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "H")


@register_cb_instruction(0x6D, 0, 8)
def handle_cb_bit_5_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "L")


@register_cb_instruction(0x6E, 0, 16)
def handle_cb_bit_5_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "(HL)")


@register_cb_instruction(0x6F, 0, 8)
def handle_cb_bit_5_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 5, "A")


@register_cb_instruction(0x70, 0, 8)
def handle_cb_bit_6_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "B")


@register_cb_instruction(0x71, 0, 8)
def handle_cb_bit_6_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "C")


@register_cb_instruction(0x72, 0, 8)
def handle_cb_bit_6_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "D")


@register_cb_instruction(0x73, 0, 8)
def handle_cb_bit_6_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "E")


@register_cb_instruction(0x74, 0, 8)
def handle_cb_bit_6_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "H")


@register_cb_instruction(0x75, 0, 8)
def handle_cb_bit_6_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "L")


@register_cb_instruction(0x76, 0, 16)
def handle_cb_bit_6_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "(HL)")


@register_cb_instruction(0x77, 0, 8)
def handle_cb_bit_6_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 6, "A")


@register_cb_instruction(0x78, 0, 8)
def handle_cb_bit_7_b(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "B")


@register_cb_instruction(0x79, 0, 8)
def handle_cb_bit_7_c(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "C")


@register_cb_instruction(0x7A, 0, 8)
def handle_cb_bit_7_d(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "D")


@register_cb_instruction(0x7B, 0, 8)
def handle_cb_bit_7_e(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "E")


@register_cb_instruction(0x7C, 0, 8)
def handle_cb_bit_7_h(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "H")


@register_cb_instruction(0x7D, 0, 8)
def handle_cb_bit_7_l(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "L")


@register_cb_instruction(0x7E, 0, 16)
def handle_cb_bit_7_hl(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "(HL)")


@register_cb_instruction(0x7F, 0, 8)
def handle_cb_bit_7_a(logger, cpu, instruction):
    handle_cb_generic_bit(cpu._state, 7, "A")


def handle_cb_generic_res(state, bit, register_name):
    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        state.memory.write(state.HL, value & ~(1 << bit))
    else:
        value = getattr(state, register_name) & ~(1 << bit)
        setattr(state, register_name, value)


@register_cb_instruction(0x80, 0, 8)
def handle_cb_res_0_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "B")


@register_cb_instruction(0x81, 0, 8)
def handle_cb_res_0_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "C")


@register_cb_instruction(0x82, 0, 8)
def handle_cb_res_0_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "D")


@register_cb_instruction(0x83, 0, 8)
def handle_cb_res_0_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "E")


@register_cb_instruction(0x84, 0, 8)
def handle_cb_res_0_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "H")


@register_cb_instruction(0x85, 0, 8)
def handle_cb_res_0_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "L")


@register_cb_instruction(0x86, 0, 16)
def handle_cb_res_0_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "(HL)")


@register_cb_instruction(0x87, 0, 8)
def handle_cb_res_0_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 0, "A")


@register_cb_instruction(0x88, 0, 8)
def handle_cb_res_1_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "B")


@register_cb_instruction(0x89, 0, 8)
def handle_cb_res_1_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "C")


@register_cb_instruction(0x8A, 0, 8)
def handle_cb_res_1_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "D")


@register_cb_instruction(0x8B, 0, 8)
def handle_cb_res_1_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "E")


@register_cb_instruction(0x8C, 0, 8)
def handle_cb_res_1_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "H")


@register_cb_instruction(0x8D, 0, 8)
def handle_cb_res_1_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "L")


@register_cb_instruction(0x8E, 0, 16)
def handle_cb_res_1_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "(HL)")


@register_cb_instruction(0x8F, 0, 8)
def handle_cb_res_1_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 1, "A")


@register_cb_instruction(0x90, 0, 8)
def handle_cb_res_2_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "B")


@register_cb_instruction(0x91, 0, 8)
def handle_cb_res_2_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "C")


@register_cb_instruction(0x92, 0, 8)
def handle_cb_res_2_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "D")


@register_cb_instruction(0x93, 0, 8)
def handle_cb_res_2_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "E")


@register_cb_instruction(0x94, 0, 8)
def handle_cb_res_2_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "H")


@register_cb_instruction(0x95, 0, 8)
def handle_cb_res_2_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "L")


@register_cb_instruction(0x96, 0, 16)
def handle_cb_res_2_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "(HL)")


@register_cb_instruction(0x97, 0, 8)
def handle_cb_res_2_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 2, "A")


@register_cb_instruction(0x98, 0, 8)
def handle_cb_res_3_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "B")


@register_cb_instruction(0x99, 0, 8)
def handle_cb_res_3_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "C")


@register_cb_instruction(0x9A, 0, 8)
def handle_cb_res_3_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "D")


@register_cb_instruction(0x9B, 0, 8)
def handle_cb_res_3_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "E")


@register_cb_instruction(0x9C, 0, 8)
def handle_cb_res_3_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "H")


@register_cb_instruction(0x9D, 0, 8)
def handle_cb_res_3_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "L")


@register_cb_instruction(0x9E, 0, 16)
def handle_cb_res_3_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "(HL)")


@register_cb_instruction(0x9F, 0, 8)
def handle_cb_res_3_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 3, "A")


@register_cb_instruction(0xA0, 0, 8)
def handle_cb_res_4_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "B")


@register_cb_instruction(0xA1, 0, 8)
def handle_cb_res_4_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "C")


@register_cb_instruction(0xA2, 0, 8)
def handle_cb_res_4_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "D")


@register_cb_instruction(0xA3, 0, 8)
def handle_cb_res_4_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "E")


@register_cb_instruction(0xA4, 0, 8)
def handle_cb_res_4_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "H")


@register_cb_instruction(0xA5, 0, 8)
def handle_cb_res_4_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "L")


@register_cb_instruction(0xA6, 0, 16)
def handle_cb_res_4_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "(HL)")


@register_cb_instruction(0xA7, 0, 8)
def handle_cb_res_4_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 4, "A")


@register_cb_instruction(0xA8, 0, 8)
def handle_cb_res_5_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "B")


@register_cb_instruction(0xA9, 0, 8)
def handle_cb_res_5_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "C")


@register_cb_instruction(0xAA, 0, 8)
def handle_cb_res_5_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "D")


@register_cb_instruction(0xAB, 0, 8)
def handle_cb_res_5_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "E")


@register_cb_instruction(0xAC, 0, 8)
def handle_cb_res_5_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "H")


@register_cb_instruction(0xAD, 0, 8)
def handle_cb_res_5_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "L")


@register_cb_instruction(0xAE, 0, 16)
def handle_cb_res_5_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "(HL)")


@register_cb_instruction(0xAF, 0, 8)
def handle_cb_res_5_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 5, "A")


@register_cb_instruction(0xB0, 0, 8)
def handle_cb_res_6_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "B")


@register_cb_instruction(0xB1, 0, 8)
def handle_cb_res_6_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "C")


@register_cb_instruction(0xB2, 0, 8)
def handle_cb_res_6_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "D")


@register_cb_instruction(0xB3, 0, 8)
def handle_cb_res_6_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "E")


@register_cb_instruction(0xB4, 0, 8)
def handle_cb_res_6_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "H")


@register_cb_instruction(0xB5, 0, 8)
def handle_cb_res_6_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "L")


@register_cb_instruction(0xB6, 0, 16)
def handle_cb_res_6_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "(HL)")


@register_cb_instruction(0xB7, 0, 8)
def handle_cb_res_6_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 6, "A")


@register_cb_instruction(0xB8, 0, 8)
def handle_cb_res_7_b(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "B")


@register_cb_instruction(0xB9, 0, 8)
def handle_cb_res_7_c(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "C")


@register_cb_instruction(0xBA, 0, 8)
def handle_cb_res_7_d(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "D")


@register_cb_instruction(0xBB, 0, 8)
def handle_cb_res_7_e(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "E")


@register_cb_instruction(0xBC, 0, 8)
def handle_cb_res_7_h(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "H")


@register_cb_instruction(0xBD, 0, 8)
def handle_cb_res_7_l(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "L")


@register_cb_instruction(0xBE, 0, 16)
def handle_cb_res_7_hl(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "(HL)")


@register_cb_instruction(0xBF, 0, 8)
def handle_cb_res_7_a(logger, cpu, instruction):
    handle_cb_generic_res(cpu._state, 7, "A")


def handle_cb_generic_set(state, bit, register_name):
    if register_name == "(HL)":
        value = state.memory.read(state.HL)
        state.memory.write(state.HL, value | (1 << bit))
    else:
        value = getattr(state, register_name) | (1 << bit)
        setattr(state, register_name, value)


@register_cb_instruction(0xC0, 0, 8)
def handle_cb_set_0_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "B")


@register_cb_instruction(0xC1, 0, 8)
def handle_cb_set_0_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "C")


@register_cb_instruction(0xC2, 0, 8)
def handle_cb_set_0_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "D")


@register_cb_instruction(0xC3, 0, 8)
def handle_cb_set_0_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "E")


@register_cb_instruction(0xC4, 0, 8)
def handle_cb_set_0_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "H")


@register_cb_instruction(0xC5, 0, 8)
def handle_cb_set_0_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "L")


@register_cb_instruction(0xC6, 0, 16)
def handle_cb_set_0_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "(HL)")


@register_cb_instruction(0xC7, 0, 8)
def handle_cb_set_0_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 0, "A")


@register_cb_instruction(0xC8, 0, 8)
def handle_cb_set_1_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "B")


@register_cb_instruction(0xC9, 0, 8)
def handle_cb_set_1_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "C")


@register_cb_instruction(0xCA, 0, 8)
def handle_cb_set_1_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "D")


@register_cb_instruction(0xCB, 0, 8)
def handle_cb_set_1_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "E")


@register_cb_instruction(0xCC, 0, 8)
def handle_cb_set_1_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "H")


@register_cb_instruction(0xCD, 0, 8)
def handle_cb_set_1_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "L")


@register_cb_instruction(0xCE, 0, 16)
def handle_cb_set_1_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "(HL)")


@register_cb_instruction(0xCF, 0, 8)
def handle_cb_set_1_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 1, "A")


@register_cb_instruction(0xD0, 0, 8)
def handle_cb_set_2_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "B")


@register_cb_instruction(0xD1, 0, 8)
def handle_cb_set_2_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "C")


@register_cb_instruction(0xD2, 0, 8)
def handle_cb_set_2_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "D")


@register_cb_instruction(0xD3, 0, 8)
def handle_cb_set_2_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "E")


@register_cb_instruction(0xD4, 0, 8)
def handle_cb_set_2_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "H")


@register_cb_instruction(0xD5, 0, 8)
def handle_cb_set_2_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "L")


@register_cb_instruction(0xD6, 0, 16)
def handle_cb_set_2_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "(HL)")


@register_cb_instruction(0xD7, 0, 8)
def handle_cb_set_2_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 2, "A")


@register_cb_instruction(0xD8, 0, 8)
def handle_cb_set_3_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "B")


@register_cb_instruction(0xD9, 0, 8)
def handle_cb_set_3_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "C")


@register_cb_instruction(0xDA, 0, 8)
def handle_cb_set_3_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "D")


@register_cb_instruction(0xDB, 0, 8)
def handle_cb_set_3_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "E")


@register_cb_instruction(0xDC, 0, 8)
def handle_cb_set_3_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "H")


@register_cb_instruction(0xDD, 0, 8)
def handle_cb_set_3_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "L")


@register_cb_instruction(0xDE, 0, 16)
def handle_cb_set_3_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "(HL)")


@register_cb_instruction(0xDF, 0, 8)
def handle_cb_set_3_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 3, "A")


@register_cb_instruction(0xE0, 0, 8)
def handle_cb_set_4_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "B")


@register_cb_instruction(0xE1, 0, 8)
def handle_cb_set_4_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "C")


@register_cb_instruction(0xE2, 0, 8)
def handle_cb_set_4_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "D")


@register_cb_instruction(0xE3, 0, 8)
def handle_cb_set_4_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "E")


@register_cb_instruction(0xE4, 0, 8)
def handle_cb_set_4_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "H")


@register_cb_instruction(0xE5, 0, 8)
def handle_cb_set_4_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "L")


@register_cb_instruction(0xE6, 0, 16)
def handle_cb_set_4_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "(HL)")


@register_cb_instruction(0xE7, 0, 8)
def handle_cb_set_4_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 4, "A")


@register_cb_instruction(0xE8, 0, 8)
def handle_cb_set_5_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "B")


@register_cb_instruction(0xE9, 0, 8)
def handle_cb_set_5_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "C")


@register_cb_instruction(0xEA, 0, 8)
def handle_cb_set_5_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "D")


@register_cb_instruction(0xEB, 0, 8)
def handle_cb_set_5_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "E")


@register_cb_instruction(0xEC, 0, 8)
def handle_cb_set_5_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "H")


@register_cb_instruction(0xED, 0, 8)
def handle_cb_set_5_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "L")


@register_cb_instruction(0xEE, 0, 16)
def handle_cb_set_5_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "(HL)")


@register_cb_instruction(0xEF, 0, 8)
def handle_cb_set_5_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 5, "A")


@register_cb_instruction(0xF0, 0, 8)
def handle_cb_set_6_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "B")


@register_cb_instruction(0xF1, 0, 8)
def handle_cb_set_6_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "C")


@register_cb_instruction(0xF2, 0, 8)
def handle_cb_set_6_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "D")


@register_cb_instruction(0xF3, 0, 8)
def handle_cb_set_6_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "E")


@register_cb_instruction(0xF4, 0, 8)
def handle_cb_set_6_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "H")


@register_cb_instruction(0xF5, 0, 8)
def handle_cb_set_6_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "L")


@register_cb_instruction(0xF6, 0, 16)
def handle_cb_set_6_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "(HL)")


@register_cb_instruction(0xF7, 0, 8)
def handle_cb_set_6_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 6, "A")


@register_cb_instruction(0xF8, 0, 8)
def handle_cb_set_7_b(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "B")


@register_cb_instruction(0xF9, 0, 8)
def handle_cb_set_7_c(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "C")


@register_cb_instruction(0xFA, 0, 8)
def handle_cb_set_7_d(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "D")


@register_cb_instruction(0xFB, 0, 8)
def handle_cb_set_7_e(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "E")


@register_cb_instruction(0xFC, 0, 8)
def handle_cb_set_7_h(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "H")


@register_cb_instruction(0xFD, 0, 8)
def handle_cb_set_7_l(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "L")


@register_cb_instruction(0xFE, 0, 16)
def handle_cb_set_7_hl(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "(HL)")


@register_cb_instruction(0xFF, 0, 8)
def handle_cb_set_7_a(logger, cpu, instruction):
    handle_cb_generic_set(cpu._state, 7, "A")


@register_instruction(0xA0, 0, 4)
def handle_and_a_b(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "B")


@register_instruction(0xA1, 0, 4)
def handle_and_a_c(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "C")


@register_instruction(0xA2, 0, 4)
def handle_and_a_d(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "D")


@register_instruction(0xA3, 0, 4)
def handle_and_a_e(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "E")


@register_instruction(0xA4, 0, 4)
def handle_and_a_h(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "H")


@register_instruction(0xA5, 0, 4)
def handle_and_a_l(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "L")


@register_instruction(0xA6, 0, 8)
def handle_and_a_hl_mem(logger, cpu, instruction):
    value = cpu._state.memory.read(cpu._state.HL)
    a = cpu._state.A & value
    cpu._state.A = a
    cpu._state.zf = 1 if a == 0 else 0
    cpu._state.nf = 0
    cpu._state.hf = 1
    cpu._state.cf = 0


@register_instruction(0xA7, 0, 4)
def handle_and_a_a(logger, cpu, instruction):
    handle_generic_and_(cpu._state, "A", "A")
