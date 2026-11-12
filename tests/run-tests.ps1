# Builds and runs the offline tests: the tap / double-tap rules of src\TapDetector.h and the roll turn math of
# src\RollHeading.h. Needs clang++ (LLVM) on PATH, or set $env:CXX to another C++17 compiler that takes the same
# arguments. Exit code 0 = every test passed.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cxx = if ($env:CXX) { $env:CXX } else { 'clang++' }
$failed = 0
foreach ($t in @('test_tap_detector', 'test_roll_heading')) {
    $out = Join-Path ([IO.Path]::GetTempPath()) ("simpledodge-$t.exe")
    & $cxx -std=c++17 -I (Join-Path $here '..\src') (Join-Path $here "$t.cpp") -o $out
    if ($LASTEXITCODE -ne 0) { Write-Output "${t}: build failed"; $failed++; continue }
    & $out
    if ($LASTEXITCODE -ne 0) { $failed++ }
}
exit $failed
