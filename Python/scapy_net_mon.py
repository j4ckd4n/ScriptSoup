from scapy.all import *

import datetime

def format_raw_data(data):
  return ''.join([chr(b) if 32 <= b <= 126 else '.' for b in data])

def packet_handler(packet: Packet):
  if packet.haslayer('Raw'):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if packet.haslayer('IP') and (packet.haslayer("TCP") or packet.haslayer("UDP")):
      src_ip = packet['IP'].src
      dst_ip = packet['IP'].dst
      src_port = packet['TCP'].sport if packet.haslayer('TCP') else packet['UDP'].sport
      dst_port = packet['TCP'].dport if packet.haslayer('TCP') else packet['UDP'].dport

      hex_data = "no raw data"
      raw_data = "no raw data"

      if packet['Raw'].load:
        hex_data = packet['Raw'].load[:16].hex()
        raw_data = format_raw_data(packet['Raw'].load[:32])

      print(f"[{timestamp}] {src_ip}:{src_port} -> {dst_ip}:{dst_port} | Hex: {hex_data} | Raw: {raw_data}")

sniff(iface="Wi-Fi", prn=packet_handler, store=0)