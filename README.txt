# Wi-Fi Control for Linux Mint

A lightweight Tkinter GUI for NetworkManager. Features:
- Wi-Fi radio ON/OFF
- Adapter and managed/unmanaged status
- Scan nearby networks and view signal/security
- Connect to a selected network (password prompt for secured networks)
- Disconnect the current Wi-Fi device
- Try to mark the Wi-Fi adapter as managed using a PolicyKit authentication prompt
- Periodic status refresh

## Requirements
Linux Mint / Ubuntu with:
- Python 3
- `python3-tk`
- NetworkManager (`nmcli`)
- `pkexec` for the graphical administrator action (optional)

Install missing dependencies:
```bash
sudo apt update
sudo apt install python3-tk network-manager pkexec
```

## Install
Keep `wifi_control.py`, `wifi-control.png`, and `install.sh` in the same directory, then:
```bash
chmod +x install.sh
./install.sh
```
Search the Mint application menu for **Wi-Fi Control**, or run:
```bash
~/.local/bin/wifi-control
```

The installer is user-local and does not need sudo. It does not change NetworkManager configuration. The “Fix unmanaged adapter” button asks for admin permission and runs `nmcli device set <adapter> managed yes`.

## Uninstall
From the same folder:
```bash
./uninstall.sh
```
Or remove these user-level files:
- `~/.local/share/wifi-control/`
- `~/.local/bin/wifi-control`
- `~/.local/share/applications/wifi-control.desktop`
- `~/.local/share/icons/hicolor/256x256/apps/wifi-control.png`

The app uses `nmcli` for network actions. Connecting to a secured network requires entering its password in the GUI.
