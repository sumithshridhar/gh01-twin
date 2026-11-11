#!/usr/bin/env bash
# Builds the alarm-logic test in a temporary folder, runs it, and deletes the program afterwards.
#   needs: pip install ziglang   (a C++ compiler that installs with pip)
set -e
cd "$(dirname "$0")"
T=$(mktemp -d)
python -m ziglang c++ -std=c++17 -O1 -w -o "$T/test_alarm_logic.exe" test_alarm_logic.cpp
"$T/test_alarm_logic.exe"; status=$?
rm -rf "$T"
exit $status
