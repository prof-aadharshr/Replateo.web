$ErrorActionPreference = "Continue" # Don't stop on error, verify output
Start-Transcript -Path "c:\Users\Aadharsh\Desktop\REPLATEO\react_replateo\git_log.txt" -Force
Write-Host "Starting Git Recovery..."

if (Test-Path .git) {
    Write-Host "Removing existing .git folder..."
    Remove-Item -Recurse -Force .git
}

Write-Host "Initializing Git..."
git init

Write-Host "Adding Remote..."
git remote add origin https://github.com/prof-aadharshr/Replateo.web.git

Write-Host "Adding Files..."
git add .

Write-Host "Committing..."
git commit -m "fix: Final recovery push"

Write-Host "Branching..."
git branch -M main

Write-Host "Pushing..."
git push -u -f origin main

Write-Host "Done!"
