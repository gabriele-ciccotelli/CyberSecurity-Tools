# Key and Mouse Logger

> **Disclaimer:**  
> This script is intended strictly for **educational** and **ethical** purposes.  
> Unauthorized monitoring of computer activity is **illegal** and **unethical**.  
> Use only on systems for which you have **explicit written permission**.

---

## Description

A Python-based key and mouse logger that:

- Captures **keyboard events** (printable characters, special keys, and Ctrl+ combinations).
- Records **mouse events** (clicks and scrolls).
- Saves all events to a log file with **timestamps**.
- Offers an option to **group keystrokes** within a specified time interval for readability.
- Stops when **Ctrl + Esc** is pressed.

---

## Requirements

Ensure you have Python 3 installed, then run:

```bash
pip install pynput
```

> The other modules (`argparse`, `os`, `datetime`, `threading`) are part of the standard library.

---

## Usage

Run the script from the command line:

```bash
python keylogger.py [options]
```

### Available Options

| Flag              | Description                                                                   | Default           |
|-------------------|-------------------------------------------------------------------------------|-------------------|
| `-h`, `--help`    | Show this help message and exit                                               | —                 |
| `-o OUTPUT`       | Path to the log file (will default to `./log.txt` if none provided)           | `./log.txt`       |
| `-i INTERVAL`     | Time interval (in seconds) for grouping keystrokes (e.g. `0.5`)               | grouping disabled |

### Examples

- **Default logging, no grouping**:  
  ```bash
  python keylogger.py
  ```

- **Custom log path and 0.5 s grouping**:  
  ```bash
  python keylogger.py -o /path/to/custom_log.txt -i 0.5
  ```

---

## Features

- **Keyboard Logging**: detects printable and non-printable keys, including Ctrl+key combinations.  
- **Mouse Logging**: captures click coordinates and scroll events.  
- **Timestamps**: every event is recorded with date and time.  
- **Keystroke Grouping**: groups keystrokes within a given interval.  
- **Modifier Tracking**: logs release of Shift, Ctrl, and Alt keys.  
- **Custom Output**: specify a custom log file path.  
- **Safe Stop**: end logging with Ctrl + Esc.  
- **Thread-Safe**: uses locks to ensure safe concurrent logging across threads.

---

## How It Works

The logger uses two threads:

- **Keyboard listener**: detects key presses, releases, and combinations;  
- **Mouse listener**: detects clicks and scrolls.  

Events are logged with timestamps.  
The logger stops when **Ctrl + Esc** is pressed.

---

## Compatibility

- **Supported OS:** Microsoft Windows only.  
- Other operating systems are not tested and may require elevated privileges or unsupported hooks.

---

## Limitations & Ethics

- **Permissions:** may require administrator privileges on Windows.  
- **Performance:** constant monitoring may have a minimal impact on system resources.  
- **Ethical Use:** use only with explicit written authorization; comply with all applicable privacy laws.

---

## License

Distributed under the **MIT License**.  
See [LICENSE.md](../LICENSE.md) for details.

---

## Author

Developed by Gabriele Ciccotelli

- **GitHub:** [github.com/gabriele-ciccotelli](https://github.com/gabriele-ciccotelli)
- **LinkedIn:** [linkedin.com/gabriele-ciccotelli](https://www.linkedin.com/in/gabriele-ciccotelli/)