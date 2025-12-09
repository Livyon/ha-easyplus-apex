# Easyplus Apex (Unofficial) for Home Assistant

![Banner](https://capsule-render.vercel.app/api?type=waving&color=00a1f1&height=200&section=header&text=Easyplus%20Apex&fontSize=70&animation=fadeIn&fontAlignY=35&desc=Unofficial%20Integration%20by%20Core%20Automations&descAlignY=55&descAlign=50)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-1.3.0-blue.svg?style=for-the-badge&logo=github)](https://github.com/CoreAutomations/ha-easyplus-apex)
[![maintainer](https://img.shields.io/badge/maintainer-Core%20Automations-green.svg?style=for-the-badge)](https://coreautomations.be)

**Modernize your Easyplus Apex System.** This robust, local-push integration bridges the gap between existing Apex installations and the modern smart home world of Home Assistant.

Developed by **Core Automations**, designed for stability and ease of use.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **📄 Smart XML Import** | **New!** Import your `config.xml` file. The system automatically creates entities with the **correct names**, maps **shutters**, and strictly separates **lights vs. switches**. No more manual renaming! |
| **🧹 Zero Junk** | When using XML Import, unused relays ("Re +4", "relay 85") are automatically filtered out. Keep your Home Assistant clean. |
| **🔌 Auto-Discovery** | Don't have the XML file? No problem. Use the Auto-Discovery mode to find devices as you use them. |
| **🪄 Magic Wizard** | Exclusive **"Discovery by Use"** technology. Add new shutters manually simply by pressing the wall switch. |
| **⚡️ Instant Updates** | Uses a local TCP push connection. When you press a button, Home Assistant updates instantly (0ms delay). |

## 🚀 Installation

### Option 1: HACS (Recommended)
The easiest way to install and keep updated.

1.  Open **HACS** in Home Assistant.
2.  Go to **Integrations** > Top right menu > **Custom repositories**.
3.  Add this URL: `https://github.com/JOUW_GITHUB_NAAM/ha-easyplus-apex`
4.  Category: **Integration**.
5.  Click **Download**.
6.  **Restart** Home Assistant.

### Option 2: Manual
1.  Download the `easyplus_apex` folder from this repository.
2.  Copy it to your `custom_components` folder in Home Assistant.
3.  Restart Home Assistant.

---

## 📚 Configuration

This integration supports two configuration methods:

1.  **XML Import (Recommended):** Export your config from the Apex software, paste it into Home Assistant, and you are done. All names and types are set automatically.
2.  **Manual / Auto-Discovery:** Detects devices as you use them. Useful if you do not have access to the original configuration file.

👉 **[Read the Full User Manual (MANUAL.md)](MANUAL.md)** for detailed steps on exporting XML and configuring shutters.

---

## ⚖️ Disclaimer & Credits

**Unofficial Integration**
This project is an open-source initiative developed by **Core Automations**. It is not officially affiliated with, maintained, or endorsed by *Apex Systems International* or *Easyplus*.

The names "Easyplus" and "Apex Systems" are trademarks of their respective owners and are used in this project solely for identification and compatibility purposes.

**License**
MIT License.
