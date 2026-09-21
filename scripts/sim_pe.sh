#!/bin/bash

set -e

iverilog -g2012 \
    -o pe_sim \
    rtl/pe.sv \
    tb/pe_tb.sv

vvp pe_sim

