# Ghost Protocol 👻

<div align="center">

**The automated guardian of your sanity.**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Install once. Forget forever.*

</div>

---

## ✨ Features

Ghost Protocol watches your project in the background and protects you from yourself.

- 🚫 **Auto-Ignore Heavy Assets:** Automatically adds large binaries/videos to `.gitignore` and `.cursorignore`.
- 🧹 **Smart Cleanup:** Removes ignored file paths from `.gitignore` when you delete the files from disk.
- 🛡️ **Commit Guard:** Blocks commits if you try to push giant source files (>500KB).
- 📊 **Live Dashboard:** Beautiful terminal UI showing project stats (tokens, file count, cost).
- 🚀 **Performance:** Uses a queue-based watcher with smart debouncing. Zero CPU impact.

---

## 🚀 Installation

### From PyPI (Recommended)
```bash
pip install ghost-protocol
```
From Source
Bash

```bash
git clone https://github.com/yourname/ghost-protocol.git
cd ghost-protocol
pip install -e .
```

## ⚡ Usage

### 1. Install Git Hook (One time)
This sets up the pre-commit check automatically.

Bash

```bash
ghost --install
```

### 2. Run Background Daemon (Daily driver)
Run this in a separate terminal (or minimize it). Ghost watches for file changes.

Bash

```bash
ghost --ghost
```

### 3. Open Monitor (Optional)
See your project stats in real-time.

Bash

```bash
ghost --monitor
```

## ⚙️ Configuration

Create a `ghost_config.json` in your project root to customize behavior.

JSON

```json
{
  "limits": {
    "max_asset_size_mb": 2.0,
    "max_code_size_mb": 1.0
  },
  "skip_dirs": ["my_secret_folder"]
}
```

## 🏗 Architecture

- **Config Manager:** Singleton pattern with thread-safe cached sets.
- **File Locking:** Cross-platform advisory locks (fcntl / msvcrt) to prevent race conditions.
- **Queue System:** Decoupled file watching (watchdog) from I/O operations using a thread-safe queue.
- **Atomic Writes:** All file modifications use temporary files + os.replace for data integrity.

## 📝 License

MIT License - see LICENSE file for details.

Made with 🧠 and a bit of 🍅.
