#!/bin/bash
# read capability container
opensc-tool -s "00 A4 04 00 07 D2760000850101" -s "00 A4 00 0C 02 E103" -s "00 b0 00 00 0f"
# read ndef from file 0xe104
opensc-tool -s "00 a4 04 00 07 D2760000850101" -s "00 a4 00 0c 02 E104" -s "00 b0 00 00 00"
