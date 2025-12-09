# 📖 User Manual - Easyplus Apex (Unofficial)

Welcome to the user guide. This integration allows you to choose between a **Smart XML Import** (recommended) or **Manual Auto-Discovery**.

---

## 1. Initial Setup & Connection

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **Easyplus Apex (Unofficial)**.
3.  Enter your Controller details:
    * **IP Address** (e.g., `192.168.1.***`)
    * **Port** (Default: `2024`)
    * **Password**
4.  Click **Submit**.

You will now be presented with a **Configuration Method** menu.

---

## 2. Method A: Import XML File (Recommended) 🏆

This is the cleanest and fastest way. It reads your original Apex configuration to determine names, device types (Dimmer vs Switch), and Shutters.

### 📤 Step 1: Get your XML
1.  Open the **Easyplus configuration software** on your PC.
2.  Go to the **GUI / Apps** tab.
3.  Click on **Get the EasyLink Configuration** (or Export XML).
4.  Open the saved `.xml` file with Notepad (or any text editor).
5.  **Select All** (Ctrl+A) and **Copy** (Ctrl+C).

### 📥 Step 2: Import in Home Assistant
1.  In the Home Assistant setup menu, select **Import XML File**.
2.  **Paste** the content of your XML file into the text box.
3.  Click **Submit**.

> **Result:** Home Assistant will restart the integration. 
> * ✅ Real room names (e.g., "Kitchen") are applied automatically.
> * ✅ Shutters are created automatically.
> * ✅ Unused/Generic relays (e.g., "relay 85") are **ignored** to keep your system clean.

### ⚠️ Note on Shutters & Direction
The XML import assumes standard wiring. If a shutter moves in the wrong direction (Up = Down):
1.  Go to **Configure** > **Remove Cover** and delete that specific shutter.
2.  Go to **Configure** > **Add Manually**.
3.  Re-add the shutter using the same ID, but check the **"Invert Direction"** box.
*(Alternatively: Swap the black and brown wires in your physical wall box for a permanent fix).*

---

## 3. Method B: Auto-Discovery (No XML)

Use this method only if you do not have the original configuration file.

1.  Select **Auto-Discovery** in the setup menu.
2.  The system will start empty.
3.  **Walk to a room** and press a physical button.
4.  The corresponding entity will appear in Home Assistant instantly as `switch.apex_relay_X`.
5.  Click on the entity > **Settings** (cogwheel) > **Rename** it manually (e.g., to "Living Room Light").

---

## 4. Managing Shutters (Covers)

If you didn't use XML Import, or added a new motor later, use the **Wizard**.

### 🪄 The Discovery Wizard:
1.  Go to **Settings** > **Devices & Services** > **Easyplus Apex** > **Configure**.
2.  Select **"Detect Cover (Wizard)"**.
3.  Click "Submit" and **IMMEDIATELY** walk to your wall switch.
4.  Press **Open** briefly, then press **Close** briefly.
5.  The wizard detects the relay usage and asks you to name the new shutter.

### 📝 Manual Add/Remove
You can always manually add or remove shutters via the **Configure** menu if you know the Relay IDs (e.g., Direction ID 90, Power ID 91).

---

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **"Re +0" Names** | If your shutters appear as "Re +0", this means they were not named in the original Apex software. You can simply rename them in Home Assistant (Settings > Rename). |
| **Missing Devices** | If using XML Import: Ensure the device has a name in the Apex software. Unnamed or "Junk" names are filtered out by default. |
| **Entities Unavailable** | Check if the Apex controller has power. Reload the integration. |
| **Wrong Direction** | See the "Note on Shutters & Direction" in section 2. |

---

*Developed with ❤️ by Core Automations.*
