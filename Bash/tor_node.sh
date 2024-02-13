#!/bin/bash
echo "=== Creating tor user ==="
useradd -m -s /bin/bash tor
echo "tor:tor" | chpasswd
usermod -aG sudo tor
echo "tor ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "=== Installing xfc3 and VNC ==="
# function to execute on behalf of tor user
function run_as_tor {
	su - tor -c "$1"
}
sudo apt-get update
run_as_tor "sudo apt-get install xfce4 xfce4-goodies -y"
run_as_tor "sudo apt-get install tightvncserver -y"
run_as_tor "sudo apt-get install dbus-x11 -y"
echo "=== Setting up TOR ==="
run_as_tor 'cd /home/tor; wget https://www.torproject.org/dist/torbrowser/13.0.9/tor-browser-linux-x86_64-13.0.9.tar.xz -P /home/tor/; tar -xvJf tor-browser-linux-x86_64-13.0.9.tar.xz; sudo mv /home/tor/tor-browser /usr/local/share/'
run_as_tor 'cd /usr/local/share/tor-browser;./start-tor-browser.desktop --register-app'
echo "=== Configuring VNC ==="
run_as_tor "mkdir -p /home/tor/.vnc"
run_as_tor 'echo "l7Vt53Jmkck=" | base64 -d > /home/tor/.vnc/passwd' # password is KKoLkb8
run_as_tor 'sudo chmod 600 /home/tor/.vnc/passwd'
run_as_tor 'echo "#/bin/bash" > /home/tor/.vnc/xstartup'
run_as_tor 'echo "xrdb $HOME/.Xresources" >> /home/tor/.vnc/xstartup'
run_as_tor 'echo "startxfce4 &" >> /home/tor/.vnc/xstartup'
run_as_tor 'chmod 755 /home/tor/.vnc/xstartup'
run_as_tor 'sudo chown -R tor:tor /home/tor/.vnc'
echo "=== Starting VNC ==="
run_as_tor 'vncserver -geometry 1920x1080'
echo "=== replacing history with link to null ==="
run_as_tor 'ln -sf /dev/null /home/tor/.bash_history'
echo "=== updating the node ==="
sudo apt-get upgrade -y