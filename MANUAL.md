# User Manual - Easyplus Apex (Unofficial)

Welcome to the user guide for the Easyplus Apex integration. This guide helps you set up your system after installation.

## 1. Initial Setup

1.  Go to **Settings** > **Devices & Services** in Home Assistant.
2.  Click **Add Integration** and search for **Easyplus Apex (Unofficial)**.
3.  Enter your Controller details:
    * **IP Address** (e.g., 192.168.1.***)
    * **Port** (Default: 2024)
    * **Password**
4.  Click **Submit**.

🎉 **Success!** All your relays (lights/switches) and dimmers are now immediately available in Home Assistant.

---

## 2. Naming Your Devices (Relays & Dimmers)

Because the Apex controller broadcasts technical addresses (e.g., ID 1, ID 2) instead of room names, your entities will initially appear as `switch.apex_relay_1`, `light.apex_dimmer_24`, etc.

**The easiest way to name them:**

1.  Open the **Easyplus Apex** integration page in Home Assistant.
2.  Physically walk to a room and **turn on a light** using the wall switch.
3.  Watch your screen: one of the switches in the list will instantly jump to "On".
4.  Click on that entity, select the **Settings (cogwheel)** icon.
5.  Rename it (e.g., "Kitchen Light") and click **Update**.
6.  Repeat this for your other lights. Home Assistant will remember these names forever.

---

## 3. Configuring Shutters & Blinds (Covers)

The integration features a unique **"Discovery by Use"** wizard. You do not need to know the relay numbers to set up your blinds.

1.  Go to **Settings** > **Devices & Services** > **Easyplus Apex**.
2.  Click **Configure**.
3.  Select **"Detect Cover (Wizard)"** and click Next.
4.  **Follow the instructions:**
    * Click "Submit" in Home Assistant.
    * **Immediately** walk to your physical wall switch for the shutter.
    * Press **Open** briefly (you will hear a click).
    * Press **Close** briefly (you will hear a click).
    * *The system listens for 10 seconds for this activity.*
5.  **Result:**
    * The wizard will report: *"Cover Found! Activity detected on relays X and Y."*
    * Enter a name (e.g., "Living Room Blind").
    * Enter the total travel time (in seconds) for accurate positioning.
    * Click **Submit**.

Your shutter is now available as a Cover entity in Home Assistant!

---

## Troubleshooting

* **Connection Failed:** Check if your Home Assistant is on the same network as the Apex Controller. Ensure no "Client Isolation" is active on your router/modem.
* **Discovery Wizard fails:** Make sure you operate the physical switch *while* the spinner is showing in Home Assistant. You have a 10-second window.
