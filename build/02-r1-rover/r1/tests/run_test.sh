#!/usr/bin/env bash
# Builds the firmware test in a temporary folder, runs it, and deletes the program afterwards.
set -e
cd "$(dirname "$0")"
T=$(mktemp -d)
python -m ziglang c++ -std=c++17 -O1 -w -I. -o "$T/test_r1_io.exe" test_r1_io.cpp
"$T/test_r1_io.exe"; status=$?
rm -rf "$T"
exit $status
