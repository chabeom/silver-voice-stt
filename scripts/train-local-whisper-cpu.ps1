param(
    [string]$ManifestDir = "training data\processed\local_manifest",
    [string]$OutputDir = "models\whisper-ko-elderly-local-cpu",
    [string]$ModelName = "openai/whisper-tiny",
    [int]$Epochs = 1,
    [int]$MaxTrainSamples = 100,
    [int]$MaxEvalSamples = 20,
    [int]$GradientAccumulationSteps = 4,
    [switch]$Background,
    [string]$ResumeFromCheckpoint = "",
    [string]$LoraAdapterPath = "",
    [string]$RunName = "",
    [switch]$SkipHistory
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot ".venv-training\Scripts\python.exe"
if (!(Test-Path $PythonPath)) {
    throw "Training venv was not found. Run scripts\setup-local-training-env.ps1 first."
}

$manifestPath = Join-Path $RepoRoot $ManifestDir
$trainManifest = Join-Path $manifestPath "train.jsonl"
$validManifest = Join-Path $manifestPath "valid.jsonl"
$testManifest = Join-Path $manifestPath "test.jsonl"
if (!(Test-Path $trainManifest) -or !(Test-Path $validManifest)) {
    throw "Manifest files were not found. Run scripts\prepare-local-training-data.ps1 first."
}

$outputPath = Join-Path $RepoRoot $OutputDir
$logDir = Join-Path $RepoRoot "logs\training"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "whisper-cpu-$timestamp.log"
$errPath = Join-Path $logDir "whisper-cpu-$timestamp.err.log"

$env:PYTHONPATH = Join-Path $RepoRoot "services\training_pipeline"
$env:TOKENIZERS_PARALLELISM = "false"
$threadCount = [Math]::Max(1, [Math]::Min([Environment]::ProcessorCount - 2, 12))
$env:OMP_NUM_THREADS = "$threadCount"
$env:MKL_NUM_THREADS = "$threadCount"

$trainScript = Join-Path $RepoRoot "services\training_pipeline\scripts\train_whisper.py"
$historyScript = Join-Path $RepoRoot "services\training_pipeline\scripts\record_training_result.py"
$historyCsv = Join-Path $RepoRoot "models\training_history.csv"
$historyJsonl = Join-Path $RepoRoot "models\training_history.jsonl"
$argsList = @(
    $trainScript,
    "--model-name-or-path", $ModelName,
    "--train-manifest", $trainManifest,
    "--valid-manifest", $validManifest,
    "--output-dir", $outputPath,
    "--language", "korean",
    "--task", "transcribe",
    "--train-strategy", "lora-encoder",
    "--batch-size", "1",
    "--eval-batch-size", "1",
    "--gradient-accumulation-steps", "$GradientAccumulationSteps",
    "--epochs", "$Epochs",
    "--learning-rate", "1e-5",
    "--logging-steps", "1",
    "--save-total-limit", "2",
    "--max-train-samples", "$MaxTrainSamples",
    "--max-eval-samples", "$MaxEvalSamples",
    "--dataloader-num-workers", "0",
    "--disable-gradient-checkpointing"
)

if (Test-Path $testManifest) {
    $argsList += @("--test-manifest", $testManifest)
}
if ($ResumeFromCheckpoint.Trim()) {
    $argsList += @("--resume-from-checkpoint", $ResumeFromCheckpoint)
}
if ($LoraAdapterPath.Trim()) {
    $adapterPath = Join-Path $RepoRoot $LoraAdapterPath
    $argsList += @("--lora-adapter-path", $adapterPath)
}

function ConvertTo-ProcessArgument {
    param([string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    $escaped = $Value -replace '\\(?=\\*")', '$0$0'
    $escaped = $escaped -replace '"', '\"'
    return '"' + $escaped + '"'
}

if ($Background) {
    $argumentLine = ($argsList | ForEach-Object { ConvertTo-ProcessArgument "$_" }) -join " "
    $process = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList $argumentLine `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $errPath `
        -WindowStyle Minimized `
        -PassThru

    Write-Host "Training started in the background."
    Write-Host "PID: $($process.Id)"
    Write-Host "stdout log: $logPath"
    Write-Host "stderr log: $errPath"
    Write-Host "Watch log: Get-Content `"$logPath`" -Wait"
} else {
    Write-Host "Training started in the current shell."
    Write-Host "Log: $logPath"
    & $PythonPath @argsList 2>&1 | Tee-Object -FilePath $logPath

    $resultPath = Join-Path $outputPath "training_result.json"
    if (!$SkipHistory -and (Test-Path $resultPath)) {
        $recordArgs = @(
            $historyScript,
            "--result-file", $resultPath,
            "--history-csv", $historyCsv,
            "--history-jsonl", $historyJsonl
        )
        if ($RunName.Trim()) {
            $recordArgs += @("--run-name", $RunName)
        }
        Write-Host "Recording training result history."
        & $PythonPath @recordArgs
    }
}
