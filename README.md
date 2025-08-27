# 🛡️ SFTP/FTP Sync Monitor

## 📂 What’s Inside
This tool was built during real-world DFIR and incident response cases where **fast, reliable, and secure file syncing** was critical.  
It has been refined through practical use, balancing simplicity with functionality.  

Whether you’re collecting forensic images, monitoring log sources, or just keeping folders in sync — this script does the job with minimal overhead.  

👉 [GitHub Repo](https://github.com/dfirvault/sftpmonitor/)

---

<img width="756" height="617" alt="image" src="https://github.com/user-attachments/assets/cbb774af-35b1-4f49-aeaa-0b78d3074b93" />


## ✅ Features
- **Two-Way Monitoring**: Choose to watch either your local folder or the remote server.  
- **Real-Time Sync**: Automatically uploads, downloads, or deletes files as changes occur.  
- **Protocol Flexibility**: Works with secure **SFTP** or standard **FTP**.  
- **Lightweight**: No heavy dependencies — just `paramiko` + `watchdog`.  
- **Forensic-Ready**: Perfect for collecting logs, evidence, or case data securely.  

---

## 🧠 Use Case
Designed for analysts, responders, and engineers who need to **move and monitor files securely** without manual intervention. Typical workflow:

1. Connect to a remote server (SFTP/FTP).  
2. Select the remote folder to watch.  
3. Select your local folder.  
4. Pick your mode:  
   - **REMOTE mode** → Download any new/changed files from server.  
   - **LOCAL mode** → Upload any new/changed files to server.  
5. Let it run. Files stay in sync automatically.  

---

## 🚀 Get Started
Clone and run:
```bash
git clone https://github.com/dfirvault/sftpmonitor/
cd sftpmonitor
pip install paramiko watchdog
python SFTPMonitor.py
```

---

## 📬 Contact
👤 Jacob Wilson  
📧 dfirvault@gmail.com  

---
⚡ *Fast. Focused. Forensic.*
