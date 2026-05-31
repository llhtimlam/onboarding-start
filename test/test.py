# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray
import numpy as np

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM frequency test")
    
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Set to PWM Mode
    dut._log.info("Write transaction, address 0x00, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 
    
    dut._log.info("Write transaction, address 0x01, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x03, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 

    # Set Duty Cycle 1/256
    dut._log.info("Set 1-Pulse Duty cycle")
    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    #assert dut.pwm_peripheral_inst.pwm_duty_cycle.value == 0x01, f"Expected 0x01, got {dut.pwm_peripheral_inst.pwm_duty_cycle.value}"
    await ClockCycles(dut.clk, 1000)

    # Sample all pwm pin for 100 PWM tick
    dut._log.info("Test 100 PWM Cycle")
    timestamp = [[] for _ in range(16)] # Initialize timestamp list of 16 pin list
    pin_on = [0] * 16
    for i in range(300000):
        # Output pin
        for j in range(8):
            if pin_on[j] == 1: # Skip timestamp sampling until it turn low for posedge detection
                if dut.uo_out.value[j] == 0:
                    pin_on[j] = 0
            elif dut.uo_out.value[j] == 1:
                timestamp[j].append(i)
                pin_on[j] = 1

        # Bidirectional pin
        for k in range(8):
            if pin_on[k+8] == 1: # Skip timestamp sampling until it turn low for posedge detection
                if dut.uio_out.value[k] == 0:
                    pin_on[k+8] = 0
            elif dut.uio_out.value[k] == 1:
                timestamp[k+8].append(i)
                pin_on[k+8] = 1
        await ClockCycles(dut.clk, 1)

    # Verify frequency tolerance (2970–3030 Hz)
    UPPER_FREQUENCY_TOLERANCE = int(np.ceil(10000000 / 2970))
    LOWER_FREQUENCY_TOLERANCE = int(np.floor(10000000 / 3030))
    # Calculate PWM posedge pulse interval
    for pin in range(16):
        if len(timestamp[pin]) < 2: # Timeout check
            if pin < 8:
                assert False, f"[TIMEOUT] Output Pin {pin} did not response."
            else:
                assert False, f"[TIMEOUT] Bidirectional Pin {pin-8} did not response"
        periods = np.diff(timestamp[pin])
        within_bounds = np.all((periods >= LOWER_FREQUENCY_TOLERANCE) & (periods <= UPPER_FREQUENCY_TOLERANCE))
        if pin < 8:
            assert within_bounds, f"Output Pin {pin} failed PWM Frequency test! Periods: {periods}"
        else:
            assert within_bounds, f"Bidirectional Pin {pin-8} failed PWM Frequency test! Periods: {periods}"
    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")
    
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

     # Set to PWM Mode
    dut._log.info("Write transaction, address 0x00, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 
    
    dut._log.info("Write transaction, address 0x01, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x03, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000) 

    # Test 0%, 50%, and 100% duty cycles
    # Test Duty Cycle 0%
    dut._log.info("Set Duty cycle 0%")
    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    #assert dut.pwm_peripheral_inst.pwm_duty_cycle.value == 0x00, f"Expected 0x00, got {dut.pwm_peripheral_inst.pwm_duty_cycle.value}"
    await ClockCycles(dut.clk, 1000) 

    # Sample all pwm pin for 100 PWM tick
    dut._log.info("Test 100 PWM Cycle")
    for i in range(300000):
        # Output pin
        for j in range(8):
            assert dut.uo_out.value[j] == 0, f"Output Pin {j} failed PWM Duty Cycle (0%) test!"
        # Bidirectional pin
        for k in range(8):
            assert dut.uio_out.value[k] == 0, f"Bidirectional Pin {k} failed PWM Duty Cycle (0%) test!"
        await ClockCycles(dut.clk, 1)
    dut._log.info("PWM Duty Cycle (0%) test completed successfully")

    # Test Duty Cycle 50%
    dut._log.info("Set Duty cycle 50%")
    dut._log.info("Write transaction, address 0x04, data 0x7F")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x7F)  # Write transaction
    #assert dut.pwm_peripheral_inst.pwm_duty_cycle.value == 0x7F, f"Expected 0x7F, got {dut.pwm_peripheral_inst.pwm_duty_cycle.value}"
    await ClockCycles(dut.clk, 1000) 

    # Sample all pwm pin for 100 PWM tick
    dut._log.info("Test 100 PWM Cycle")
    timestamp = [[] for _ in range(16)] # Initialize timestamp list of 16 pin list
    pin_on = [0] * 16
    for i in range(300000):
        # Output pin
        for j in range(8):
            if pin_on[j] == 1: # Negedge detection
                if dut.uo_out.value[j] == 0:
                    timestamp[j].append(i)
                    pin_on[j] = 0
            elif dut.uo_out.value[j] == 1: # Posedge detection
                timestamp[j].append(i)
                pin_on[j] = 1

        # Bidirectional pin
        for k in range(8):
            if pin_on[k+8] == 1: # Negedge detection
                if dut.uio_out.value[k] == 0:
                    timestamp[k+8].append(i)
                    pin_on[k+8] = 0
            elif dut.uio_out.value[k] == 1: # Posedge detection
                timestamp[k+8].append(i)
                pin_on[k+8] = 1
        await ClockCycles(dut.clk, 1)
    
    # 50% of frequency tolerance
    UPPER_FREQUENCY_TOLERANCE = int(np.ceil(10000000 / (2970) / 2))
    LOWER_FREQUENCY_TOLERANCE = int(np.floor(10000000 / (3030) / 2))
    # Calculate PWM posedge/negedge interval
    for pin in range(16):
        if len(timestamp[pin]) < 2: # Handle timeout edge cases (always high/low).
            if pin < 8:
                assert False, f"[TIMEOUT] Output Pin {pin} did not response."
            else:
                assert False, f"[TIMEOUT] Bidirectional Pin {pin-8} did not response"
        periods = np.diff(timestamp[pin])
        within_bounds = np.all((periods >= LOWER_FREQUENCY_TOLERANCE) & (periods <= UPPER_FREQUENCY_TOLERANCE))
        if pin < 8:
            assert within_bounds, f"Output Pin {pin} failed PWM Frequency test! Periods: {periods}"
        else:
            assert within_bounds, f"Bidirectional Pin {pin-8} failed PWM Frequency test! Periods: {periods}"
    dut._log.info("PWM Duty Cycle (50%) test completed successfully")

    # Test Duty Cycle 100%
    dut._log.info("Set Duty cycle 100%")
    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    #assert dut.pwm_peripheral_inst.pwm_duty_cycle.value == 0xFF, f"Expected 0xFF, got {dut.pwm_peripheral_inst.pwm_duty_cycle.value}"
    await ClockCycles(dut.clk, 1000) 

    # Sample all pwm pin for 100 PWM tick
    dut._log.info("Test 100 PWM Cycle")
    for i in range(300000):
        # Output pin
        for j in range(8):
            assert dut.uo_out.value[j] == 1, f"Output Pin {j} failed PWM Duty Cycle (100%) test!"
        # Bidirectional pin
        for k in range(8):
            assert dut.uio_out.value[k] == 1, f"Bidirectional Pin {k} failed PWM Duty Cycle (100%) test!"
        await ClockCycles(dut.clk, 1)
    dut._log.info("PWM Duty Cycle (100%) test completed successfully")

    dut._log.info("PWM Duty Cycle test completed successfully")
