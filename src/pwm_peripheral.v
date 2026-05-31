/*
 * Copyright (c) 2024 Damir Gazizullin
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module pwm_peripheral (
    input  wire       clk,      // clock
    input  wire       rst_n,     // reset_n - low to reset
    input  wire [7:0] en_reg_out_7_0,
    input  wire [7:0] en_reg_out_15_8,
    input  wire [7:0] en_reg_pwm_7_0,
    input  wire [7:0] en_reg_pwm_15_8,
    input  wire [7:0] pwm_duty_cycle,
    output reg [15:0] out
);

    localparam clk_div_trig = 12; // Divide by (12+1)*256, yielding 3000 (3004.80769) Hz
    reg [3:0] clk_counter;
    reg [7:0] pwm_counter;
    wire pwm_signal = (pwm_duty_cycle == 8'hFF) ? 1'b1 : (pwm_counter <= pwm_duty_cycle); // 253 is 98.82% 254 is 99.21%, 255 is 100%, not 99.61%

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out <= 0;
            pwm_counter <= 0;
            clk_counter <= 0;
        end else begin
            if (clk_counter == clk_div_trig) begin
                pwm_counter <= pwm_counter + 1;
                clk_counter <= 0;
            end else begin
                clk_counter <= clk_counter + 1;
            end
            // Apply PWM to each bit individually if enabled
            // Lower 8 bits
            out[0] <= en_reg_out_7_0[0] ? (en_reg_pwm_7_0[0] ? pwm_signal : 1'b1) : 1'b0;
            out[1] <= en_reg_out_7_0[1] ? (en_reg_pwm_7_0[1] ? pwm_signal : 1'b1) : 1'b0;
            out[2] <= en_reg_out_7_0[2] ? (en_reg_pwm_7_0[2] ? pwm_signal : 1'b1) : 1'b0;
            out[3] <= en_reg_out_7_0[3] ? (en_reg_pwm_7_0[3] ? pwm_signal : 1'b1) : 1'b0;
            out[4] <= en_reg_out_7_0[4] ? (en_reg_pwm_7_0[4] ? pwm_signal : 1'b1) : 1'b0;
            out[5] <= en_reg_out_7_0[5] ? (en_reg_pwm_7_0[5] ? pwm_signal : 1'b1) : 1'b0;
            out[6] <= en_reg_out_7_0[6] ? (en_reg_pwm_7_0[6] ? pwm_signal : 1'b1) : 1'b0;
            out[7] <= en_reg_out_7_0[7] ? (en_reg_pwm_7_0[7] ? pwm_signal : 1'b1) : 1'b0;

            // Upper 8 bits
            out[8]  <= en_reg_out_15_8[0] ? (en_reg_pwm_15_8[0] ? pwm_signal : 1'b1) : 1'b0;
            out[9]  <= en_reg_out_15_8[1] ? (en_reg_pwm_15_8[1] ? pwm_signal : 1'b1) : 1'b0;
            out[10] <= en_reg_out_15_8[2] ? (en_reg_pwm_15_8[2] ? pwm_signal : 1'b1) : 1'b0;
            out[11] <= en_reg_out_15_8[3] ? (en_reg_pwm_15_8[3] ? pwm_signal : 1'b1) : 1'b0;
            out[12] <= en_reg_out_15_8[4] ? (en_reg_pwm_15_8[4] ? pwm_signal : 1'b1) : 1'b0;
            out[13] <= en_reg_out_15_8[5] ? (en_reg_pwm_15_8[5] ? pwm_signal : 1'b1) : 1'b0;
            out[14] <= en_reg_out_15_8[6] ? (en_reg_pwm_15_8[6] ? pwm_signal : 1'b1) : 1'b0;
            out[15] <= en_reg_out_15_8[7] ? (en_reg_pwm_15_8[7] ? pwm_signal : 1'b1) : 1'b0;
        end
    end

endmodule
