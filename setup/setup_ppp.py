import os

peer_content = """/dev/serial0
115200
nocrtscts
debug
lock
local
ipcp-accept-local
ipcp-accept-remote
usepeerdns
defaultroute
replacedefaultroute
noauth
hide-password
persist
connect "/usr/sbin/chat -v -f /etc/ppp/chat-sim7600"
"""

chat_content = """ABORT "BUSY"
ABORT "NO CARRIER"
ABORT "NO DIALTONE"
ABORT "ERROR"
ABORT "NO ANSWER"
"" AT
OK AT+CGDCONT=1,"IP","internet"
OK ATD*99#
CONNECT
"""

def setup():
    try:
        # Write files locally
        with open('/home/luz/sim7600.peer', 'w') as f:
            f.write(peer_content)
        with open('/home/luz/sim7600.chat', 'w') as f:
            f.write(chat_content)
            
        print("Files created in /home/luz/.")
        print("Now running sudo commands to move them...")
        
        os.system('sudo mv /home/luz/sim7600.peer /etc/ppp/peers/sim7600')
        os.system('sudo mv /home/luz/sim7600.chat /etc/ppp/chat-sim7600')
        os.system('sudo chown root:dip /etc/ppp/peers/sim7600 /etc/ppp/chat-sim7600')
        os.system('sudo chmod 640 /etc/ppp/peers/sim7600 /etc/ppp/chat-sim7600')
        
        print("Setup completed successfully.")
        print("Restarting connection...")
        os.system('sudo poff sim7600')
        import time
        time.sleep(2)
        os.system('sudo pon sim7600')
    except Exception as e:
        print(f"Error during setup: {e}")

if __name__ == '__main__':
    setup()
