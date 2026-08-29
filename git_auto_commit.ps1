# git_auto_commit.ps1
param(
    [Parameter(Mandatory=$true)][string]$Message
)

# Ensure we are in the repository root
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Add all changes, commit with the provided message, and push
git add .
if ($LASTEXITCODE -ne 0) { Write-Error "git add failed"; exit 1 }

git commit -m $Message
if ($LASTEXITCODE -ne 0) { Write-Error "git commit failed (maybe no changes)"; exit 1 }

git push origin main
if ($LASTEXITCODE -ne 0) { Write-Error "git push failed"; exit 1 }

Write-Host "Changes committed and pushed successfully."
