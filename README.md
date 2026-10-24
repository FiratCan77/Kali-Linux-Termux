<div align="center">

# 🐉 Kali-Xfce Localhost

**An Ultra-Lightweight, Single-File Browser-Based Kali Linux Desktop Environment Powered by Python & Vanilla Web Technologies.**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Android%20%7C%20Linux%20%7C%20PC-orange.svg)]()
[![Status](https://img.shields.io/badge/status-Active%20Development-success.svg)]()

*Say goodbye to bloated PRoot-Distro and heavy VNC setups. Run a full Kali XFCE-style desktop right inside your browser with zero dependencies!*

</div>

---

## 🚀 What is Kali-Xfce Localhost?

**Kali-Xfce Localhost** is an experimental, minimalist desktop environment designed for developers, hackers, and Linux enthusiasts who want a fully functional Kali Linux look-and-feel without the heavy overhead of traditional container solutions (like Docker, PRoot, or X11/VNC servers). 

Built entirely into a **single Python file (`kali.py`)**, it combines a powerful backend asynchronous command bridge with a sleek, responsive HTML5/JavaScript frontend. Whether you are running it locally on your PC or inside **Termux on Android**, it starts instantly and flies like the wind! ⚡

---

## ✨ Key Features

- **🎯 Zero Bloat / Single File:** No gigabytes of dependencies, no complex installation scripts. Just download `kali.py` and run.
- **💻 Real Terminal Bridge:** Fully interactive terminal connected to your host system via asynchronous Python threads (`/api/tail` streaming engine). Supports `apt`, `git`, python scripts, and custom shell commands.
- **📁 Advanced File Manager:** Browse directories, examine file sizes, rename files on the fly, and execute scripts (`.py`, `.sh`, `.cpp`, `.c`) directly with one click.
- **📝 Built-in Text Editor:** Integrated Notepad with file opening and saving capabilities.
- **🎨 Dynamic XFCE Theme & Wallpapers:** Comes with official Kali Purple themes, custom mouse cursor simulation, click ripples, and multiple wallpaper switchers.
- **📱 Mobile & PC Optimized:** Works flawlessly inside Android browsers via Termux (`localhost:8080`) without triggering Android's aggressive OOM process-killer.
- **🛠️ Pre-configured Tools Launcher:** Quick shortcuts for Metasploit, Nmap, ExploitDB, Hydra, and more.

---

## 📦 Quick Start

### Prerequisites
- Python 3.x installed on your system or Termux.

### Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/FiratCan77/Kali-Xfce-Localhost.git](https://github.com/FiratCan77/Kali-Run the script:Xfce-Localhost.git)
   cd Kali-Xfce-Localhost python3 kali.py
Open your browser:
Navigate to:http://localhost:8080 (If you are running this on Termux on your Android phone, just type the command above, open your phone browser, and enjoy your pocket Kali desktop!)
​⌨️ Built-in Applications & Tools ApplicationDescription
TerminalReal-time interactive shell with command history (Up/Down arrows).
FilesFile explorer with directory navigation, file running, and renaming support.
Text EditorLightweight code/text editor with save/load capabilities.
SettingsAppearance settings and dynamic wallpaper switcher.
PackagesQuick installer for C/C++ (clang), Python, and essential tools.
GoogleIntegrated web search utility.🏗️ Architecture & Tech Stack
​Backend: Python Standard Library (http.server, socketserver, subprocess, threading) — No external frameworks like Flask or Django required!
​Frontend: HTML5, CSS3 (Glassmorphism, Custom Grid, Flexbox), Vanilla JavaScript (Window Manager, Custom Cursor Engine).
​Environment: Designed specifically for lightweight Linux distros and Termux enviroments
​⚠️ Disclaimer
​This project is created for educational, development, and personal productivity purposes. Use it responsibly and ensure you have authorization before running system-level commands on target environments.
​👤 Creator
​Developed with ❤️ by Fırat Can (FiratCan77).
​📄 License
​Distributed under the MIT License. See LICENSE for more information.


