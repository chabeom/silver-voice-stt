param(
    [string]$VenvDir = ".venv-training",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$TrainingRoot = Join-Path $RepoRoot "services\training_pipeline"
$RequirementsFile = Join-Path $TrainingRoot "requirements.txt"
$VenvPath = Join-Path $RepoRoot $VenvDir
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"

function Get-BasePython {
    $candidates = @(
        @("py", "-3.11"),
        @("py", "-3.10"),
        @("py", "-3.9"),
        @("python")
    )

    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        $args = @()
        if ($candidate.Count -gt 1) {
            $args = $candidate[1..($candidate.Count - 1)]
        }

        try {
            & $exe @args --version *> $null
            return @{ Exe = $exe; Args = $args }
        } catch {
        }
    }

    throw "Python was not found. Install Python 3.10 or 3.11, then rerun this script."
}

if ($Force -and (Test-Path $VenvPath)) {
    Remove-Item -LiteralPath $VenvPath -Recurse -Force
}

if (!(Test-Path $PythonPath)) {
    $basePython = Get-BasePython
    Write-Host "Creating training virtual environment at $VenvPath"
    & $basePython.Exe @($basePython.Args + @("-m", "venv", $VenvPath))
}

Write-Host "Upgrading pip tooling"
& $PythonPath -m pip install --upgrade pip setuptools wheel

Write-Host "Installing training dependencies from $RequirementsFile"
& $PythonPath -m pip install -r $RequirementsFile

Write-Host "Validating installed packages"
& $PythonPath -c "import torch, transformers, datasets, peft, jiwer, soundfile; print('training env ok'); print('torch cuda available:', torch.cuda.is_available())"

Write-Host "Done. Use scripts\prepare-local-training-data.ps1 then scripts\train-local-whisper-cpu.ps1."
