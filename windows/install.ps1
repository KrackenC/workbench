# Workbench -> Claude Code launcher for Windows (one-time setup per PC, no admin needed).
#
# Why: Claude Code's own claude-cli:// links open a terminal that closes at once on Windows
# (anthropics/claude-code#86056). This registers a separate link type, workbench-claude://,
# that opens Windows Terminal (or PowerShell) with Claude Code running in your home folder and the
# Workbench prompt pre-typed in the input box (claude --prefill), waiting for you to press Enter.
#
# Install:   irm https://raw.githubusercontent.com/KrackenC/workbench/main/windows/install.ps1 | iex
# Remove:    Remove-Item -Recurse HKCU:\Software\Classes\workbench-claude; Remove-Item -Recurse "$env:LOCALAPPDATA\Workbench"
#
# Safety: any web page can try to open a workbench-claude:// link, so the handler only passes on
# prompts that start with "Let's work on " (what the Workbench buttons send), up to 500 characters.
# Anything else opens a plain Claude Code session with no prompt. The prompt is handed to Claude
# through a temp file, never pasted into a command line.

$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:LOCALAPPDATA 'Workbench'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$handler = Join-Path $dir 'open-claude.ps1'

$handlerCode = @'
param([string]$Uri)
$ErrorActionPreference = 'Stop'
try {
  $prompt = ''
  if ($Uri -match '[?&]q=([^&]*)') { $prompt = [Uri]::UnescapeDataString($Matches[1].Replace('+', ' ')) }
  $prompt = ($prompt -replace '[\x00-\x1f\x7f]', ' ' -replace '"', "'").Trim()  # PowerShell 5 mangles " in arguments
  if ($prompt -and (-not $prompt.StartsWith("Let's work on ") -or $prompt.Length -gt 500)) { $prompt = '' }

  $claude = (Get-Command claude.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
  if (-not $claude) { $claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe' }
  if (-not (Test-Path -LiteralPath $claude)) { throw "Claude Code (claude.exe) was not found. Install it, then try again." }

  $tmp = Join-Path $env:TEMP ('workbench-prompt-' + [guid]::NewGuid().ToString('N') + '.txt')
  [IO.File]::WriteAllText($tmp, $prompt, (New-Object Text.UTF8Encoding $false))

  $q = { param($s) "'" + $s.Replace("'", "''") + "'" }
  $inner = "Set-Location -LiteralPath `$HOME; `$p = [IO.File]::ReadAllText($(& $q $tmp)); Remove-Item -LiteralPath $(& $q $tmp); " +
           "if (`$p) { & $(& $q $claude) --prefill `$p } else { & $(& $q $claude) }"
  $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))

  $wt = Get-Command wt.exe -ErrorAction SilentlyContinue
  if ($wt) {
    Start-Process -FilePath $wt.Source -ArgumentList @('new-tab', 'powershell.exe', '-NoExit', '-EncodedCommand', $enc)
  } else {
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-EncodedCommand', $enc)
  }
} catch {
  Add-Type -AssemblyName PresentationFramework
  [System.Windows.MessageBox]::Show("Workbench couldn't open Claude Code:`n`n" + $_.Exception.Message, 'Workbench') | Out-Null
}
'@
[IO.File]::WriteAllText($handler, $handlerCode, (New-Object Text.UTF8Encoding $true))

$key = 'HKCU:\Software\Classes\workbench-claude'
New-Item -Force -Path "$key\shell\open\command" | Out-Null
Set-ItemProperty -Path $key -Name '(Default)' -Value 'URL:Workbench Claude Code'
Set-ItemProperty -Path $key -Name 'URL Protocol' -Value ''
$cmd = 'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $handler + '" "%1"'
Set-ItemProperty -Path "$key\shell\open\command" -Name '(Default)' -Value $cmd

$found = Get-Command claude.exe -ErrorAction SilentlyContinue
Write-Host ''
Write-Host 'Workbench Claude Code launcher installed (prompts arrive pre-typed, not sent).' -ForegroundColor Green
if (-not $found -and -not (Test-Path (Join-Path $env:USERPROFILE '.local\bin\claude.exe'))) {
  Write-Host 'Note: claude.exe was not found on this PC yet. Install Claude Code before using the buttons.' -ForegroundColor Yellow
}
Write-Host 'The first time you click a Claude Code button, Chrome or Edge asks to open the link: tick "Always allow" and click Open.'
Write-Host 'Opening the Workbench so it knows this PC is set up...'
# Tells the page this PC has launcher version 2, which hides its "Set up this PC" button.
# Keep the number in step with LAUNCHER_VER in src/workbench.html.
Start-Process 'https://krackenc.github.io/workbench/#pc-ready-2'
