#!/usr/bin/env python3
"""
UI module for SSH GitHub Configurator
Contains the main GUI interface with improved error handling and user feedback
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from pathlib import Path
import platform

from ssh_manager import SSHManager, SSHKeyError
from utils import safe_execute, ErrorHandler, ClipboardManager
from logger import app_logger


class SSHGitHubConfiguratorUI:
    """Main UI class for the SSH GitHub Configurator"""
    
    def __init__(self, root):
        self.root = root
        self.ssh_manager = SSHManager()
        self.error_handler = ErrorHandler()
        self.style = ttk.Style()
        self.style.theme_use("clam") # Use 'clam' theme as a base

        # Configure a red button style for danger actions
        self.style.configure("Danger.TButton", foreground="white", background="#dc3545", font=("Arial", 10, "bold"))
        self.style.map("Danger.TButton",
            background=[('active', '#c82333'), ('pressed', '#bd2130')],
            foreground=[('active', 'white'), ('pressed', 'white')]
        )
        
        # Log system info for debugging
        self.error_handler.log_system_info()
        
        self.setup_window()
        self.setup_styles()
        self.create_interface()
        self._display_found_ssh_keys()
        
        # Initialize application state
        self.current_pubkey_content = ""
        
        # Try to get user's git email for default
        try:
            import subprocess
            result = subprocess.run(['git', 'config', '--global', 'user.email'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                self.email_entry.insert(0, result.stdout.strip())
        except Exception:
            pass  # Ignore if git is not available
        
        # Check for existing keys on startup
        self.check_existing_keys()
    
    def setup_window(self):
        """Configure main window properties with size limits, maximize disabled, and start maximized"""
        try:
            self.root.title("SSH GitHub Configurator")
            
            # Set minimum and maximum window size
            min_width, min_height = 600, 500
            max_width, max_height = 800, 700
            
            self.root.minsize(min_width, min_height)
            self.root.maxsize(max_width, max_height)
            
            # Allow resizing within limits
            self.root.resizable(True, True)
            
            # Start maximized
            if platform.system() == "Windows":
                self.root.state('zoomed') # Maximized state for Windows
            else:
                # For other systems, try to set fullscreen or a large geometry
                self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
                
            # Disable maximize button using Windows API
            try:
                if platform.system() == "Windows":
                    # Use Windows API to disable maximize button
                    import ctypes
                    from ctypes import wintypes
                    
                    # Wait for window to be created
                    self.root.update()
                    
                    # Get window handle
                    hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                    if hwnd == 0:
                        hwnd = self.root.winfo_id()
                    
                    # Get current window style
                    style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)  # GWL_STYLE
                    
                    # Remove maximize box (WS_MAXIMIZEBOX = 0x10000)
                    style = style & ~0x10000
                    
                    # Apply new style
                    ctypes.windll.user32.SetWindowLongPtrW(hwnd, -16, style)
                    
                    # Force window to redraw
                    ctypes.windll.user32.SetWindowPos(
                        hwnd, 0, 0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0004 | 0x0020  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED
                    )
                    
                    app_logger.info("Maximize button disabled on Windows")
                else:
                    # For non-Windows systems, try alternative methods
                    try:
                        self.root.attributes('-type', 'dialog')
                    except:
                        pass
                    app_logger.info("Window configured for non-Windows system")
                    
            except Exception as e:
                app_logger.warning(f"Could not disable maximize button: {e}")
                # Continue without disabling maximize button
            
            # Center window on screen (only if not maximized)
            if platform.system() != "Windows": # Windows 'zoomed' handles centering
                self.root.update_idletasks()
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                x = (screen_width // 2) - (min_width // 2) # Use min_width for centering if not maximized
                y = (screen_height // 2) - (min_height // 2)
                self.root.geometry(f"{min_width}x{min_height}+{x}+{y}")
            
            # Set window icon (if available)
            try:
                # You can add an icon file here if desired
                pass
            except Exception:
                pass
            
            app_logger.info(f"Main window configured: {min_width}x{min_height} to {max_width}x{max_height}, starting maximized")
            
        except Exception as e:
            app_logger.error(f"Failed to setup window: {e}", exc_info=True)
    
    def _on_focus(self, event=None):
        """Handle window focus events"""
        # This can be used for additional window management if needed
        pass
    
    def setup_styles(self):
        """Configure styles for GitHub-like appearance"""
        try:
            style = ttk.Style()
            
            # Configure button styles
            style.configure("Success.TButton", foreground="white", background="#28a745")
            style.configure("Danger.TButton", foreground="white", background="#dc3545")
            style.configure("Primary.TButton", foreground="white", background="#0366d6")
            style.configure("Warning.TButton", foreground="white", background="#ffc107")
            
            app_logger.debug("UI styles configured")
            
        except Exception as e:
            app_logger.error(f"Failed to setup styles: {e}", exc_info=True)
    
    def create_interface(self):
        """Create the main interface"""
        try:
            # Main frame with padding
            self.root.grid_rowconfigure(0, weight=1)
            self.root.grid_columnconfigure(0, weight=1)
            
            # Create a main canvas to hold the scrollable content
            self.main_canvas = tk.Canvas(self.root)
            self.main_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
            
            # Create a scrollbar and link it to the canvas
            self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
            self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
            
            # Create a frame inside the canvas to hold the actual UI content
            main_frame = ttk.Frame(self.main_canvas, padding="20")
            self.main_frame_id = self.main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
            
            # Configure the canvas scrolling
            main_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
            self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.main_canvas.bind("<Configure>", lambda e: self.main_canvas.itemconfigure(self.main_frame_id, width=e.width))
            
            # Title
            title_label = ttk.Label(main_frame, text="SSH GitHub Configurator", 
                                   font=("Arial", 16, "bold"))
            title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
            
            # Status frame

            # SSH Keys Display frame
            self.create_ssh_keys_display_frame(main_frame, row=2)
            
            # Key management frame
            self.create_key_management_frame(main_frame, row=3)
            
            # Public key display frame
            self.create_pubkey_frame(main_frame, row=4)
            
            # Error log frame (collapsible)
            self.create_error_log_frame(main_frame, row=6)
            
            # Configure grid weights
            main_frame.columnconfigure(0, weight=1)
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            
            app_logger.info("UI interface created successfully")
            
        except Exception as e:
            app_logger.error(f"Failed to create interface: {e}", exc_info=True)
            self.show_error_message("Interface Creation Error", str(e))

    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling for the main canvas."""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    

    def create_ssh_keys_display_frame(self, parent, row):
        """Create frame to display all found SSH keys"""
        keys_frame = ttk.LabelFrame(parent, text="Found SSH Keys", padding="10")
        keys_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Treeview for displaying keys
        self.keys_tree = ttk.Treeview(keys_frame, columns=("Type", "Private Path", "Public Path"), show="headings")
        self.keys_tree.heading("Type", text="Type")
        self.keys_tree.heading("Private Path", text="Private Path")
        self.keys_tree.heading("Public Path", text="Public Path")

        self.keys_tree.column("Type", width=100, stretch=tk.NO)
        self.keys_tree.column("Private Path", width=250, stretch=tk.YES)
        self.keys_tree.column("Public Path", width=250, stretch=tk.YES)

        self.keys_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.keys_tree.bind("<<TreeviewSelect>>", self._on_key_select)

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(keys_frame, orient=tk.VERTICAL, command=self.keys_tree.yview)
        self.keys_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        keys_frame.columnconfigure(0, weight=1)
        keys_frame.rowconfigure(0, weight=1)

        delete_button = ttk.Button(keys_frame, text="Excluir Chave Selecionada", command=self._delete_selected_ssh_key, style="Danger.TButton")
        delete_button.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        keys_frame.columnconfigure(1, weight=1)

        app_logger.info("SSH keys display frame created")

    def create_key_management_frame(self, parent, row):
        """Create key management frame"""
        key_frame = ttk.LabelFrame(parent, text="SSH Key Management", padding="10")
        key_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Email input frame
        email_frame = ttk.Frame(key_frame)
        email_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(email_frame, text="Email for SSH key:").grid(row=0, column=0, sticky=tk.W)
        self.email_entry = ttk.Entry(email_frame, width=40)
        self.email_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Key Name input frame
        key_name_frame = ttk.Frame(key_frame)
        key_name_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(key_name_frame, text="Key Name (optional, e.g., 'github_personal'):").grid(row=0, column=0, sticky=tk.W)
        self.key_name_entry = ttk.Entry(key_name_frame, width=40)
        self.key_name_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Passphrase input frame
        passphrase_frame = ttk.Frame(key_frame)
        passphrase_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.use_passphrase_var = tk.BooleanVar(value=False)
        self.use_passphrase_checkbox = ttk.Checkbutton(passphrase_frame, text="Usar Passphrase (será solicitada no terminal)", variable=self.use_passphrase_var)
        self.use_passphrase_checkbox.grid(row=0, column=0, sticky=tk.W, pady=(5, 0))

        # Generate button with progress indicator
        button_frame = ttk.Frame(key_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        self.generate_button = ttk.Button(button_frame, text="Generate New SSH Key", 
                                         command=self.generate_key_safe)
        self.generate_button.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Progress bar (initially hidden)
        self.progress_bar = ttk.Progressbar(button_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=1, padx=(10, 0), sticky=(tk.W, tk.E))
        self.progress_bar.grid_remove()  # Hide initially
        
        email_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(0, weight=1)
    
    def create_pubkey_frame(self, parent, row):
        """Create public key display frame"""
        pubkey_frame = ttk.LabelFrame(parent, text="Public Key", padding="10")
        pubkey_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Public key text area with better formatting
        self.pubkey_text = scrolledtext.ScrolledText(pubkey_frame, height=4, width=70, 
                                                    state=tk.DISABLED, wrap=tk.WORD,
                                                    font=("Courier", 9))
        self.pubkey_text.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Button frame
        button_frame = ttk.Frame(pubkey_frame)
        button_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Copy button
        self.copy_button = ttk.Button(button_frame, text="Copy to Clipboard", 
                                     command=self.copy_to_clipboard_safe, state=tk.DISABLED)
        self.copy_button.grid(row=0, column=0, sticky=tk.W)
        
        # Key info label
        self.key_info_label = ttk.Label(button_frame, text="", font=("Arial", 8))
        self.key_info_label.grid(row=0, column=1, padx=(20, 0), sticky=(tk.W, tk.E))
        
        pubkey_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
    

    def create_error_log_frame(self, parent, row):
        """Create collapsible error log frame"""
        self.error_frame = ttk.LabelFrame(parent, text="Debug Information", padding="10")
        self.error_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.error_frame.grid_remove()  # Hide initially
        
        # Toggle button
        self.toggle_error_button = ttk.Button(parent, text="Show Debug Info", 
                                            command=self.toggle_error_log)
        self.toggle_error_button.grid(row=row+1, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        # Error text area
        self.error_text = scrolledtext.ScrolledText(self.error_frame, height=6, width=70,
                                                   font=("Courier", 8), state=tk.DISABLED)
        self.error_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.error_frame.columnconfigure(0, weight=1)
    
    def _display_found_ssh_keys(self):
        """Populate the Treeview with found SSH keys"""
        try:
            self.keys_tree.delete(*self.keys_tree.get_children()) # Clear existing entries
            
            found_keys = self.ssh_manager.find_all_ssh_keys()
            
            if not found_keys:
                self.keys_tree.insert("", tk.END, values=("Nenhuma chave SSH encontrada", "", ""))
                return
            
            for key_info in found_keys:
                self.keys_tree.insert("", tk.END, values=(
                    key_info.get("type", "Unknown"),
                    key_info.get("private_path", "N/A"),
                    key_info.get("public_path", "N/A")
                ))
            app_logger.info("SSH keys displayed in UI")
        except Exception as e:
            app_logger.error(f"Failed to display SSH keys: {e}", exc_info=True)
            self.show_error_message("Display Keys Error", str(e))

    def _delete_selected_ssh_key(self):
        """
        Handles the deletion of a selected SSH key pair from the UI.
        """
        selected_item = self.keys_tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Chave Selecionada", "Por favor, selecione uma chave SSH para excluir.")
            return

        values = self.keys_tree.item(selected_item, "values")
        private_path_str = values[1]
        public_path_str = values[2]

        if not private_path_str or not public_path_str:
            messagebox.showerror("Erro", "Não foi possível obter os caminhos da chave selecionada.")
            return

        private_path = Path(private_path_str)
        public_path = Path(public_path_str)

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a chave SSH:\nPrivada: {private_path.name}\nPública: {public_path.name}?"):
            try:
                self.ssh_manager.delete_ssh_key(private_path, public_path)
                messagebox.showinfo("Sucesso", "Chave SSH excluída com sucesso!")
                self._display_found_ssh_keys() # Refresh the list
            except SSHKeyError as e:
                messagebox.showerror("Erro de Exclusão", f"Falha ao excluir a chave SSH: {e}")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro inesperado: {e}")

    def toggle_error_log(self):
        """Toggle error log visibility"""
        try:
            if self.error_frame.winfo_viewable():
                self.error_frame.grid_remove()
                self.toggle_error_button.config(text="Show Debug Info")
            else:
                self.error_frame.grid()
                self.toggle_error_button.config(text="Hide Debug Info")
        except Exception as e:
            app_logger.error(f"Error toggling debug info: {e}")
    
    def add_debug_message(self, message: str):
        """Add message to debug log"""
        try:
            self.error_text.config(state=tk.NORMAL)
            self.error_text.insert(tk.END, f"{message}\n")
            self.error_text.see(tk.END)
            self.error_text.config(state=tk.DISABLED)
        except Exception:
            pass  # Fail silently for debug messages
    
    def show_error_message(self, title: str, message: str):
        """Show error message to user with logging"""
        try:
            app_logger.error(f"User error - {title}: {message}")
            self.add_debug_message(f"ERROR: {title} - {message}")
            messagebox.showerror(title, message)
        except Exception as e:
            app_logger.critical(f"Failed to show error message: {e}", exc_info=True)
    
    def show_success_message(self, title: str, message: str):
        """Show success message to user"""
        try:
            app_logger.info(f"Success - {title}: {message}")
            self.add_debug_message(f"SUCCESS: {title} - {message}")
            messagebox.showinfo(title, message)
        except Exception as e:
            app_logger.error(f"Failed to show success message: {e}")

    def start_generation_ui(self):
        """Update UI to show key generation in progress"""
        self.generate_button.config(state=tk.DISABLED)
        self.progress_bar.grid()
        self.progress_bar.start()
        self.add_debug_message("UI updated: Key generation started.")

    def generation_error(self, title: str, message: str):
        """Handle key generation error and update UI"""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.generate_button.config(state=tk.NORMAL)
        self.show_error_message(title, message)
        self.add_debug_message(f"UI updated: Key generation failed with error: {message}")

    def generation_success(self, result):
        """Handle successful key generation and update UI"""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.generate_button.config(state=tk.NORMAL)
        self.show_success_message("Key Generation Success", result)
        self.add_debug_message(f"UI updated: Key generation successful: {result}")
        self._display_found_ssh_keys() # Refresh the key list
    
    @safe_execute(show_error=True)
    def check_existing_keys(self):
        """Check for existing SSH keys with error handling"""
        try:
            self.add_debug_message("Checking for existing SSH keys...")
            
            key_info = self.ssh_manager.check_existing_keys()
            
            if key_info['found']:
                key_type = key_info['type']
                self.load_public_key(key_info['public_path'])
                self.add_debug_message(f"Found existing {key_type} key")
            else:
                self.generate_button.config(state=tk.NORMAL)
                self.add_debug_message("No existing SSH keys found")
                
        except SSHKeyError as e:
            self.show_error_message("SSH Key Check Error", str(e))
        except Exception as e:
            error_msg = self.error_handler.handle_exception(e, "check_existing_keys")
            self.show_error_message("Unexpected Error", error_msg)
    
    @safe_execute(show_error=True)
    def load_public_key(self, pubkey_path: Path):
        """Load and display public key with error handling"""
        try:
            self.add_debug_message(f"Loading public key from: {pubkey_path}")
            
            pubkey_content = self.ssh_manager.load_public_key(pubkey_path)
            self.current_pubkey_content = pubkey_content
            
            # Display key in text area
            self.pubkey_text.config(state=tk.NORMAL)
            self.pubkey_text.delete(1.0, tk.END)
            self.pubkey_text.insert(1.0, pubkey_content)
            self.pubkey_text.config(state=tk.DISABLED)
            
            # Enable copy button
            self.copy_button.config(state=tk.NORMAL)
            
            # Show key info
            key_parts = pubkey_content.split()
            if len(key_parts) >= 2:
                key_type = key_parts[0]
                key_size = len(key_parts[1])
                self.key_info_label.config(text=f"Type: {key_type}, Size: {key_size} chars")
            
            self.add_debug_message("Public key loaded successfully")
            
        except SSHKeyError as e:
            self.show_error_message("Public Key Error", str(e))
        except Exception as e:
            error_msg = self.error_handler.handle_exception(e, "load_public_key")
            self.show_error_message("Load Key Error", error_msg)
    
    def generate_key_safe(self):
        """Safely generate SSH key with improved user options"""
        try:
            # Get user email from entry field
            email = self.email_entry.get().strip()
            if not email:
                messagebox.showwarning("Email Required", "Please enter your email address for the SSH key.")
                return
            
            key_name = self.key_name_entry.get().strip()
            use_passphrase = self.use_passphrase_var.get() # Get state of checkbox
            passphrase = None if use_passphrase else "" # Pass None if checkbox is checked, else empty string

            # Determine the path of the key to be generated/checked
            ssh_dir = Path.home() / ".ssh"
            key_file_exists = False
            key_to_check_name = None

            if key_name:
                key_to_check_name = key_name
                key_file_exists = (ssh_dir / key_name).exists()
            else:
                # If no key_name, check for default keys
                if (ssh_dir / "id_ed25519").exists():
                    key_to_check_name = "id_ed25519"
                    key_file_exists = True
                elif (ssh_dir / "id_rsa").exists():
                    key_to_check_name = "id_rsa"
                    key_file_exists = True
                else:
                    # No key_name and no default keys, so a key_name is required
                    messagebox.showwarning("Key Name Required", "Please provide a Key Name to create a new key.")
                    return

            overwrite = False
            if key_file_exists:
                response = messagebox.askyesnocancel(
                    "Existing SSH Key Found",
                    f"A chave SSH '{key_to_check_name}' já existe. "
                    "Deseja sobrescrevê-la? "
                    "Isso removerá a chave existente e criará uma nova."
                    "\n\nSim: Sobrescrever chave existente\n"
                    "Não: Manter chave existente (a geração será ignorada)\n"
                    "Cancelar: Cancelar a operação"
                )

                if response is None:  # Cancel
                    return
                elif response:  # Yes - overwrite
                    overwrite = True
                else:  # No - keep existing
                    messagebox.showinfo(
                        "Keys Preserved",
                        f"A chave SSH '{key_to_check_name}' foi preservada. Você pode usá-la para conectar ao GitHub."
                    )
                    return

            self.add_debug_message("Starting SSH key generation...")
            
            # Update UI to show progress
            self.start_generation_ui()
            
            # Generate key in separate thread
            def generation_worker():
                try:
                    result = self.ssh_manager.generate_ssh_key(
                        email=email, 
                        passphrase=passphrase,
                        use_passphrase=use_passphrase,
                        overwrite=overwrite,
                        key_name=key_name
                    )
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.generation_success(result))

                except SSHKeyError as e:
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.generation_error("SSH Key Generation Error", msg))
                except Exception as e:
                    error_msg = f"Unexpected error: {e}"
                    self.root.after(0, lambda msg=error_msg: self.generation_error("Unexpected Generation Error", msg))
            
            # Start generation in background thread
            threading.Thread(target=generation_worker, daemon=True).start()
            
        except Exception as e:
            self.generation_error("Generation Setup Error", f"Failed to start key generation: {e}")

    def _on_key_select(self, event):
        selected_item = self.keys_tree.focus()
        if selected_item:
            item_values = self.keys_tree.item(selected_item, 'values')
            if item_values:
                key_path = item_values[1]  # Assuming the path is the second column
                try:
                    with open(key_path + ".pub", 'r') as f:
                        pubkey_content = f.read()
                    self.pubkey_text.config(state=tk.NORMAL)
                    self.pubkey_text.delete(1.0, tk.END)
                    self.pubkey_text.insert(tk.END, pubkey_content)
                    self.pubkey_text.config(state=tk.DISABLED)
                except FileNotFoundError:
                    self.pubkey_text.delete(1.0, tk.END)
                    self.pubkey_text.insert(tk.END, "Public key file not found.")
                except Exception as e:
                    self.pubkey_text.delete(1.0, tk.END)
                    self.pubkey_text.insert(tk.END, f"Error reading public key: {e}")    
    @safe_execute(show_error=True)
    def copy_to_clipboard_safe(self):
        """Safely copy public key to clipboard"""
        try:
            if not self.current_pubkey_content:
                self.show_error_message("Copy Error", "No public key available to copy")
                return
            
            success = ClipboardManager.copy_to_clipboard(self.current_pubkey_content, self.root)
            
            if success:
                self.show_success_message("Success", "Public key copied to clipboard!")
                self.add_debug_message("Public key copied to clipboard")
            else:
                self.show_error_message("Clipboard Error", "Failed to copy to clipboard. Please copy manually.")
                
        except Exception as e:
            error_msg = self.error_handler.handle_exception(e, "copy_to_clipboard")
            self.show_error_message("Clipboard Error", error_msg)
    
                

    
    def test_error(self, title: str, message: str):
        """Handle connection test error"""
        try:
            self.test_progress_bar.stop()
            self.test_progress_bar.grid_remove()
            self.test_button.config(state=tk.NORMAL, text="Test GitHub Connection")
            self.test_result_label.config(text="❌ Connection test failed", foreground="red")
            
            self.show_error_message(title, message)
            
        except Exception as e:
            app_logger.error(f"Error in test_error: {e}", exc_info=True)