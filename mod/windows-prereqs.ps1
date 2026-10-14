# Installs what the TGMC mod's setup needs on Windows 10/11 with winget: Git, Python 3, a full ffmpeg (with libvorbis) and Pillow.
# The .NET 10 SDK is fetched by setup itself into build\tools\dotnet. Run once, in PowerShell:
#
#   powershell -ExecutionPolicy Bypass -File mod\windows-prereqs.ps1
#
# Then open a NEW terminal window (so the PATH changes apply) and run setup.cmd.
$ErrorActionPreference = "Stop"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
	Write-Error "winget was not found. Install 'App Installer' from the Microsoft Store, or install Git, Python 3 and ffmpeg by hand."
}
function Install-IfMissing($command, $id) {
	if (Get-Command $command -ErrorAction SilentlyContinue) {
		Write-Host "$command is already installed"
	} else {
		winget install --id $id -e --accept-package-agreements --accept-source-agreements
	}
}
Install-IfMissing git Git.Git
Install-IfMissing python Python.Python.3.12
Install-IfMissing ffmpeg Gyan.FFmpeg
Write-Host ""
Write-Host "Installing Pillow..."
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m pip install --upgrade pillow } else { python -m pip install --upgrade pillow }
Write-Host ""
Write-Host "Done. Open a NEW terminal window and run setup.cmd."
