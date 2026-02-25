# PowerShell script to commit the root repository of the project
# Usage: .\commit.ps1 "Commit message"

git add .
git commit -m $args[0]
if ($LASTEXITCODE -eq 0) {
    Write-Host "Commit successful."
} else {
    Write-Host "Commit failed."
}
