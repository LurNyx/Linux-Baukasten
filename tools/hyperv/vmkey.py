"""Tastendruck an eine Hyper-V-VM senden (WMI Msvm_Keyboard.TypeKey). Administrator noetig."""
import subprocess

PS = r"""
$ErrorActionPreference = 'Stop'
$ns = 'root\virtualization\v2'
$vm = Get-CimInstance -Namespace $ns -ClassName Msvm_ComputerSystem -Filter "ElementName='@VM@'"
$kb = Get-CimAssociatedInstance -InputObject $vm -ResultClassName Msvm_Keyboard | Select-Object -First 1
$r = Invoke-CimMethod -InputObject $kb -MethodName TypeKey -Arguments @{keyCode=[uint32]@KEY@}
"rc=" + $r.ReturnValue
"""


def press(vm_name: str, vk: int = 13) -> str:
    """vk: Windows-Virtual-Key-Code (13 = Enter)."""
    script = PS.replace("@VM@", vm_name).replace("@KEY@", str(vk))
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:300])
    return r.stdout.decode("utf-8", "replace").strip()
