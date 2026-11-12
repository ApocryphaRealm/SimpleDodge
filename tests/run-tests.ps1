# Builds and runs the offline tests (the tap / double-tap rules of src\TapDetector.h). Needs clang++ (LLVM) on PATH, or
# set $env:CXX to another C++17 compiler that takes the same arguments. Exit code 0 = every test passed.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cxx = if ($env:CXX) { $env:CXX } else { 'clang++' }
$out = Join-Path ([IO.Path]::GetTempPath()) 'simpledodge-test-tap-detector.exe'
& $cxx -std=c++17 -I (Join-Path $here '..\src') (Join-Path $here 'test_tap_detector.cpp') -o $out
if ($LASTEXITCODE -ne 0) { Write-Output 'build failed'; exit 1 }
& $out
exit $LASTEXITCODE
