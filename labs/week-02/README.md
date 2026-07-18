# Week 2 Lab — Networking, Packet Capture, and Man-in-the-Middle

**Lecture:** Intro to Networking, OSI Model, and MITM Attacks

---

## Overview

HuskyHub transmits all data over plain HTTP. This week you will use Wireshark to capture your own login traffic and see your credentials in cleartext. You will then perform an ARP spoofing attack against a second device to intercept their session cookie and impersonate them without knowing their password.

No remediation this week. The goal is to viscerally understand why encryption in transit matters before you implement it in Week 3.

---

## ⚠️ Network and Acceptable Use Policy Warning

**Do NOT perform the ARP spoofing portion of this lab (Steps 1–6) on the UW campus network or any school-provided wifi** (this also extends to any shared network where other people are connected — apartment building wifi, office networks, or public hotspots like coffee shops).

ARP spoofing poisons ARP caches across your entire network subnet — not just between your two devices. On a shared network this affects other users' traffic and constitutes unauthorized interference with a computer network, which violates the UW Acceptable Use Policy and may violate the Computer Fraud and Abuse Act (18 U.S.C. § 1030).

**Required setup for Steps 1–6:** Both devices must be connected to an **isolated local network** — a personal mobile hotspot or a home router where you are the only user. The key requirement is that no other people are on the same network segment during the exercise.

The Wireshark setup exercises in the Understanding Wireshark section below are safe to perform anywhere.

---

## Tools

| Tool | Purpose |
|------|---------|
| Wireshark | Packet capture and traffic analysis |
| Scapy (Python library) | ARP spoofing to position yourself as a MITM |
| Terminal | Execute commands |
| ip / ifconfig / ipconfig | Identify network interfaces and IP addresses |
| Browser Developer Tools | Manually set cookies |

### Installing Tools by Platform

**macOS (all hardware including M1/M2/M3):**
```bash
# Install Wireshark — use the native .dmg from wireshark.org (not brew)
# Download from: https://www.wireshark.org/download.html
# Select the appropriate disk image for your hardware (Intel or Apple Silicon)

# Install Scapy
pip3 install scapy
```

> If `pip3` is not available, install Python 3 from [python.org](https://www.python.org/downloads/) first.

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install wireshark python3-pip
pip3 install scapy
```

> During Wireshark install, select **Yes** when asked whether non-root users may capture packets.

**Windows:**
- Download Wireshark from [wireshark.org/download](https://www.wireshark.org/download.html) and install normally. The installer will offer to install **Npcap** — accept this, as Scapy requires it for raw packet capture on Windows.
- Open PowerShell and install Scapy:
```powershell
pip install scapy
```

> All `arpspoof.py` and `arprestore.py` commands in this lab must be run in **PowerShell as Administrator** on Windows. Run the commands shown below as `python …` (no `sudo`) in that elevated PowerShell.

---

## Understanding Wireshark

Wireshark is a packet analyzer that records every packet traveling through your network interface and lets you inspect the raw contents of each one. You will use it throughout this lab: to verify your setup on your own machine first, and then during the MITM exercise to capture the victim device's session cookie.

**Opening Wireshark:**

Launch Wireshark from your Applications folder (macOS), Start menu (Windows), or run `wireshark` in a terminal (Linux). It is a graphical application — no terminal required.

**The main panels:**

| Panel | What it shows |
|-------|---------------|
| **Interface list** | All network interfaces on your machine. Select your active one before starting a capture. |
| **Packet list** | Every captured packet — one row each with timestamp, source and destination IPs, protocol, and a brief summary. |
| **Packet detail** | The selected packet broken into protocol layers. Click any layer's arrow to expand it and see the individual fields inside. |
| **Filter bar** | Type a display filter here to narrow what appears in the packet list. This does not discard captured data — it only controls what is visible. |

**Filters you will use in this lab:**

| Filter | What it matches |
|--------|----------------|
| `http.request.method == "POST"` | HTTP POST requests — what your browser sends when you submit a login form |
| `http.cookie` | Any HTTP request that includes a cookie header |
| `ip.addr == <victim-ip> && http.cookie` | Cookie-carrying requests to or from a specific IP — used in Step 4 of the MITM exercise |

**Finding credentials in a captured packet:**

Select a POST request in the packet list. In the packet detail pane, expand **Hypertext Transfer Protocol**, then expand **HTML Form URL Encoded**. The decoded form fields — username and password in plaintext — appear there.

**Finding a session cookie:**

Select a request matching the `http.cookie` filter. In the packet detail pane, expand **Hypertext Transfer Protocol** and look for the **Cookie** field. The full cookie string is shown there.

**Before starting the MITM exercise — verify your setup:**

Confirm Wireshark is capturing correctly on your machine by running through the following steps on your own HuskyHub instance. You will use these exact same techniques on the victim device's traffic during the MITM steps.

1. Find your active interface name (you will need this for Step 3 of the MITM exercise):
   - **macOS:** `ipconfig getifaddr en0` (try `en1` if this returns nothing)
   - **Linux:** `ip addr`
   - **Windows:** `ipconfig` in PowerShell

2. Open Wireshark. Because HuskyHub runs on `localhost`, your traffic travels over the **loopback interface** — select it here, not your Wi-Fi or Ethernet adapter:
   - **macOS:** `lo0`
   - **Linux:** `lo`
   - **Windows:** `Npcap Loopback Adapter`

   Start a capture using the blue shark fin button.

3. In your browser, navigate to `http://localhost:80/login` and log in. Stop the capture once you are redirected to the home page.

4. Apply the filter `http.request.method == "POST"`. Click the login request and expand the **HTML Form URL Encoded** section. Confirm you can see your credentials in plaintext — screenshot this.

5. Change the filter to `http.cookie`. Locate a request containing your session cookie and record the full value.

> **macOS note:** If no interfaces appear when you open Wireshark, go to System Preferences → Privacy & Security and grant Wireshark permission to capture packets, then relaunch.

---

## Understanding the Lab Scripts

Two Python scripts are provided in `labs/week-02/scripts/` for the MITM exercise. Both use **scapy**, a Python library for crafting and sending raw network packets at the Ethernet layer.

**Installing scapy:**

```bash
pip3 install scapy
```

> On macOS and Linux, both scripts require `sudo` because sending raw packets requires root privileges.

---

**`arpspoof.py`** — performs the ARP spoofing attack (one direction per invocation)

```
# Terminal 1 — tell the victim that you are the gateway
sudo python3 labs/week-02/scripts/arpspoof.py <victim-ip> <gateway-ip> <interface>

# Terminal 2 — tell the gateway that you are the victim
sudo python3 labs/week-02/scripts/arpspoof.py <gateway-ip> <victim-ip> <interface>
```

Run both simultaneously in two terminals. Each resolves the target's MAC address and sends forged ARP replies in a loop. Press `Ctrl+C` in each terminal to stop.

---

**`arprestore.py`** — restores ARP caches after the attack ends

```
sudo python3 labs/week-02/scripts/arprestore.py <interface> <victim-ip> <gateway-ip>
sudo python3 labs/week-02/scripts/arprestore.py <interface> <gateway-ip> <victim-ip>
```

Sends a burst of correct ARP replies to immediately repair the ARP caches of both devices. Run once per direction after stopping `arpspoof.py`.

> **Use the provided scripts as your primary method** — particularly on macOS, where the `arpspoof` tool from `dsniff` does not build reliably on Apple Silicon.

---

## Steps

### 1. Device Setup (MITM Exercise)

> **Reminder:** Both devices must be on an isolated personal network — not school wifi or any shared network. See the warning at the top of this lab.

This exercise requires a second device acting as the **victim device**. Any device with a browser will work — a second laptop, a desktop, or a phone. Your primary machine is the **attacker**.

**On the attacker machine only:** ensure HuskyHub is running (`docker compose up` in the `huskyhub-su26` directory) before the victim device tries to connect. The victim device does not need Docker or any special software — only a browser.

**On the victim device:**
Open a browser and navigate to `http://<attacker-ip>:80` (the attacker machine's IP on the shared network — not localhost). Leave this session active and the victim device on.

Connect both devices to the same isolated network (personal mobile hotspot or home router where you are the only user).

You need three values before proceeding:
1. Your own IP address (attacker machine)
2. The victim device's IP address
3. The gateway IP address

---

#### Step 1a. Find your own IP and the gateway

**macOS (all hardware including M1/M2/M3):**
```bash
# Your IP on the active interface
ipconfig getifaddr en0

# Gateway IP
netstat -rn | grep default | awk '{print $2}' | head -1
```

**Linux:**
```bash
ip addr show        # find your IP
ip route            # look for "default via <gateway>"
```

**Windows (PowerShell):**
```powershell
ipconfig
Get-NetRoute -DestinationPrefix "0.0.0.0/0"
```

> **iPhone hotspot note:** iPhones assign addresses in the `172.20.10.x` range, not `192.168.x.x`. Your IP will look like `172.20.10.2` through `172.20.10.14`, and the gateway will be `172.20.10.1`. Android hotspots typically use `192.168.43.x` with gateway `192.168.43.1`. If your IP looks unusual, this is why.

---

#### Step 1b. Find the victim device's IP address

The most reliable method on all platforms — including Apple Silicon Macs — is to read the ARP cache after both devices have exchanged any network traffic (such as loading HuskyHub):

**macOS / Linux (attacker machine):**
```bash
arp -a
```

This lists every device the attacker machine has recently talked to on the local network. Look for an entry whose IP is in the same subnet as yours but is not your own IP and not the gateway. That is the victim device.

**If the victim device does not appear in `arp -a` yet:**
Have the victim device navigate to `http://<attacker-ip>:80`. Any network activity will populate the ARP cache. Run `arp -a` again on the attacker machine.

**Alternative — nmap ping sweep (use only if `arp -a` fails):**

First, determine your subnet. If your IP is `172.20.10.3`, your subnet is `172.20.10.0/28`. If your IP is `192.168.43.5`, your subnet is `192.168.43.0/24`.

```bash
# macOS / Linux
sudo nmap -sn <your-subnet>
# Example for iPhone hotspot:
sudo nmap -sn 172.20.10.0/28
# Example for Android hotspot or home router:
sudo nmap -sn 192.168.43.0/24
```

---

**Before the victim device appears in `arp -a`, make sure HuskyHub has been loaded in its browser.** The Scapy scripts in Step 3 resolve MAC addresses via ARP at startup and will exit with an error if the target is not yet reachable. Confirming the victim device appears in `arp -a` first avoids this.

Record all three values before continuing:
- Attacker IP: `_______________`
- Victim IP: `_______________`
- Gateway IP: `_______________`

---

### 2. Enable IP Forwarding on the Attacker Machine

**What IP forwarding does and why disabling it would break the attack:**
Normally, an operating system discards IP packets addressed to other machines — it is not a router, so forwarding them is not its job. When you run the ARP spoofing script, the victim's traffic starts arriving at your machine because you have told the network you are the gateway. If IP forwarding is disabled, your machine receives those packets and drops them — the victim device loses internet connectivity, which is immediately noticeable and indicates something is wrong. Enabling IP forwarding tells the kernel to forward those packets onward to the real gateway, so traffic continues flowing transparently. From the victim device's perspective, everything appears normal. `sysctl` is the Linux/macOS tool for reading and writing kernel parameters at runtime; `net.inet.ip.forwarding=1` (macOS) and `net.ipv4.ip_forward=1` (Linux) are the specific parameters that control IP forwarding.

This ensures traffic continues to flow so the victim device does not lose connectivity during the attack.

**macOS:**
```bash
sudo sysctl -w net.inet.ip.forwarding=1
```

**Linux:**
```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

**Windows (PowerShell as Administrator):**
```powershell
# Windows handles IP forwarding differently — Scapy manages packet forwarding
# at the application layer. No separate sysctl step is required on Windows.
# Ensure PowerShell is running as Administrator before Step 3.
```

---

### 3. Execute the ARP Spoofing Attack

**What ARP is and what spoofing it accomplishes:**
ARP (Address Resolution Protocol) is how devices on a local network discover each other's MAC addresses. When your laptop wants to send a packet to the gateway (e.g., `192.168.1.1`), it broadcasts an ARP request: "Who has IP 192.168.1.1? Tell me your MAC address." The gateway responds with its MAC, and your laptop caches that mapping. The spoofing script exploits the fact that ARP has no authentication — any device can send an ARP reply claiming any IP-to-MAC mapping, and other devices will update their cache. By sending forged ARP replies to both the victim and the gateway, you insert your MAC into both their caches: the victim thinks you are the gateway (sends you their outbound traffic), and the gateway thinks you are the victim (sends you traffic destined for the victim). Running both commands together covers both directions.

Open two terminals on the attacker machine and run both commands simultaneously:

```bash
# Terminal 1: Tell the victim that you are the gateway
sudo python3 labs/week-02/scripts/arpspoof.py <victim-ip> <gateway-ip> <interface>

# Terminal 2: Tell the gateway that you are the victim
sudo python3 labs/week-02/scripts/arpspoof.py <gateway-ip> <victim-ip> <interface>
```

**Example** (iPhone hotspot, Wi-Fi interface `en0`, victim at `172.20.10.5`, gateway at `172.20.10.1`):
```bash
# Terminal 1
sudo python3 labs/week-02/scripts/arpspoof.py 172.20.10.5 172.20.10.1 en0

# Terminal 2
sudo python3 labs/week-02/scripts/arpspoof.py 172.20.10.1 172.20.10.5 en0
```

> **macOS note:** The interface will typically be `en0` (Wi-Fi) or `en1`. Confirm with `ifconfig`.

> **Windows note:** Open both PowerShell windows as Administrator. The interface name will appear as a quoted string (e.g., `"Wi-Fi"` or `"Ethernet"`). Confirm with `ipconfig`.

---

### 4. Capture the Victim's Session Cookie

**Why the session cookie is the target and what it grants the attacker:**
HTTP is a stateless protocol — the server has no built-in memory of who you are between requests. Session cookies solve this by storing a token that identifies your authenticated session. When the victim's browser sends any request to HuskyHub, it attaches this cookie automatically. Because you are now a man-in-the-middle receiving all their traffic, Wireshark can read the cookie value from the unencrypted HTTP stream. The Wireshark filter `ip.addr == <victim-ip> && http.cookie` narrows the capture to HTTP requests from the victim device's IP that contain cookie headers. Once you have the cookie value, you do not need the victim's password — you can impersonate their authenticated session directly.

While both `arpspoof.py` processes are running, open Wireshark on the **attacker machine**:

1. On the Wireshark start screen, select your **Wi-Fi network interface** — this is where the victim's traffic arrives:
   - **macOS:** `en0` (or `en1` if en0 shows no traffic)
   - **Linux:** `wlan0` or `eth0` depending on your connection type
   - **Windows:** `Wi-Fi` or `Ethernet` (whichever you used to connect to the shared network)

   > Do **not** select the loopback interface here — unlike the verification exercise earlier, you are capturing traffic arriving over the network, not traffic from your own machine.

2. Click the blue shark fin button to start the capture.

3. In the filter bar at the top, type the following and press Enter:
   ```
   ip.addr == <victim-ip> && http.cookie
   ```

**On the victim device:** navigate to `http://<attacker-ip>:80` and click between pages in HuskyHub (Home, Grades, etc.). Each page load sends an HTTP request with the session cookie attached.

On the attacker machine, packets from the victim's IP will appear in the capture list. Click one, expand **Hypertext Transfer Protocol** in the packet detail pane, and look for the **Cookie** field. Record the full cookie value.

---

### 5. Impersonate the Victim

**Why manually setting a cookie is equivalent to stealing credentials:**
Cookies are stored by the browser and sent automatically on every request to the matching domain. The browser has no mechanism to verify that a cookie was legitimately issued by the server — it stores and transmits whatever value is present. When you open Developer Tools and manually change the `authenticated` cookie to match the victim's value, your browser will send that value on your next request to `localhost`. The server reads the cookie, recognizes it as a valid session token it previously issued, and responds as if it is talking to the victim. There is no second factor, no IP address check, no re-verification — the cookie alone is the authentication proof. This is the exact attack model that motivates the `HttpOnly` and `Secure` cookie flags you observed in Week 1: `HttpOnly` prevents JavaScript from reading the cookie (blocking XSS-based theft), and `Secure` prevents it from being sent over plain HTTP (blocking this exact interception).

In your browser, open Developer Tools → **Application → Cookies → localhost**.

Manually set the `authenticated` cookie to the value you captured. Set the `role` and `user_id` cookies to match what you observed.

Reload `http://localhost`. Document what you can now access.

---

### 6. Restore the Network

**What happens to ARP caches when the attack stops and why restoration matters:**
ARP cache entries have a time-to-live. When the spoofing script stops sending its false replies, the victim and gateway will eventually receive legitimate ARP responses from the real owners of each IP address, and their caches will self-correct. However, "eventually" may take 60 seconds or more. The restoration script sends explicit ARP replies with the correct MAC addresses, repairing both caches immediately rather than waiting for TTL expiry. This step is also an ethical obligation: you are running this exercise against your own second device on an isolated network, and cleanly restoring the network to its pre-attack state is part of responsible security research practice.

Stop both `arpspoof.py` processes (`Ctrl+C`). Then run `arprestore.py` once for each direction:

```bash
# Repair the victim's ARP cache (tell them the real MAC for the gateway)
sudo python3 labs/week-02/scripts/arprestore.py <interface> <victim-ip> <gateway-ip>

# Repair the gateway's ARP cache (tell it the real MAC for the victim)
sudo python3 labs/week-02/scripts/arprestore.py <interface> <gateway-ip> <victim-ip>
```

Confirm the victim device can still reach HuskyHub normally.

Disable IP forwarding:

**macOS:**
```bash
sudo sysctl -w net.inet.ip.forwarding=0
```

**Linux:**
```bash
sudo sysctl -w net.ipv4.ip_forward=0
```

---

## Write-Up Questions

**Q1.** You impersonated the victim device's session using only a session cookie — no password required. What does this tell you about how HuskyHub authenticates users after login? What is the difference between authentication and session management, and which one failed here?

**Q2.** At which OSI layer would HTTPS protect against each of the two attacks performed today (credential capture and cookie theft)? Would HTTPS fully prevent both? Explain any remaining risk.

**Q3.** The ARP spoofing attack required you to be on the same local network as your target. What are realistic scenarios in which an attacker could be on the same network as a user of a public web application?

---

## Hacker Mindset Prompt

An attacker intercepting traffic at a coffee shop is combining a Layer 2 manipulation with passive observation. The attack is silent, requires no vulnerability in the target application, and is nearly undetectable by the victim.

Reflect on:

- **Contrarian:** This attack requires no login, no exploit, and no interaction with the application at all. What assumption about "security" does this challenge?
- **Committed:** A committed attacker who captures a valid session cookie does not stop at reading one page. Describe the next three steps they would take.
- **Creative:** How would you design a network attack that captures credentials from many users simultaneously rather than one targeted victim?
