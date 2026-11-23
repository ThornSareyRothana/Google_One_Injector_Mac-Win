# Google One Subscription Injector

Inject custom subscription offers and intro plans directly into Google One on a rooted Android device/emulator, bringing up the official Google Play checkout sheet.

> [!NOTE]
> **Does NOT auto-confirm payment.** The official Google Play checkout sheet is displayed on your device screen for you to review and confirm manually.

---

## Prerequisites

1. **Rooted Android device or emulator** (e.g. MuMu Player, LDPlayer, Nox, or rooted physical phone).
2. **Google account** already logged in on the device.
3. **Google One app** installed from the Play Store.

`frida-server`, `module_521.apk`, and `adb` connectivity are managed automatically by the script.

---

## Quick Start

### Option 1: Double-click or run `run.bat`
```bat
run.bat
```

### Option 2: Python Command
```powershell
python -m pip install -r requirements.txt
python main.py
```

### Direct CLI Shortcuts (Skip Menu)
```powershell
# Launch checkout directly with plan name or menu index:
python main.py --plan 1
python main.py --plan helium_1m

# Stack / Renew onto existing Google One subscription:
python main.py --stack --plan pro_6m

# With YouTube Premium add-on:
python main.py --plan pro_12m --addon yt_1m
```

---

## Interactive Menu Commands

When running without arguments, an interactive menu will appear:

| Key | Description |
|---|---|
| **1 - 28** | Select plan by number or plan ID to trigger checkout |
| **`s`** | Toggle **Stack / Renew mode** (stacks onto active subscription) |
| **`a`** | Choose optional YouTube Premium add-on |
| **`r`** or **`g`** | Restart Google One app & re-attach Frida |
| **`e`** | Re-run environment verification |
| **`l`** | Refresh / re-display menu |
| **`q`** | Quit |

---

## Purchase Modes

- **New Purchase (`STACK=false`)**: Default mode. Launches checkout as a clean, new subscription.
- **Stack / Renew (`STACK=true`)**: Stacks the new plan onto your existing Google One subscription (`ReplacementMode = 5 CHARGE_FULL_PRICE`). Requires the account to currently have an active plan.
