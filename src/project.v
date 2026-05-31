/*
 * Copyright (c) 2024 Tim Lam
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
//`include "pwm_peripheral.v"

module tt_um_uwasic_onboarding_llhtimlam #(
  parameter [6:0] MAX_ADDRESS = 7'h04
)(
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Wire Setting
  assign uio_oe  = 8'b11111111;
  wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

  // Define Peripheral
  wire SCLK, COPI, nCS;
  reg [7:0] en_reg_out_7_0;
  reg [7:0] en_reg_out_15_8;
  reg [7:0] en_reg_pwm_7_0;
  reg [7:0] en_reg_pwm_15_8;
  reg [7:0] pwm_duty_cycle;

  // Input: SPI Interface
  assign SCLK = ui_in[0];
  assign COPI = ui_in[1];
  assign nCS  = ui_in[2];

  // Output: PWM Interface
  //wire OUT_0, OUT_1, OUT_2, OUT_3, OUT_4, OUT_5, OUT_6, OUT_7;
  //wire OUT_8, OUT_9, OUT_10, OUT_11, OUT_12, OUT_13, OUT_14, OUT_15;
  //assign uo_out[0]  = OUT_0;
  //assign uo_out[1]  = OUT_1;
  //assign uo_out[2]  = OUT_2;
  //assign uo_out[3]  = OUT_3;
  //assign uo_out[4]  = OUT_4;
  //assign uo_out[5]  = OUT_5;
  //assign uo_out[6]  = OUT_6;
  //assign uo_out[7]  = OUT_7;

  //assign uio_out[0] = OUT_8;
  //assign uio_out[1] = OUT_9;
  //assign uio_out[2] = OUT_10;
  //assign uio_out[3] = OUT_11;
  //assign uio_out[4] = OUT_12;
  //assign uio_out[5] = OUT_13;
  //assign uio_out[6] = OUT_14;
  //assign uio_out[7] = OUT_15;

  //assign OUT_0  = en_reg_out_7_0[0];
  //assign OUT_1  = en_reg_out_7_0[1];
  //assign OUT_2  = en_reg_out_7_0[2];
  //assign OUT_3  = en_reg_out_7_0[3];
  //assign OUT_4  = en_reg_out_7_0[4];
  //assign OUT_5  = en_reg_out_7_0[5];
  //assign OUT_6  = en_reg_out_7_0[6];
  //assign OUT_7  = en_reg_out_7_0[7];

  //assign OUT_8  = en_reg_out_15_8[0];
  //assign OUT_9  = en_reg_out_15_8[1];
  //assign OUT_10 = en_reg_out_15_8[2];
  //assign OUT_11 = en_reg_out_15_8[3];
  //assign OUT_12 = en_reg_out_15_8[4];
  //assign OUT_13 = en_reg_out_15_8[5];
  //assign OUT_14 = en_reg_out_15_8[6];
  //assign OUT_15 = en_reg_out_15_8[7];

  // SPI Clock
  wire SPI_clk = (SPI_counter == 7'd99); // count 100 for 10MHz Clk to 100kHz SPI
  reg [6:0] SPI_counter;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      SPI_counter <= 7'b0;
    end else if (!SPI_clk) begin
      SPI_counter <= SPI_counter + 7'b1;
    end else begin
      SPI_counter <= 7'b0;
    end
  end

  // Hashing
  reg [3:0] bit_idx;
  reg [15:0] data;

  // FIFO and CDC intermediate
  reg nCS_meta, nCS_sync1, nCS_sync2;
  reg SCLK_meta, SCLK_sync1, SCLK_sync2;
  reg COPI_meta, COPI_sync1, COPI_sync2;
  wire nCS_negedge, nCS_posedge;
  wire SCLK_posedge;
  //wire SCLK_negedge;
  reg transaction_ready, transaction_end, transaction_complete;

  // nCS
  always @(posedge clk) begin 
    nCS_meta <= nCS;
    nCS_sync1 <= nCS_meta;
    nCS_sync2 <= nCS_sync1;
  end
  assign nCS_negedge = (!nCS_sync1 && nCS_sync2);
  assign nCS_posedge = (nCS_sync1 && !nCS_sync2);

  // SCLK
  always @(posedge clk) begin 
    SCLK_meta <= SCLK;
    SCLK_sync1 <= SCLK_meta;
    SCLK_sync2 <= SCLK_sync1;
  end
  //assign SCLK_negedge = (!SCLK_sync1 && SCLK_sync2);
  assign SCLK_posedge = (SCLK_sync1 && !SCLK_sync2);

  // COPI
  always @(posedge clk) begin 
    COPI_meta <= COPI;
    COPI_sync1 <= COPI_meta;
    COPI_sync2 <= COPI_sync1;
  end

  // Listen nCS
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      transaction_ready <= 1'b0;
    end else begin
      if (nCS_negedge) begin // Start listening when nCS drop
        transaction_ready <= 1'b1;
      end else if (nCS_posedge || transaction_complete) begin // Stop listening when completed or interrupted
          transaction_ready <= 1'b0;
      end
    end
  end

  // Reset and Process Trigger
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      transaction_complete <= 1'b0;
    end else begin // Reset after pulsing trigger
      transaction_complete <= 1'b0;
      if (transaction_end && nCS_posedge) begin // Process command after nCS rise if valid
        transaction_complete <= 1'b1;
      end
    end
  end

  // Sample COPI
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      bit_idx         <= 4'b0;
      data            <= 16'b0;
      transaction_end <= 1'b0;
    end else begin
      if (nCS_sync2) begin // Reset if interrupted
        bit_idx         <= 4'd0;
        transaction_end <= 1'b0;
      end else if (transaction_ready && SCLK_posedge && !transaction_end) begin // Sample for the listening window when SCLK rise
        data[4'd15 - bit_idx] <= COPI_sync2;
        if (bit_idx == 4'd15) begin // Reset and stop listening when command end at 16th bit
          bit_idx         <= 4'b0;
          transaction_end <= 1'b1;
        end else begin // Progress to next bit for next SCLK rise
          bit_idx <= bit_idx + 4'b1;
        end
      end
    end
  end
  
  // Process Hashing
  wire       cmd_function = data[15];
  wire [6:0] cmd_address  = data[14:8];
  wire [7:0] cmd_data     = data[7:0];

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      en_reg_out_7_0   <= 8'h00;
      en_reg_out_15_8  <= 8'h00;
      en_reg_pwm_7_0   <= 8'h00;
      en_reg_pwm_15_8  <= 8'h00;
      pwm_duty_cycle   <= 8'h00;
    end else begin
      if (transaction_complete) begin // Process only when trigger
        if (cmd_function) begin // 1: Write 0: Read
          if (cmd_address <= MAX_ADDRESS) begin // Skip invalid address
            case (cmd_address)
              7'h00: en_reg_out_7_0  <= cmd_data;
              7'h01: en_reg_out_15_8 <= cmd_data;
              7'h02: en_reg_pwm_7_0  <= cmd_data;
              7'h03: en_reg_pwm_15_8 <= cmd_data;
              7'h04: pwm_duty_cycle  <= cmd_data;
              default: begin // Idle when invalid address
              end
            endcase
          end
        end
      end
    end
  end

  // PWM 3072 Hz
  pwm_peripheral pwm_peripheral_inst (
    .clk(clk),
    .rst_n(rst_n),
    .en_reg_out_7_0(en_reg_out_7_0),
    .en_reg_out_15_8(en_reg_out_15_8),
    .en_reg_pwm_7_0(en_reg_pwm_7_0),
    .en_reg_pwm_15_8(en_reg_pwm_15_8),
    .pwm_duty_cycle(pwm_duty_cycle),
    .out({uio_out, uo_out})
  );

endmodule
