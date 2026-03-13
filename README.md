# 🔀 SwiGi

**Přepni klávesnici. Myš následuje. Hotovo.**

SwiGi synchronizuje Easy-Switch mezi Logitech klávesnicí a myší přes Bluetooth — bez receiveru, bez Logi Options+, bez nutnosti být na stejné síti.

Stiskneš Easy-Switch na klávesnici → myš se automaticky přepne na stejný počítač.

> *Děláno pro lidi. Užij si to a nebuď otrok tlačítek.* ✌️

---

**Switch your keyboard. Mouse follows. Done.**

SwiGi syncs Easy-Switch between Logitech keyboard and mouse over Bluetooth — no receiver, no Logi Options+, no same-network requirement.

Press Easy-Switch on keyboard → mouse automatically switches to the same host.

> *Made for people. Enjoy it and stop being a slave to buttons.* ✌️

---

## 🇨🇿 Česky

### Proč?

Logitech od roku 2019 tvrdí, že synchronizované přepínání klávesnice a myši "nejde" bez Flow (a Flow vyžaduje stejnou síť). Tisíce lidí to na fórech prosí. Tak tady to je.

### Co potřebuješ

- Logitech klávesnice + myš s Easy-Switch a Bluetooth (MX řada, Ergo řada, aj.)
- Python 3.10+ (nebo portable build bez Pythonu)
- hidapi knihovna

### Rychlý start

**macOS:**
```bash
brew install hidapi
python3 swigi.py
```

**Windows:**
1. Stáhni `hidapi.dll` z [github.com/libusb/hidapi/releases](https://github.com/libusb/hidapi/releases) → Assets → `hidapi-win.zip` → `x64/hidapi.dll`
2. Dej `hidapi.dll` do stejné složky jako `swigi.py`
```
python swigi.py
```

**Linux:**
```bash
sudo apt install libhidapi-hidraw0
python3 swigi.py
```

### Portable (bez instalace Pythonu)

#### macOS
```bash
brew install hidapi pyinstaller
./build_mac.sh
# Výstup: dist/SwiGi/ — zkopíruj kamkoli
```

#### Windows (bez admin práv)
1. Stáhni [Python embeddable](https://www.python.org/downloads/windows/) (ZIP, ne instalátor) → rozbal do `python-3/`
2. Stáhni `hidapi.dll` (viz výše)
3. Dej `swigi.py`, `hidapi.dll`, `python-3/`, `setup_swigi.bat` do jedné složky
4. Spusť `setup_swigi.bat`

### Autostart

#### macOS (launchd)
```bash
cat > ~/Library/LaunchAgents/com.swigi.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.swigi</string>
    <key>ProgramArguments</key>
    <array>
        <string>CESTA/K/dist/SwiGi/SwiGi</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>CESTA/K/swigi.log</string>
    <key>StandardErrorPath</key>
    <string>CESTA/K/swigi.log</string>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.swigi.plist
```

#### Windows (Startup)
1. `Win+R` → `shell:startup`
2. Nový zástupce → `CESTA\python\pythonw.exe CESTA\swigi.py`
3. Běží na pozadí, žádné okno

#### Linux (systemd)
```bash
cat > ~/.config/systemd/user/swigi.service << 'EOF'
[Unit]
Description=SwiGi

[Service]
ExecStart=/cesta/k/python3 /cesta/k/swigi.py
Restart=always

[Install]
WantedBy=default.target
EOF
systemctl --user enable --now swigi
```

### Oprávnění

- **macOS:** Nastavení → Soukromí a zabezpečení → Sledování vstupu → povol Terminal / SwiGi
- **Windows:** Může vyžadovat potvrzení přístupu k HID (první spuštění)
- **Linux:** Udev pravidlo:
  ```bash
  echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/42-logitech-hid.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

### Jak to funguje

1. Daemon periodicky posílá HID++ ping na klávesnici (každých ~250ms)
2. Klávesnice při stisku Easy-Switch pošle CHANGE_HOST notifikaci
3. Daemon ji zachytí a pošle stejný příkaz myši
4. Oba se přepnou na stejný host

Využívá HID++ 2.0 protokol (feature CHANGE_HOST `0x1814`). Jeden Python soubor, žádné externí závislosti kromě hidapi.

### Testováno

| Zařízení | OS | Připojení |
|----------|-----|-----------|
| MX Keys S + MX Vertical | macOS (Sequoia) | Bluetooth |
| MX Keys S + MX Vertical | Windows 11 | Bluetooth |

Mělo by fungovat s libovolnou kombinací Logitech zařízení s HID++ 2.0 a CHANGE_HOST.

---

## 🇬🇧 English

### Why?

Since 2019, Logitech has been saying that synchronized keyboard-mouse switching "can't be done" without Flow (which requires the same network). Thousands of people have been begging for it on forums. Well, here it is.

### Requirements

- Logitech keyboard + mouse with Easy-Switch and Bluetooth (MX series, Ergo series, etc.)
- Python 3.10+ (or portable build without Python)
- hidapi library

### Quick Start

**macOS:**
```bash
brew install hidapi
python3 swigi.py
```

**Windows:**
1. Download `hidapi.dll` from [github.com/libusb/hidapi/releases](https://github.com/libusb/hidapi/releases) → Assets → `hidapi-win.zip` → `x64/hidapi.dll`
2. Place `hidapi.dll` next to `swigi.py`
```
python swigi.py
```

**Linux:**
```bash
sudo apt install libhidapi-hidraw0
python3 swigi.py
```

### Portable (no Python installation needed)

#### macOS
```bash
brew install hidapi pyinstaller
./build_mac.sh
# Output: dist/SwiGi/ — copy anywhere
```

#### Windows (no admin rights needed)
1. Download [Python embeddable](https://www.python.org/downloads/windows/) (ZIP, not installer) → extract to `python-3/`
2. Download `hidapi.dll` (see above)
3. Put `swigi.py`, `hidapi.dll`, `python-3/`, `setup_swigi.bat` in one folder
4. Run `setup_swigi.bat`

### Autostart

#### macOS (launchd)
```bash
cat > ~/Library/LaunchAgents/com.swigi.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.swigi</string>
    <key>ProgramArguments</key>
    <array>
        <string>PATH/TO/dist/SwiGi/SwiGi</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>PATH/TO/swigi.log</string>
    <key>StandardErrorPath</key>
    <string>PATH/TO/swigi.log</string>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.swigi.plist
```

#### Windows (Startup folder)
1. `Win+R` → `shell:startup`
2. New shortcut → `PATH\python\pythonw.exe PATH\swigi.py`
3. Runs in background, no window

#### Linux (systemd)
```bash
cat > ~/.config/systemd/user/swigi.service << 'EOF'
[Unit]
Description=SwiGi

[Service]
ExecStart=/path/to/python3 /path/to/swigi.py
Restart=always

[Install]
WantedBy=default.target
EOF
systemctl --user enable --now swigi
```

### Permissions

- **macOS:** Settings → Privacy & Security → Input Monitoring → allow Terminal / SwiGi
- **Windows:** May require HID access confirmation on first run
- **Linux:** Udev rule:
  ```bash
  echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/42-logitech-hid.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

### How It Works

1. Daemon periodically sends HID++ ping to keyboard (~250ms interval)
2. Keyboard sends CHANGE_HOST notification when Easy-Switch is pressed
3. Daemon catches it and sends the same command to the mouse
4. Both switch to the same host

Uses HID++ 2.0 protocol (CHANGE_HOST feature `0x1814`). Single Python file, no external dependencies besides hidapi.

### Tested

| Device | OS | Connection |
|--------|-----|------------|
| MX Keys S + MX Vertical | macOS (Sequoia) | Bluetooth |
| MX Keys S + MX Vertical | Windows 11 | Bluetooth |

Should work with any Logitech device combo that supports HID++ 2.0 and CHANGE_HOST.

---

## 🤝 Podpora / Support

Pokud ti SwiGi ušetří čas a nervy:

If SwiGi saves you time and frustration:

<a href="https://www.buymeacoffee.com/TVUJ_UCET" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a>

---

## 📜 Licence

MIT — dělej si s tím co chceš.

## 🙏 Poděkování / Credits

Inspirováno projektem [CleverSwitch](https://github.com/MikalaiBarysevich/CleverSwitch) od MikalaiBarysevich a protokolovou dokumentací z [Solaar](https://github.com/pwr-Solaar/Solaar).
