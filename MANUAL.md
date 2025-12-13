# 📘 User Manual - Easyplus Apex (Unofficial)

![Banner](https://capsule-render.vercel.app/api?type=waving&color=00a1f1&height=200&section=header&text=User%20Manual&fontSize=70&animation=fadeIn&fontAlignY=35&desc=Installation%20&%20Configuration%20Guide&descAlignY=55&descAlign=50)

> [!TIP]
> **Quick Start:** Most users should choose **Method A (XML Import)** for the fastest and cleanest setup.

---

## 1. Initial Connection 🔌

First, we need to establish a link between Home Assistant and your Controller.

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for `Easyplus Apex`.
3.  Enter your credentials:

| Field | Value |
| :--- | :--- |
| **IP Address** | Your local IP (e.g., `192.168.1.xxx`) |
| **Port** | `2024` (Default) |
| **Password** | Your User or Admin password |

---

## 2. Configuration Methods ⚙️

You will be presented with a choice. Choose the path that fits your situation.

### 🏆 Method A: Smart XML Import (Recommended)
*Best for: Clean installations, correct naming, automatic shutter detection.*

> [!NOTE]
> This method uses your original `config.xml` file to filter out unused "junk" relays and apply your custom room names instantly.

**Step-by-Step:**

1.  **Export:** Open the **Easyplus PC Software** -> Go to **GUI/Apps** -> Click **Get EasyLink Configuration**.
2.  **Copy:** Open the saved `.xml` file in Notepad. Press `Ctrl+A` (Select All) and `Ctrl+C` (Copy).
3.  **Paste:** In Home Assistant, select **Import XML File** and paste the content.
4.  **Done:** The integration will restart with your full configuration loaded.

### 🧭 Method B: Auto-Discovery
*Best for: Users without access to the original configuration file.*

1.  Select **Auto-Discovery** during setup.
2.  The system starts **empty** to keep it clean.
3.  **Discovery by Use:** Walk to a room, press a physical switch, and the device will appear in Home Assistant instantly.
4.  **Rename:** Click on the new entity to give it a friendly name.

---

## 3. Managing Shutters (Covers) 🪟

Easyplus shutters are complex, but this integration makes them easy to manage.

### ✏️ Edit Cover (Direction & Time)
Is your shutter moving **UP** when you press **DOWN**? Or does the progress bar not match reality?

> [!WARNING]
> Do not delete the shutter! Use the built-in edit tool instead.

1.  Go to **Settings** > **Devices** > **Easyplus Apex** > **Configure**.
2.  Select the option: **"Edit Cover (Direction/Time)"**.
3.  Select the shutter you want to fix.
4.  Adjust the settings:
    * ✅ **Invert Direction:** Check this to flip Up/Down controls.
    * ⏱️ **Travel Time:** Enter the time (in seconds) it takes to fully open.
5.  Click **Submit**.

### 🪄 The Wizard (Add New)
If you installed a new motor that isn't in your XML file yet:
1.  Go to **Configure** -> Select **"Detect Cover (Wizard)"**.
2.  Click Submit.
3.  **Immediately** press the physical wall switch (Open, then Close).
4.  The system detects the relays and creates the entity for you.

---

## ❓ Troubleshooting

Having issues? Check the solutions below.

| Problem | Possible Cause | Solution |
| :--- | :--- | :--- |
| **"Re +0" Names** | Missing name in Apex | The shutter has no name in the original software. Rename it manually in Home Assistant settings. |
| **Missing Entities** | Strict Filtering | When using XML Import, devices without a name (or default names like "relay 85") are ignored to keep the list clean. |
| **Grayed Out** | Connection Loss | Check if the Apex Controller is powered on and connected to the network. Reload the integration. |
| **Wrong Direction** | Wiring | Use the **Edit Cover** tool in the configuration menu to invert the direction software-side. |

> [!IMPORTANT]
> **Restoring Missing Items:** If you accidentally deleted devices, simply go to **Configure** > **Import XML Config** and paste your XML file again. This restores everything without losing your custom settings.

---

<div align="center">

*Unofficial Integration developed by Core Automations* [Report an Issue](https://github.com/Livyon/ha-easyplus-apex/issues)

</div>
