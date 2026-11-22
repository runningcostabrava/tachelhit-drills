# Engega un guió llarg FORA de la sessió de Claude, com a procés propi del Windows, perquè el
# reaper de memòria de la sessió no el mati a mitja nit (li va passar a nit.py de TutlAit el
# 17-11-2026 a les 00:31). La sortida va a un registre al costat del guió o al que es digui.
#
# ÚS (des de PowerShell, o des de Claude amb «!»):
#   tools\lm\engega_fora.ps1 <guio.py> [arguments...] [-Registre <fitxer.log>]
# Exemple:
#   tools\lm\engega_fora.ps1 tools\tutlait\nit.py -Registre C:\Users\josep\Veus-tachelhit\_paquets\tutlait\nit_fora.log
#
# Fa servir sempre el venv del backend (mai el python global) amb -X utf8. Imprimeix el PID; per
# aturar-lo: Stop-Process -Id <PID>. Per veure'l: Get-Content <registre> -Wait.
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Guio,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Arguments = @(),
    [string]$Registre = ""
)
$arrel = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $arrel "backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "C:\Users\josep\app2\tachelhit-drills\backend\venv\Scripts\python.exe" }
if (-not (Test-Path $Guio)) { $Guio = Join-Path $arrel $Guio }
if (-not (Test-Path $Guio)) { throw "no trobo el guió $Guio" }
if (-not $Registre) { $Registre = [IO.Path]::ChangeExtension((Resolve-Path $Guio), ".fora.log") }
$llista = @("-X", "utf8", (Resolve-Path $Guio)) + $Arguments
$p = Start-Process -FilePath $python -ArgumentList $llista -WorkingDirectory $arrel -WindowStyle Hidden `
    -RedirectStandardOutput $Registre -RedirectStandardError ([IO.Path]::ChangeExtension($Registre, ".err.log")) -PassThru
"engegat PID $($p.Id): $Guio $($Arguments -join ' ')"
"registre: $Registre"
