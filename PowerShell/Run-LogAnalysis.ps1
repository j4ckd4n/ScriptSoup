param(
  [Parameter(Mandatory=$true)]
  [string]$path
)

if(!(Test-Path $path -PathType Leaf)) {
  throw "Path specified does not point to a file"
  exit 1
}

if ((Get-ChildItem -Path $path).Extension -notlike ".7z") {
  throw "Specified file is not a .7z file."
  exit 2
}


$new_folder_path = (Get-ChildItem -Path $path).BaseName

$new_folder_path = mkdir -Path $new_folder_path -Force

Write-Output "Extracting the .7z file..."
7z x $path -o"$($new_folder_path.FullName)"

if(!(Test-Path "$new_folder_path\PlatformLogs.zip")) {
  throw "PlatformLogs.zip does not exist, cannot conduct log review"
  exit 3
}

Expand-Archive "$new_folder_path\PlatformLogs.zip" -DestinationPath "$new_folder_path\PlatformLogs"

$log_directory = "$new_folder_path\PlatformLogs\EventViewer"

if(!(Test-Path -Path $log_directory)){
  throw "EventViewer log file directory does not exist"
  exit 4
}

# This assumes that you have Hayabusa in your $ENV:PATH
hayabusa.exe csv-timeline -d $log_directory -o "$log_directory\hayabusa.csv"

Start-Process "$log_directory\hayabusa.csv"
