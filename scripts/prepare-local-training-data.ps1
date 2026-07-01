param(
    [string]$MetadataFile = "training data\local\metadata.csv",
    [string]$AudioRoot = "training data\local\audio",
    [string]$OutputDir = "training data\processed\local_manifest",
    [double]$ValidRatio = 0.1,
    [double]$TestRatio = 0.1,
    [double]$MinDurationSeconds = 0.3,
    [double]$MaxDurationSeconds = 30.0,
    [int]$MaxSamples = 0,
    [switch]$ConvertToWav,
    [switch]$OverwriteConvertedAudio
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot ".venv-training\Scripts\python.exe"
if (!(Test-Path $PythonPath)) {
    throw "Training venv was not found. Run scripts\setup-local-training-env.ps1 first."
}

$env:PYTHONPATH = Join-Path $RepoRoot "services\training_pipeline"

$prepareScript = Join-Path $RepoRoot "services\training_pipeline\scripts\prepare_local_dataset.py"
$metadataPath = Join-Path $RepoRoot $MetadataFile
$audioRootPath = Join-Path $RepoRoot $AudioRoot
$outputPath = Join-Path $RepoRoot $OutputDir

$argsList = @(
    $prepareScript,
    "--metadata-file", $metadataPath,
    "--audio-root", $audioRootPath,
    "--output-dir", $outputPath,
    "--valid-ratio", $ValidRatio,
    "--test-ratio", $TestRatio,
    "--min-duration-seconds", $MinDurationSeconds,
    "--max-duration-seconds", $MaxDurationSeconds
)

if ($MaxSamples -gt 0) {
    $argsList += @("--max-samples", $MaxSamples)
}
if ($ConvertToWav) {
    $argsList += "--convert-to-wav"
}
if ($OverwriteConvertedAudio) {
    $argsList += "--overwrite-converted-audio"
}

& $PythonPath @argsList
