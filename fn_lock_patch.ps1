<#
  Magic Keyboard (A2449, Bluetooth) - enable the Fn and Lock (Touch ID) keys WITHOUT a driver

  How it works:
  Windows caches the SDP record of Bluetooth HID devices (including the HID report descriptor)
  in the registry: HKLM\SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices\<MAC>\CachedServices
  In the keyboard's descriptor the Fn bit uses a vendor usage (0xFF01/0x03) and the Lock key is
  Consumer 0x019E (AL Terminal Lock). The Windows keyboard driver (kbdhid) drops both.
  This script rewrites them in place (same length) to standard keys:
      Fn    -> F24 (Keyboard page 0x07, usage 0x73)
      Lock  -> F23 (Keyboard page 0x07, usage 0x72)
  magic_keyboard_media.ahk then handles the F24 / F23 combinations.

  Usage (asks for administrator rights by itself):
      fn_lock_patch.bat            -> patch + restart the keyboard
      fn_lock_patch.bat -Restore   -> restore the original descriptor from the backup

  Backup: sdp_backup_<MAC>.reg in this folder (created on the first run only, from the original).
  Windows rewrites the cache when the keyboard is paired again, then run this script again.
#>
param([switch]$Restore)

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Restore) { $argList += " -Restore" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
    exit
}

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $PSCommandPath
$devRoot = 'HKLM:\SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices'
$hidPrefix = 'BTHENUM\{00001124-0000-1000-8000-00805F9B34FB}_VID&0001004C_PID&029C'

# Fn bit (0xFF01/0x03) + the usage page of the constant padding after it + Lock (Consumer 0x019E)
$orig = [byte[]](0x06,0x01,0xFF,0x09,0x03,0x81,0x02,0x05,0x0C,0x09,0x00,0x95,0x01,0x75,0x01,0x81,0x01,0x0A,0x9E,0x01)
$new  = [byte[]](0x06,0x07,0x00,0x09,0x73,0x81,0x02,0x05,0x07,0x09,0x00,0x95,0x01,0x75,0x01,0x81,0x01,0x0A,0x72,0x00)

function Find-Bytes([byte[]]$hay, [byte[]]$needle) {
    for ($i = 0; $i -le $hay.Length - $needle.Length; $i++) {
        $ok = $true
        for ($j = 0; $j -lt $needle.Length; $j++) { if ($hay[$i + $j] -ne $needle[$j]) { $ok = $false; break } }
        if ($ok) { return $i }
    }
    return -1
}

function Restart-Keyboard {
    $dev = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "$hidPrefix*" -and $_.Class -eq 'HIDClass' } | Select-Object -First 1
    if (-not $dev) { Write-Host "The keyboard is not connected right now, the change applies on the next connection." -ForegroundColor Yellow; return }
    # A Bluetooth HID device cannot be disabled (Disable-PnpDevice: "Not supported"), but it can be restarted.
    Write-Host "Restarting the keyboard (it will not type for a few seconds)..."
    $out = pnputil.exe /restart-device "$($dev.InstanceId)" 2>&1 | Out-String
    Write-Host $out.Trim()
    if ($LASTEXITCODE -ne 0) {
        Write-Host "The restart failed. Turn Bluetooth off and on (Win+A), or restart the PC." -ForegroundColor Yellow
    }
}

try {
    $devs = @(Get-ChildItem $devRoot | Where-Object {
        $p = Get-ItemProperty $_.PSPath
        $p.VID -eq 0x4C -and $p.PID -eq 0x29C
    })
    if (-not $devs) { throw "No paired Magic Keyboard (VID 0x004C, PID 0x029C) found in the registry." }

    foreach ($d in $devs) {
        $mac = $d.PSChildName
        $backup = Join-Path $here "sdp_backup_$mac.reg"

        if ($Restore) {
            if (-not (Test-Path $backup)) { throw "No backup found: $backup. Remove the keyboard in Bluetooth settings and pair it again, that also restores the original." }
            reg.exe import "$backup" | Out-Null
            Write-Host "Restored from the backup: $backup" -ForegroundColor Green
            continue
        }

        if (-not (Test-Path $backup)) {
            # Only back up the ORIGINAL descriptor: if the cache is already patched
            # (e.g. the backup file was lost), a backup now would not restore anything.
            $hasOriginal = $false
            foreach ($sub in 'CachedServices', 'DynamicCachedServices') {
                $key = Join-Path $d.PSPath $sub
                if (-not (Test-Path $key)) { continue }
                $item = Get-Item $key
                foreach ($vn in $item.GetValueNames()) {
                    $val = $item.GetValue($vn)
                    if ($val -is [byte[]] -and (Find-Bytes $val $orig) -ge 0) { $hasOriginal = $true }
                }
            }
            if ($hasOriginal) {
                reg.exe export $d.Name "$backup" /y | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "Could not save the backup: $backup" }
                Write-Host "Backup saved: $backup"
            } else {
                Write-Host "No backup made: the descriptor is already patched (no original to save)." -ForegroundColor Yellow
                Write-Host "To undo the patch without a backup: remove the keyboard in Bluetooth settings and pair it again." -ForegroundColor Yellow
            }
        }

        $patched = 0; $already = 0
        foreach ($sub in 'CachedServices', 'DynamicCachedServices') {
            $key = Join-Path $d.PSPath $sub
            if (-not (Test-Path $key)) { continue }
            $item = Get-Item $key
            foreach ($vn in $item.GetValueNames()) {
                $val = $item.GetValue($vn)
                if ($val -isnot [byte[]]) { continue }
                $i = Find-Bytes $val $orig
                if ($i -ge 0) {
                    [Array]::Copy($new, 0, $val, $i, $new.Length)
                    Set-ItemProperty -Path $key -Name $vn -Value $val -Type Binary
                    $patched++
                } elseif ((Find-Bytes $val $new) -ge 0) {
                    $already++
                }
            }
        }
        Write-Host "[$mac] records patched: $patched, already patched: $already" -ForegroundColor Green
        if ($patched -eq 0 -and $already -eq 0) { throw "The expected descriptor bytes were not found, nothing was changed." }
    }

    Restart-Keyboard
    Write-Host ""
    Write-Host "Done. If the Fn / Lock keys still do not work, restart the PC (the Bluetooth stack reads the cache at startup)." -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
Read-Host "Press Enter to close"
