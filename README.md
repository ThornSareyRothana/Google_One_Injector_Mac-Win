# Google One Subscription Injector — Windows & macOS

A Python and Frida tool that requests the offers configured in [frida.js](frida.js) and opens Google Play checkout inside Google One on a rooted Android device or emulator.

**Windows:** use `run.bat` or the Python commands below. **macOS:** set up the Python environment first, then use `run.command` or Terminal.

> [!IMPORTANT]
> Opening checkout does **not** activate a subscription. The tool does not press **Subscribe**, approve payment, or create a successful purchase receipt. Google Play determines eligibility and payment acceptance. Menu names, prices, storage amounts, and free periods are saved labels; verify the actual account and terms in checkout before confirming anything yourself.

## Contents

- [Requirements](#requirements)
- [Prepare Android](#prepare-android)
- [Windows setup](#windows-setup)
- [macOS setup](#macos-setup)
- [Using the menu](#using-the-menu)
- [Command-line options](#command-line-options)
- [Troubleshooting](#troubleshooting)
- [Project files](#project-files)

## Requirements

| Requirement | Details |
| --- | --- |
| Host computer | Windows or macOS. macOS operation has been checked on Apple Silicon with MuMuPlayer. Other combinations depend on emulator compatibility. |
| Python | Python 3.12 is recommended for the commands below. |
| Android | A rooted Android device or emulator with ADB access. Android root access is required. |
| Google apps | Google Play Store, Google Play services, and Google One installed inside Android. |
| Google account | Signed in and able to use the Play Store. The script lists accounts on the device; it does not choose the billing account. |
| Internet | Required for Python packages, Frida downloads when necessary, and Google Play. |

Pinned dependencies in [requirements.txt](requirements.txt):

~~~text
frida==17.9.1
frida-tools==14.8.1
~~~

The Android Frida server must match the host version. Startup checks the Android CPU architecture and prepares the matching server. Compressed ARM64 and x86-64 archives are included as fallbacks.

## Prepare Android

1. Start your emulator and wait for Android to boot, or connect a rooted phone with USB debugging enabled.
2. Make sure Android root access is available. The script supports an ADB shell already running as root, `su -c`, and `su 0`.
3. Open the Play Store, select the intended Google account, and finish any sign-in or verification prompts.
4. Install **Google One by Google LLC** from the Play Store. Open it once and select the intended account there too.
5. Find the emulator instance's **ADB port**. In MuMu for Mac, look for **Open ADB** under **Developer**; older versions place it under **Tools**. See [MuMu's developer guide](https://www.mumuplayer.com/help/mac/developer-support-function.html).

Examples use `127.0.0.1:5555`. **Replace `5555` with your instance's actual port.** Each instance can use a different port.

## Windows setup

### 1. Get the project and Python

Download **Code → Download ZIP** from this repository and extract it, or clone it if Git is installed:

~~~powershell
git clone https://github.com/ThornSareyRothana/Google_One_Injector_Mac-Win.git
cd Google_One_Injector_Mac-Win
~~~

Install [Python 3.12 for Windows](https://www.python.org/downloads/windows/), including the Python launcher. Enable **Add Python to PATH** during installation. Open a new PowerShell window inside the project folder containing `main.py`.

### 2. Install ADB

Download [Android SDK Platform-Tools for Windows](https://developer.android.com/tools/releases/platform-tools), extract it, and add its `platform-tools` folder to your `PATH`.

For example, if ADB is at `C:\Android\platform-tools\adb.exe`, this makes it available in the current PowerShell window:

~~~powershell
$env:Path = "C:\Android\platform-tools;$env:Path"
adb version
~~~

The script also attempts to download Windows Platform-Tools into `bin` when ADB is missing. Installing ADB on `PATH` makes the diagnostic commands below available directly.

### 3. Create the Python environment

Run from the project folder:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

These commands use the environment directly; PowerShell activation is not required.

### 4. Connect Android and launch

~~~powershell
adb connect 127.0.0.1:5555
adb devices -l
.\.venv\Scripts\python.exe main.py --serial 127.0.0.1:5555
~~~

For a USB-connected phone, skip `adb connect` and use the serial shown by `adb devices -l`.

### Windows batch launcher

You can also double-click **run.bat**, or run:

~~~powershell
.\run.bat
~~~

The batch launcher uses `python` from `PATH` and attempts to install the pinned dependencies. If Python is missing, it may attempt installation through `winget`. It does **not** automatically select the `.venv` above; use the explicit virtual-environment command when you want that interpreter.

## macOS setup

### 1. Install Python and native macOS ADB

Install [Homebrew](https://brew.sh/) if needed, then open Terminal:

~~~bash
brew install python@3.12
brew install --cask android-platform-tools
python3.12 --version
adb version
~~~

Package references: [Python 3.12](https://formulae.brew.sh/formula/python%403.12) and [Android Platform-Tools](https://formulae.brew.sh/cask/android-platform-tools).

If `brew` is not found after installation, follow the **Next steps** printed by Homebrew's installer and reopen Terminal.

> [!NOTE]
> Install native macOS ADB before launching. The current automatic ADB download and extra emulator path searches target Windows. They do not install macOS ADB. `run.bat` is a Windows launcher.

### 2. Get the project

Download and extract **Code → Download ZIP**, or use Git:

~~~bash
git clone https://github.com/ThornSareyRothana/Google_One_Injector_Mac-Win.git
cd Google_One_Injector_Mac-Win
~~~

If using a ZIP, open Terminal in the extracted folder instead. Run the following commands from the folder containing `main.py`.

### 3. Create the Python environment

~~~bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
chmod +x run.command
~~~

### 4. Connect MuMu and launch

With Android running and its ADB port identified:

~~~bash
adb connect 127.0.0.1:5555
adb devices -l
.venv/bin/python main.py --serial 127.0.0.1:5555
~~~

After setup, double-click **run.command** in Finder, or run:

~~~bash
./run.command
~~~

The launcher uses `.venv/bin/python` inside this project and adds the usual Homebrew binary folders to its `PATH`. It does not create the environment or install dependencies.

## Using the menu

Startup selects an ADB device, checks root access and Google One, prepares the embedded billing module and Frida server, restarts Google One, and attaches Frida. It may replace a device's existing Frida server to match the host version.

When ready, the terminal displays the offers and an `Enter choice >` prompt:

| Input | Action |
| --- | --- |
| `1`–`28` or a plan ID | Request the configured offer and attempt to open checkout. |
| `s` | Toggle existing-subscription replacement mode. |
| `a` | Choose an optional YouTube add-on. |
| `r` or `g` | Restart Google One and reattach Frida. |
| `e` | Repeat environment checks. |
| `l` | Redisplay the menu. |
| `q` | Quit and detach. |

Current groups are Plus, Pro, Ultra 5x, and Ultra 20x; the Plus section also includes YouTube add-on entries. See [frida.js](frida.js) for the complete configured plan IDs. A listed plan is not a guarantee that Google Play will offer it to your account.

In checkout, verify the billing email, product, amount due, introductory period, renewal date, and payment method. Confirm the subscription yourself only if the displayed terms are what you intend to accept. **A checkout-launch message is not proof of a successful subscription.**

## Command-line options

Use the executable for your platform:

| Platform | Command prefix |
| --- | --- |
| Windows PowerShell | `.\.venv\Scripts\python.exe main.py` |
| macOS Terminal | `.venv/bin/python main.py` |

Append options as needed:

| Option | Meaning |
| --- | --- |
| `--serial SERIAL` or `-s SERIAL` | Prefer a serial from `adb devices -l`. If it is offline, the current script may select another available device. |
| `--plan ID_OR_NUMBER` | Request a plan directly, skipping the menu. |
| `--addon ID` | Set an optional add-on plan ID. |
| `--stack` or `--renew` | Request replacement mode `5` (`CHARGE_FULL_PRICE`) for an existing subscription. This can involve an immediate full-price charge; extra free time or an extension is not guaranteed. |
| `--wait SECONDS` | Keep a direct-command session alive after the request; defaults to 8 seconds. This does not confirm payment. |
| `--help` | Display command-line help. |

Example requesting the configured `pro_12m` offer:

**Windows:**

~~~powershell
.\.venv\Scripts\python.exe main.py --serial 127.0.0.1:5555 --plan pro_12m --wait 30
~~~

**macOS:**

~~~bash
.venv/bin/python main.py --serial 127.0.0.1:5555 --plan pro_12m --wait 30
~~~

Currently, `pro_12m` is menu option **13**. Check eligibility and actual terms in Google Play.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| ADB not found on Mac | Install native macOS Platform-Tools and confirm `adb version` works. Automatic ADB download is Windows-only. |
| `Python environment missing` from the Mac launcher | Run the macOS environment creation and dependency installation commands above. |
| No ADB device found | Wait for Android to boot, confirm the instance's actual port, reconnect, and run `adb devices -l`. |
| Device is offline or unauthorized | Reconnect the emulator, or approve USB debugging on the physical phone. |
| Multiple devices connected | Close unrelated instances and verify the serial. Automatic fallback may select a different device if the requested one is unavailable. |
| Root check or Frida startup fails | Test `adb -s SERIAL shell id`. For a rooted ADB shell it should report `uid=0`; otherwise test `adb -s SERIAL shell su -c id` or `adb -s SERIAL shell su 0 id`. Replace `SERIAL` with your device serial. |
| Google One missing | Install the official app from the Play Store inside Android and open it once. |
| `no_offer` or zero products | Google Play returned no matching configured offer. A menu entry does not establish availability. |
| Already subscribed | Check the billing account and existing subscription in Google Play. Adding an account to Android does not prove checkout changed accounts. |
| Account disabled or authentication required | Complete Google's sign-in or [account recovery](https://accounts.google.com/signin/recovery) process. This script cannot restore a disabled account. |
| Payment declined | Check the card issuer's decline information or contact Google Play support. Reopening checkout does not resolve a payment decline. |
| Frida mismatch or download failure | Use the pinned requirements, check internet access to GitHub, and confirm the Android server matches the host version and device architecture. |

Useful checks after ADB is on your `PATH`:

~~~text
adb version
adb devices -l
adb -s SERIAL shell getprop ro.product.cpu.abi
adb -s SERIAL shell pm path com.google.android.apps.subscriptions.red
~~~

The script's printed account list is a device inventory, **not confirmation of the active billing account**.

## Project files

| File | Purpose |
| --- | --- |
| `main.py` | CLI, Android checks, Frida setup, and session management. |
| `frida.js` | Instrumentation and configured offers. |
| `module_b64.py` | Embedded Android billing module pushed to the device. |
| `requirements.txt` | Pinned Python dependencies. |
| `run.bat` | Windows launcher. |
| `run.command` | macOS launcher for the project virtual environment. |
| `assets/*.xz` | Compressed Frida server archives. |
| `.gitignore` | Excludes environments, caches, backups, downloaded ADB, and extracted servers. |

Create a separate `.venv` on each computer. Keep compressed archives in Git; extracted servers and installed Python packages remain local.
