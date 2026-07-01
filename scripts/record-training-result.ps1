param(
    [string]$ResultFile = "models\whisper-ko-elderly-sample-cpu\training_result.json",
    [string]$HistoryCsv = "models\training_history.csv",
    [string]$HistoryJsonl = "models\training_history.jsonl",
    [string]$RunName = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot ".venv-training\Scripts\python.exe"
if (!(Test-Path $PythonPath)) {
    throw "Training venv was not found. Run scripts\setup-local-training-env.ps1 first."
}

$env:PYTHONPATH = Join-Path $RepoRoot "services\training_pipeline"
$recordScript = Join-Path $RepoRoot "services\training_pipeline\scripts\record_training_result.py"
$resultPath = Join-Path $RepoRoot $ResultFile
$historyCsvPath = Join-Path $RepoRoot $HistoryCsv
$historyJsonlPath = Join-Path $RepoRoot $HistoryJsonl

$argsList = @(
    $recordScript,
    "--result-file", $resultPath,
    "--history-csv", $historyCsvPath,
    "--history-jsonl", $historyJsonlPath
)

if ($RunName.Trim()) {
    $argsList += @("--run-name", $RunName)
}

& $PythonPath @argsList
