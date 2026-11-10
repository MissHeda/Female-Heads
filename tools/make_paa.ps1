# Convert the composed PNGs (tools/out) to PAA (addons/heads/data) with ImageToPAA from the Arma 3 Tools.
$tool = "D:\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe"
$root = Split-Path -Parent $PSScriptRoot
foreach ($n in "fh_light_co", "fh_dark_co", "fh_nohq", "fh_smdi", "fh_as", "fh_injury_mc") {
    $src = Join-Path $root "tools\out\$n.png"
    if (-not (Test-Path $src)) { "skip $n"; continue }
    & $tool $src (Join-Path $root "addons\heads\data\$n.paa") | Out-Null
    "{0} {1:N0} bytes" -f $n, (Get-Item (Join-Path $root "addons\heads\data\$n.paa")).Length
}
