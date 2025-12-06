# 📖 User Manual - Easyplus Apex (Unofficial)

Welcome to the user guide. This document will guide you through the initial setup, naming your devices, and configuring your shutters.

---

## 1. Initial Setup & Connection

Once the integration is installed via HACS or manually, follow these steps to connect your system.

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **Easyplus Apex (Unofficial)**.
3.  Enter your Controller details:
    * **IP Address** (e.g., `192.168.1.***`)
    * **Port** (Default: `2024`)
    * **Password**
4.  Click **Submit**.

> **Success!** Your system is now connected. All relays (switches) and dimmers (lights) will appear in Home Assistant automatically.

---

## 2. Naming Your Devices (Relays & Dimmers)

Because the Apex controller broadcasts technical addresses (e.g., `ID 1`, `ID 2`) instead of room names, your entities will initially appear with generic names like `switch.apex_relay_1`.

### 🏷️ How to rename your devices efficiently:

1.  Open the **Easyplus Apex** integration page in Home Assistant (Settings > Devices & Services).
2.  Click on **1 Device** to see the list of entities.
3.  **Physically walk to a room** and turn on a light using the wall switch.
4.  Watch your screen: one of the switches in the list will instantly jump to **"On"**.
5.  Click on that entity, select the **Settings (cogwheel)** icon.
6.  Rename it (e.g., to *"Kitchen Light"*). Home Assistant will now remember this name forever.

> **💡 Tip:** Do this room by room. It's the fastest and most reliable way to map your home.

---

## 3. Configuring Shutters & Blinds (Covers)

This integration features a unique **"Discovery by Use"** wizard. You do **not** need to look up relay numbers or technical documentation to set up your blinds.

### 🪄 The Wizard Steps:

1.  Go to **Settings** > **Devices & Services** > **Easyplus Apex**.
2.  Click the **Configure** button.
3.  Select **"Detect Cover (Wizard)"** and click Next.
4.  **Follow the on-screen instructions:**
    * Click "Submit" in Home Assistant.
    * **Immediately** walk to your physical wall switch for the shutter.
    * Press **Open** briefly (you must hear the relay click).
    * Press **Close** briefly.
    * *The system listens for 10 seconds for this activity.*
5.  **Result:**
    * The wizard will report: *"Cover Found! Activity detected on relays X and Y."*
    * Enter a name (e.g., *"Living Room Blind"*).
    * Enter the total **travel time** (in seconds) for accurate positioning percentages.
    * Click **Submit**.

Your shutter is now available as a Cover entity in Home Assistant! 🪟

### Manual Configuration (Advanced)
If the wizard does not detect your cover (e.g. during remote configuration), you can add covers manually via the same **Configure** menu by selecting "Manually Add Cover" and entering the relay IDs yourself.

---

## ❓ Troubleshooting

| Issue | Possible Cause | Solution |
| :--- | :--- | :--- |
| **Connection Failed** | Network Isolation | Check if your router has "Client Isolation" enabled. HA and Apex must be able to "see" each other. |
| **Entities Unavailable** | Connection Lost | Check if the Apex controller has power. Reload the integration. |
| **Wizard Fails** | Timing | Make sure to operate the physical switch *while* the spinner is showing in HA. You have a 10-second window. |

---

*Developed with ❤️ by Core Automations.*
