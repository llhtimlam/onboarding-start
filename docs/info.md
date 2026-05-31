<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

SPI Peripherial with PWM

## How to test

Send command from SPI Controller and output to PWM

### Register Map

| Address | Register Name | Description | Reset Value |
|:---:|:---|:---|:---:|
| **`0x00`** | `en_reg_out_7_0` | Enable output on (`uo_out[7:0]`) | `0x00` |
| **`0x01`** | `en_reg_out_15_8` | Enable output on (`uio_out[7:0]`) | `0x00` |
| **`0x02`** | `en_reg_pwm_7_0` | Enable PWM for (`uo_out[7:0]`)| `0x00` |
| **`0x03`** | `en_reg_pwm_15_8` | Enable PWM for (`uio_out[7:0]`) | `0x00` |
| **`0x04`** | `pwm_duty_cycle` | PWM Duty Cycle ( `0x00`=0%, `0xFF`=100%) | `0x00` |

### Output behavior

| Output Enable Bit | PWM Mode Bit | Result |
|:---:|:---:|:---:|
| **`0`** | **`X`** | Output `0` |
| **`1`** | **`0`** | Output `1` |
| **`1`** | **`1`** | Output PWM |

> Note: Output Enable takes absolute precedence over PWM Mode.

## External hardware

SPI Controller and PWM output interface
