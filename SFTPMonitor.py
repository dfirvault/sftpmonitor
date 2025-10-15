import os
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime
import ftplib
import paramiko
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import getpass
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, Listbox, Scrollbar, Button, ttk
import sys
import math
from tqdm import tqdm
import shutil
import logging

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

print(f"{Colors.HEADER}{Colors.BOLD}")
print("╔══════════════════════════════════════════════════════════════╗")
print("║                   SFTP/FTP File Sync Monitor                 ║")
print("║                   Developed by Jacob Wilson                  ║")
print("║                   dfirvault@gmail.com                        ║")
print("╚══════════════════════════════════════════════════════════════╝")
print(f"{Colors.END}")

# Setup logging
def setup_logging(local_folder):
    log_dir = os.path.join(local_folder, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"sync_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

class FTPClient:
    def __init__(self, host, username, password, port=22, use_sftp=True):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_sftp = use_sftp
        self.connection = None
        
    def connect(self):
        try:
            if self.use_sftp:
                self.connection = paramiko.Transport((self.host, self.port))
                self.connection.connect(username=self.username, password=self.password)
                self.sftp = paramiko.SFTPClient.from_transport(self.connection)
                print(f"{Colors.GREEN}✓ Connected to SFTP server {self.host}:{self.port}{Colors.END}")
            else:
                self.connection = ftplib.FTP()
                self.connection.connect(self.host, self.port)
                self.connection.login(self.username, self.password)
                print(f"{Colors.GREEN}✓ Connected to FTP server {self.host}:{self.port}{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ Connection failed: {e}{Colors.END}")
            return False
    
    def disconnect(self):
        if self.connection:
            if self.use_sftp:
                self.connection.close()
            else:
                self.connection.quit()
            print(f"{Colors.YELLOW}Disconnected from server{Colors.END}")
    
    def list_files(self, remote_path):
        try:
            if self.use_sftp:
                return self.sftp.listdir(remote_path)
            else:
                return self.connection.nlst(remote_path)
        except Exception as e:
            print(f"{Colors.RED}Error listing files: {e}{Colors.END}")
            return []
    
    def list_folders(self, remote_path="."):
        try:
            items = self.list_files(remote_path)
            folders = []
            
            for item in items:
                if item in ['.', '..']:
                    continue
                    
                try:
                    if self.use_sftp:
                        item_path = os.path.join(remote_path, item).replace('\\', '/')
                        if self.sftp.stat(item_path).st_mode & 0o40000:  # Check if it's a directory
                            folders.append(item)
                    else:
                        # For FTP, we'll assume it's a folder if we can't determine otherwise
                        folders.append(item)
                except:
                    continue
                    
            return folders
        except Exception as e:
            print(f"{Colors.RED}Error listing folders: {e}{Colors.END}")
            return []
    
    def download_file(self, remote_path, local_path, logger):
        try:
            if self.use_sftp:
                # Get file size for progress tracking
                file_size = self.sftp.stat(remote_path).st_size
                
                # Show progress bar for download
                with tqdm(total=file_size, unit='B', unit_scale=True, 
                         desc=f"{Colors.BLUE}Downloading{Colors.END}", 
                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                    def progress_callback(transferred, total):
                        pbar.total = total
                        pbar.update(transferred - pbar.n)
                    
                    self.sftp.get(remote_path, local_path, callback=progress_callback)
            else:
                # FTP download with progress
                file_size = self.connection.size(remote_path)
                
                with open(local_path, 'wb') as f:
                    with tqdm(total=file_size, unit='B', unit_scale=True, 
                             desc=f"{Colors.BLUE}Downloading{Colors.END}", 
                             bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                        def callback(data):
                            f.write(data)
                            pbar.update(len(data))
                            
                        self.connection.retrbinary(f'RETR {remote_path}', callback)
            
            filename = os.path.basename(local_path)
            print(f"{Colors.GREEN}✓ Downloaded: {filename}{Colors.END}")
            logger.info(f"DOWNLOADED: {filename} from {remote_path} to {local_path}")
            return True
        except Exception as e:
            filename = os.path.basename(local_path)
            print(f"{Colors.RED}✗ Download failed: {e}{Colors.END}")
            logger.error(f"DOWNLOAD FAILED: {filename} - {e}")
            return False
    
    def upload_file(self, local_path, remote_path, logger):
        try:
            file_size = os.path.getsize(local_path)
            
            if self.use_sftp:
                # SFTP upload with progress
                with tqdm(total=file_size, unit='B', unit_scale=True, 
                         desc=f"{Colors.CYAN}Uploading{Colors.END}", 
                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                    def progress_callback(transferred, total):
                        pbar.total = total
                        pbar.update(transferred - pbar.n)
                    
                    self.sftp.put(local_path, remote_path, callback=progress_callback)
            else:
                # FTP upload with progress
                with open(local_path, 'rb') as f:
                    with tqdm(total=file_size, unit='B', unit_scale=True, 
                             desc=f"{Colors.CYAN}Uploading{Colors.END}", 
                             bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                        def callback(data):
                            pbar.update(len(data))
                            return data
                            
                        self.connection.storbinary(f'STOR {remote_path}', f, callback=callback)
            
            filename = os.path.basename(local_path)
            print(f"{Colors.GREEN}✓ Uploaded: {filename}{Colors.END}")
            logger.info(f"UPLOADED: {filename} from {local_path} to {remote_path}")
            return True
        except Exception as e:
            filename = os.path.basename(local_path)
            print(f"{Colors.RED}✗ Upload failed: {e}{Colors.END}")
            logger.error(f"UPLOAD FAILED: {filename} - {e}")
            return False
    
    def get_file_size(self, remote_path):
        try:
            if self.use_sftp:
                return self.sftp.stat(remote_path).st_size
            else:
                return self.connection.size(remote_path)
        except:
            return -1
    
    def file_exists(self, remote_path):
        try:
            if self.use_sftp:
                self.sftp.stat(remote_path)
            else:
                self.connection.size(remote_path)
            return True
        except:
            return False

class FileMonitor:
    def __init__(self):
        self.running = False
        self.last_activity_time = 0
        self.activity_detected = False
        
    def calculate_file_hash(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None
    
    def check_for_changes(self, ftp_client, remote_dir, local_dir, file_states, logger):
        """Check for changes and return True if changes were found"""
        changes_found = False
        try:
            remote_files = ftp_client.list_files(remote_dir)
            
            for filename in remote_files:
                if filename in ['.', '..']:
                    continue
                    
                remote_path = os.path.join(remote_dir, filename).replace('\\', '/')
                local_path = os.path.join(local_dir, filename)
                
                current_size = ftp_client.get_file_size(remote_path)
                file_exists = ftp_client.file_exists(remote_path)
                
                if filename not in file_states:
                    # New file detected
                    print(f"{Colors.BLUE}New file detected: {filename}{Colors.END}")
                    logger.info(f"NEW FILE DETECTED: {filename}")
                    if ftp_client.download_file(remote_path, local_path, logger):
                        file_states[filename] = {
                            'size': current_size,
                            'exists': file_exists,
                            'timestamp': time.time()
                        }
                        changes_found = True
                        self.activity_detected = True
                        self.last_activity_time = time.time()
                else:
                    # Check for changes
                    previous_state = file_states[filename]
                    if (previous_state['size'] != current_size or 
                        previous_state['exists'] != file_exists):
                        
                        print(f"{Colors.YELLOW}File changed: {filename}{Colors.END}")
                        logger.info(f"FILE CHANGED: {filename}")
                        if ftp_client.download_file(remote_path, local_path, logger):
                            file_states[filename] = {
                                'size': current_size,
                                'exists': file_exists,
                                'timestamp': time.time()
                            }
                            changes_found = True
                            self.activity_detected = True
                            self.last_activity_time = time.time()
            
            # Check for deleted files
            for filename in list(file_states.keys()):
                if filename not in remote_files:
                    local_path = os.path.join(local_dir, filename)
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        print(f"{Colors.RED}File deleted locally: {filename}{Colors.END}")
                        logger.info(f"FILE DELETED LOCALLY: {filename}")
                        changes_found = True
                        self.activity_detected = True
                        self.last_activity_time = time.time()
                    del file_states[filename]
                    
        except Exception as e:
            print(f"{Colors.RED}Error during change detection: {e}{Colors.END}")
            logger.error(f"Change detection error: {e}")
            
        return changes_found
    
    def monitor_remote(self, config, logger):
        """Monitor remote site for changes and download locally"""
        interval = config.get('interval', 60)  # Default to 60 seconds if not specified
        print(f"\n{Colors.HEADER}{Colors.BOLD}Starting REMOTE monitoring...{Colors.END}")
        print(f"{Colors.YELLOW}The tool will check for changes on the remote server{Colors.END}")
        print(f"{Colors.YELLOW}Base interval: {interval} seconds (will check immediately after changes){Colors.END}")
        print(f"{Colors.YELLOW}Any changes detected will be downloaded to your local folder{Colors.END}")
        logger.info("Starting REMOTE monitoring")
        logger.info(f"Remote folder: {config['remote_folder']}")
        logger.info(f"Local folder: {config['local_folder']}")
        logger.info(f"Base check interval: {interval} seconds")
        
        ftp_client = FTPClient(
            config['host'], config['username'], config['password'],
            config.get('port', 22), config.get('use_sftp', True)
        )
        
        if not ftp_client.connect():
            print(f"{Colors.RED}Failed to connect to remote server{Colors.END}")
            logger.error("Failed to connect to remote server")
            return
        
        # Create local directory if it doesn't exist
        local_dir = config['local_folder']
        os.makedirs(local_dir, exist_ok=True)
        
        remote_dir = config['remote_folder']
        file_states = {}
        
        # Initial check
        print(f"{Colors.CYAN}Performing initial check for changes...{Colors.END}")
        self.check_for_changes(ftp_client, remote_dir, local_dir, file_states, logger)
        
        consecutive_no_changes = 0
        current_interval = 5  # Start with quick checks after initial sync
        
        try:
            while self.running:
                try:
                    # Check for changes
                    changes_found = self.check_for_changes(ftp_client, remote_dir, local_dir, file_states, logger)
                    
                    if changes_found:
                        # Changes detected - check again soon
                        consecutive_no_changes = 0
                        current_interval = 5
                        print(f"{Colors.GREEN}Changes detected. Checking again in {current_interval} seconds...{Colors.END}")
                    else:
                        # No changes - gradually increase interval up to the configured maximum
                        consecutive_no_changes += 1
                        if consecutive_no_changes <= 3:
                            current_interval = 5  # Quick checks for first few no-change cycles
                        elif consecutive_no_changes <= 6:
                            current_interval = 15  # Medium interval
                        else:
                            current_interval = interval  # Use configured interval
                        
                        if consecutive_no_changes == 1:
                            print(f"{Colors.CYAN}No changes detected. Next check in {current_interval} seconds...{Colors.END}")
                        else:
                            print(f"{Colors.CYAN}No changes detected ({consecutive_no_changes}x). Next check in {current_interval} seconds...{Colors.END}")
                    
                    # Wait for the calculated interval
                    for remaining in range(current_interval, 0, -1):
                        if not self.running:
                            break
                        status_msg = f"Next check in {remaining}s (interval: {current_interval}s)"
                        if changes_found:
                            status_msg += " - Changes detected!"
                        elif consecutive_no_changes > 0:
                            status_msg += f" - No changes ({consecutive_no_changes}x)"
                        print(f"{Colors.CYAN}{status_msg}{Colors.END}", end='\r')
                        time.sleep(1)
                    
                    print(" " * 80, end='\r')  # Clear line
                        
                except Exception as e:
                    print(f"{Colors.RED}Error during monitoring: {e}{Colors.END}")
                    logger.error(f"Monitoring error: {e}")
                    # Try to reconnect
                    ftp_client.disconnect()
                    time.sleep(5)
                    if not ftp_client.connect():
                        print(f"{Colors.RED}Reconnection failed{Colors.END}")
                        logger.error("Reconnection failed")
                        break
                    # Reset states after reconnection
                    file_states = {}
                    consecutive_no_changes = 0
                    current_interval = 5
                
        finally:
            ftp_client.disconnect()
            logger.info("Remote monitoring stopped")
    
    class LocalChangeHandler(FileSystemEventHandler):
        def __init__(self, ftp_client, remote_dir, local_dir, logger, monitor_instance):
            self.ftp_client = ftp_client
            self.remote_dir = remote_dir
            self.local_dir = local_dir
            self.logger = logger
            self.monitor_instance = monitor_instance
            self.upload_queue = []
            self.uploading = False
        
        def on_created(self, event):
            if not event.is_directory:
                self.upload_file(event.src_path)
        
        def on_modified(self, event):
            if not event.is_directory:
                # Small delay to ensure file is completely written
                threading.Timer(2.0, self.upload_file, [event.src_path]).start()
        
        def on_deleted(self, event):
            if not event.is_directory:
                filename = os.path.basename(event.src_path)
                remote_path = os.path.join(self.remote_dir, filename).replace('\\', '/')
                try:
                    if self.ftp_client.use_sftp:
                        self.ftp_client.sftp.remove(remote_path)
                    else:
                        self.ftp_client.connection.delete(remote_path)
                    print(f"{Colors.RED}File deleted remotely: {filename}{Colors.END}")
                    self.logger.info(f"FILE DELETED REMOTELY: {filename}")
                    self.monitor_instance.activity_detected = True
                    self.monitor_instance.last_activity_time = time.time()
                except Exception as e:
                    print(f"{Colors.RED}Error deleting remote file: {e}{Colors.END}")
                    self.logger.error(f"DELETE FAILED: {filename} - {e}")
        
        def on_moved(self, event):
            # Handle file renames/moves
            if not event.is_directory:
                old_filename = os.path.basename(event.src_path)
                new_filename = os.path.basename(event.dest_path)
                old_remote_path = os.path.join(self.remote_dir, old_filename).replace('\\', '/')
                new_remote_path = os.path.join(self.remote_dir, new_filename).replace('\\', '/')
                
                try:
                    if self.ftp_client.use_sftp:
                        self.ftp_client.sftp.rename(old_remote_path, new_remote_path)
                    else:
                        # FTP doesn't have a direct rename command, so we need to download and re-upload
                        temp_path = os.path.join(self.local_dir, f"temp_{old_filename}")
                        with open(temp_path, 'wb') as f:
                            self.ftp_client.connection.retrbinary(f'RETR {old_remote_path}', f.write)
                        self.ftp_client.connection.delete(old_remote_path)
                        with open(temp_path, 'rb') as f:
                            self.ftp_client.connection.storbinary(f'STOR {new_remote_path}', f)
                        os.remove(temp_path)
                    
                    print(f"{Colors.YELLOW}File renamed remotely: {old_filename} -> {new_filename}{Colors.END}")
                    self.logger.info(f"FILE RENAMED: {old_filename} -> {new_filename}")
                    self.monitor_instance.activity_detected = True
                    self.monitor_instance.last_activity_time = time.time()
                except Exception as e:
                    print(f"{Colors.RED}Error renaming remote file: {e}{Colors.END}")
                    self.logger.error(f"RENAME FAILED: {old_filename} -> {new_filename} - {e}")
        
        def upload_file(self, local_path):
            """Upload file with retry logic"""
            if not os.path.exists(local_path):
                return
                
            filename = os.path.basename(local_path)
            remote_path = os.path.join(self.remote_dir, filename).replace('\\', '/')
            
            try:
                # Wait a moment to ensure file is completely written
                time.sleep(1)
                
                if self.ftp_client.upload_file(local_path, remote_path, self.logger):
                    self.monitor_instance.activity_detected = True
                    self.monitor_instance.last_activity_time = time.time()
            except Exception as e:
                print(f"{Colors.RED}Error uploading file: {e}{Colors.END}")
                self.logger.error(f"UPLOAD FAILED: {filename} - {e}")
    
    def monitor_local(self, config, logger):
        """Monitor local folder for changes and upload to remote"""
        interval = config.get('interval', 60)
        print(f"\n{Colors.HEADER}{Colors.BOLD}Starting LOCAL monitoring...{Colors.END}")
        print(f"{Colors.YELLOW}The tool will watch for changes in your local folder{Colors.END}")
        print(f"{Colors.YELLOW}Base interval: {interval} seconds for periodic checks{Colors.END}")
        print(f"{Colors.YELLOW}Any changes detected will be uploaded to the remote server{Colors.END}")
        logger.info("Starting LOCAL monitoring")
        logger.info(f"Remote folder: {config['remote_folder']}")
        logger.info(f"Local folder: {config['local_folder']}")
        logger.info(f"Base check interval: {interval} seconds")
        
        ftp_client = FTPClient(
            config['host'], config['username'], config['password'],
            config.get('port', 22), config.get('use_sftp', True)
        )
        
        if not ftp_client.connect():
            print(f"{Colors.RED}Failed to connect to remote server{Colors.END}")
            logger.error("Failed to connect to remote server")
            return
        
        local_dir = config['local_folder']
        remote_dir = config['remote_folder']
        
        # Initial sync: upload all local files with progress
        local_files = [f for f in os.listdir(local_dir) if os.path.isfile(os.path.join(local_dir, f))]
        if local_files:
            print(f"{Colors.CYAN}Performing initial sync of {len(local_files)} files...{Colors.END}")
            logger.info(f"Performing initial sync of {len(local_files)} files")
            
            for filename in tqdm(local_files, desc=f"{Colors.CYAN}Initial Upload{Colors.END}", 
                                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
                local_path = os.path.join(local_dir, filename)
                remote_path = os.path.join(remote_dir, filename).replace('\\', '/')
                ftp_client.upload_file(local_path, remote_path, logger)
                self.activity_detected = True
                self.last_activity_time = time.time()
        
        # Set up watchdog observer
        event_handler = self.LocalChangeHandler(ftp_client, remote_dir, local_dir, logger, self)
        observer = Observer()
        observer.schedule(event_handler, local_dir, recursive=False)
        observer.start()
        
        print(f"{Colors.GREEN}✓ Now monitoring local folder for changes{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop monitoring{Colors.END}")
        logger.info("Now monitoring local folder for changes")
        
        # Additional periodic check for any missed changes
        last_periodic_check = time.time()
        
        try:
            while self.running:
                # Periodic check every interval seconds for any missed changes
                current_time = time.time()
                if current_time - last_periodic_check >= interval:
                    print(f"{Colors.CYAN}Performing periodic check for missed changes...{Colors.END}")
                    # Here you could add logic to check for any inconsistencies
                    last_periodic_check = current_time
                
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        finally:
            observer.stop()
            observer.join()
            ftp_client.disconnect()
            logger.info("Local monitoring stopped")

def browse_local_folder():
    """Open a dialog to select local folder"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)
    folder_path = filedialog.askdirectory(title="Select Local Folder to Monitor")
    root.destroy()
    
    if folder_path:
        # Normalize path for Windows
        folder_path = os.path.normpath(folder_path)
        print(f"{Colors.GREEN}Selected local folder: {folder_path}{Colors.END}")
    
    return folder_path

def select_remote_folder(ftp_client):
    """Open a dialog to select remote folder"""
    root = tk.Tk()
    root.title("Select Remote Folder")
    root.geometry("600x500")
    root.configure(bg="#2e3440")
    
    # Set style for dark theme
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TFrame', background='#2e3440')
    style.configure('TLabel', background='#2e3440', foreground='#eceff4')
    style.configure('TButton', background='#5e81ac', foreground='#eceff4')
    style.configure('Listbox', background='#3b4252', foreground='#eceff4', selectbackground='#5e81ac')
    
    current_path = "/"
    folders_list = []
    
    def update_listbox(path):
        nonlocal current_path
        current_path = path
        path_label.config(text=f"Current Path: {path}")
        
        listbox.delete(0, tk.END)
        folders = ftp_client.list_folders(path)
        
        # Add parent directory if not at root
        if path != "/":
            listbox.insert(tk.END, "../")
        
        for folder in folders:
            listbox.insert(tk.END, folder + "/")
    
    def on_select(event):
        selection = listbox.get(listbox.curselection())
        if selection == "../":
            new_path = os.path.dirname(current_path.rstrip('/'))
            if new_path == "":
                new_path = "/"
            update_listbox(new_path)
        else:
            new_path = current_path.rstrip('/') + '/' + selection.rstrip('/')
            update_listbox(new_path)
    
    def on_ok():
        root.selected_path = current_path
        root.destroy()
    
    # Create UI elements
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    path_label = ttk.Label(main_frame, text=f"Current Path: {current_path}")
    path_label.grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
    
    listbox_frame = ttk.Frame(main_frame)
    listbox_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
    
    scrollbar = Scrollbar(listbox_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = Listbox(listbox_frame, yscrollcommand=scrollbar.set, width=70, height=20)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    listbox.bind('<Double-Button-1>', on_select)
    
    scrollbar.config(command=listbox.yview)
    
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=10)
    
    ok_button = ttk.Button(button_frame, text="Select This Folder", command=on_ok)
    ok_button.pack(side=tk.LEFT, padx=10)
    
    cancel_button = ttk.Button(button_frame, text="Cancel", command=root.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10)
    
    # Configure grid weights
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    
    # Initial population
    update_listbox(current_path)
    
    root.mainloop()
    
    return getattr(root, 'selected_path', None)

def get_password_with_stars(prompt="Password: "):
    """Get password input with * symbols instead of blank"""
    if sys.platform == "win32":
        # Windows doesn't support getpass with custom prompt characters easily
        # So we'll use a simple approach for Windows
        import msvcrt
        print(prompt, end='', flush=True)
        password = []
        while True:
            ch = msvcrt.getch()
            if ch in [b'\r', b'\n']:  # Enter key
                print()
                break
            elif ch == b'\x08':  # Backspace
                if password:
                    password.pop()
                    print('\b \b', end='', flush=True)
            else:
                password.append(ch.decode('utf-8'))
                print('*', end='', flush=True)
        return ''.join(password)
    else:
        # For Unix/Linux/Mac, we can use a more sophisticated approach
        import termios
        import tty
        
        print(prompt, end='', flush=True)
        password = []
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ['\r', '\n']:  # Enter key
                    print()
                    break
                elif ch == '\x7f':  # Backspace
                    if password:
                        password.pop()
                        print('\b \b', end='', flush=True)
                elif ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    password.append(ch)
                    print('*', end='', flush=True)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ''.join(password)

def get_monitoring_interval():
    """Get monitoring interval from user with predefined options"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}Monitoring Interval Selection{Colors.END}")
    print(f"{Colors.YELLOW}Please choose a monitoring interval:{Colors.END}")
    print(f"{Colors.CYAN}1. 1 minute (frequent checks){Colors.END}")
    print(f"{Colors.CYAN}2. 5 minutes (balanced){Colors.END}")
    print(f"{Colors.CYAN}3. 20 minutes (less frequent){Colors.END}")
    print(f"{Colors.CYAN}4. 60 minutes (infrequent){Colors.END}")
    print(f"{Colors.CYAN}5. Custom interval{Colors.END}")
    
    while True:
        choice = input(f"\n{Colors.CYAN}Enter your choice (1-5): {Colors.END}").strip()
        
        if choice == '1':
            return 60  # 1 minute in seconds
        elif choice == '2':
            return 300  # 5 minutes in seconds
        elif choice == '3':
            return 1200  # 20 minutes in seconds
        elif choice == '4':
            return 3600  # 60 minutes in seconds
        elif choice == '5':
            return get_custom_interval()
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 1-5.{Colors.END}")

def get_custom_interval():
    """Get custom interval from user"""
    print(f"\n{Colors.HEADER}Custom Interval Selection{Colors.END}")
    print(f"{Colors.YELLOW}Choose time unit:{Colors.END}")
    print(f"{Colors.CYAN}1. Seconds{Colors.END}")
    print(f"{Colors.CYAN}2. Minutes{Colors.END}")
    print(f"{Colors.CYAN}3. Hours{Colors.END}")
    
    while True:
        unit_choice = input(f"{Colors.CYAN}Enter your choice (1-3): {Colors.END}").strip()
        
        if unit_choice in ['1', '2', '3']:
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 1-3.{Colors.END}")
    
    # Get the interval value
    while True:
        try:
            value = input(f"{Colors.CYAN}Enter the interval value: {Colors.END}").strip()
            interval_value = float(value)
            
            if interval_value <= 0:
                print(f"{Colors.RED}Interval must be greater than 0.{Colors.END}")
                continue
                
            # Convert to seconds based on unit
            if unit_choice == '1':  # Seconds
                return int(interval_value)
            elif unit_choice == '2':  # Minutes
                return int(interval_value * 60)
            elif unit_choice == '3':  # Hours
                return int(interval_value * 3600)
                
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.END}")

def get_user_input():
    """Get configuration from user"""
    config = {}
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== SFTP/FTP File Sync Tool ==={Colors.END}")
    
    # Protocol selection - default to SFTP
    protocol = input(f"{Colors.CYAN}Use SFTP? (y/n, default y): {Colors.END}").lower().strip()
    config['use_sftp'] = not protocol.startswith('n') if protocol else True
    
    # Server details
    config['host'] = input(f"{Colors.CYAN}Server host: {Colors.END}").strip()
    default_port = 22 if config['use_sftp'] else 21
    port_input = input(f"{Colors.CYAN}Port (default {default_port}): {Colors.END}").strip()
    config['port'] = int(port_input) if port_input else default_port
    config['username'] = input(f"{Colors.CYAN}Username: {Colors.END}").strip()
    
    # Get password with * masking
    config['password'] = get_password_with_stars(f"{Colors.CYAN}Password: {Colors.END}")
    
    # Get monitoring interval
    config['interval'] = get_monitoring_interval()
    
    # Validate credentials and get remote folder
    ftp_client = FTPClient(
        config['host'], config['username'], config['password'],
        config['port'], config['use_sftp']
    )
    
    if not ftp_client.connect():
        print(f"{Colors.RED}Failed to connect with provided credentials. Please check your settings.{Colors.END}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}Connected successfully! Please select a remote folder...{Colors.END}")
    config['remote_folder'] = select_remote_folder(ftp_client)
    ftp_client.disconnect()
    
    if not config['remote_folder']:
        print(f"{Colors.RED}No remote folder selected. Exiting.{Colors.END}")
        sys.exit(1)
    
    # Normalize remote path
    config['remote_folder'] = config['remote_folder'].replace('\\', '/')
    print(f"{Colors.GREEN}Selected remote folder: {config['remote_folder']}{Colors.END}")
    
    # Get local folder
    print(f"{Colors.GREEN}Please select a local folder...{Colors.END}")
    config['local_folder'] = browse_local_folder()
    
    if not config['local_folder']:
        print(f"{Colors.RED}No local folder selected. Exiting.{Colors.END}")
        sys.exit(1)
    
    # Monitoring direction with clear explanation - FIXED LOGIC
    print(f"\n{Colors.HEADER}Monitoring Direction Options:{Colors.END}")
    print(f"{Colors.YELLOW}1. REMOTE monitoring: Watch the remote server for changes and download them locally{Colors.END}")
    print(f"{Colors.YELLOW}2. LOCAL monitoring: Watch your local folder for changes and upload them to the server{Colors.END}")

    direction = input(f"\n{Colors.CYAN}Enter 'remote' or 'local' to choose monitoring direction: {Colors.END}").lower().strip()

    # Default to REMOTE monitoring if no input
    if not direction:
        print(f"{Colors.YELLOW}No direction selected. Defaulting to REMOTE monitoring.{Colors.END}")
        config['monitor_remote'] = True
    else:
        # Set based on user input - 'remote' or anything starting with 'r' = True, else False
        config['monitor_remote'] = direction
