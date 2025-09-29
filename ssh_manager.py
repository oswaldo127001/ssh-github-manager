#!/usr/bin/env python3
"""
SSH Manager module for SSH GitHub Configurator
Handles all SSH key operations including detection, generation, and testing
"""

import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple, Dict
from logger import app_logger
import os


class SSHKeyError(Exception):
    """Custom exception for SSH key operations"""
    pass


class SSHManager:
    """Manages SSH key operations"""
    
    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self._ensure_ssh_directory()
    
    def _ensure_ssh_directory(self):
        """Ensure SSH directory exists with proper permissions"""
        try:
            if not self.ssh_dir.exists():
                app_logger.info(f"Creating SSH directory: {self.ssh_dir}")
                self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
            else:
                # Check permissions on existing directory
                if platform.system() != "Windows":
                    current_mode = oct(self.ssh_dir.stat().st_mode)[-3:]
                    if current_mode != "700":
                        app_logger.warning(f"SSH directory has permissions {current_mode}, should be 700")
        except Exception as e:
            app_logger.error(f"Failed to create/check SSH directory: {e}", exc_info=True)
            raise SSHKeyError(f"Cannot access SSH directory: {e}")
    
    def check_existing_keys(self) -> Dict[str, any]:
        """
        Check for existing SSH keys
        Returns dict with key info: {'found': bool, 'type': str, 'path': Path}
        """
        try:
            app_logger.info("Checking for existing SSH keys")
            
            # Check for ed25519 key
            ed25519_private = self.ssh_dir / "id_ed25519"
            ed25519_public = self.ssh_dir / "id_ed25519.pub"
            
            # Check for RSA key
            rsa_private = self.ssh_dir / "id_rsa"
            rsa_public = self.ssh_dir / "id_rsa.pub"
            
            if ed25519_private.exists() and ed25519_public.exists():
                app_logger.info("Found ed25519 key pair")
                return {
                    'found': True,
                    'type': 'ed25519',
                    'private_path': ed25519_private,
                    'public_path': ed25519_public
                }
            elif rsa_private.exists() and rsa_public.exists():
                app_logger.info("Found RSA key pair")
                return {
                    'found': True,
                    'type': 'RSA',
                    'private_path': rsa_private,
                    'public_path': rsa_public
                }
            else:
                app_logger.info("No SSH key pairs found")
                return {'found': False}

        except Exception as e:
            app_logger.error(f"Error checking existing keys: {e}", exc_info=True)
            raise SSHKeyError(f"Failed to check existing keys: {e}")

    def find_all_ssh_keys(self) -> list[Dict[str, Path]]:
        """
        Finds all SSH key pairs (private and public) in the .ssh directory.
        Returns a list of dictionaries, each containing 'private_path' and 'public_path'.
        """
        app_logger.info(f"Searching for SSH keys in {self.ssh_dir}")
        found_keys = []
        try:
            for private_key_path in self.ssh_dir.iterdir():
                if private_key_path.is_file() and not private_key_path.suffix == '.pub' and private_key_path.name not in ["known_hosts", "config"]:
                    public_key_path = private_key_path.with_suffix('.pub')
                    if public_key_path.is_file():
                        key_type = "unknown"
                        try:
                            with open(public_key_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if "ssh-rsa" in content:
                                    key_type = "RSA"
                                elif "ssh-ed25519" in content:
                                    key_type = "ED25519"
                                elif "ecdsa" in content:
                                    key_type = "ECDSA"
                        except Exception as e:
                            app_logger.warning(f"Could not determine key type for {public_key_path}: {e}")

                        found_keys.append({
                            'type': key_type,
                            'private_path': private_key_path,
                            'public_path': public_key_path
                        })
                        app_logger.info(f"Found SSH key pair: {private_key_path} ({key_type})")
            return found_keys
        except Exception as e:
            app_logger.error(f"Error finding all SSH keys: {e}", exc_info=True)
            raise SSHKeyError(f"Failed to find all SSH keys: {e}")

    def load_public_key(self, pubkey_path: Path) -> str:
        """Load public key content from file"""
        try:
            app_logger.info(f"Loading public key from: {pubkey_path}")

            if not pubkey_path.exists():
                raise SSHKeyError(f"Public key file not found: {pubkey_path}")

            with open(pubkey_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                raise SSHKeyError("Public key file is empty")

            app_logger.info("Public key loaded successfully")
            return content

        except Exception as e:
            app_logger.error(f"Failed to load public key: {e}", exc_info=True)
            raise SSHKeyError(f"Cannot read public key: {e}")
    
    def delete_ssh_key(self, private_key_path: Path, public_key_path: Path):
        """
        Deletes a given SSH key pair (private and public).
        
        Args:
            private_key_path: The path to the private SSH key file.
            public_key_path: The path to the public SSH key file.
        """
        app_logger.info(f"Attempting to delete SSH key pair: {private_key_path} and {public_key_path}")
        try:
            if private_key_path.exists():
                private_key_path.unlink()
                app_logger.info(f"Deleted private key: {private_key_path}")
            else:
                app_logger.warning(f"Private key not found, skipping deletion: {private_key_path}")
            
            if public_key_path.exists():
                public_key_path.unlink()
                app_logger.info(f"Deleted public key: {public_key_path}")
            else:
                app_logger.warning(f"Public key not found, skipping deletion: {public_key_path}")
            
            app_logger.info("SSH key pair deletion process completed.")
        except Exception as e:
            app_logger.error(f"Error deleting SSH key pair: {e}", exc_info=True)
            raise SSHKeyError(f"Failed to delete SSH key pair: {e}")

    def check_command_availability(self, command: str) -> bool:
        """Check if a command is available in the system"""
        try:
            app_logger.debug(f"Checking availability of command: {command}")
            
            if platform.system() == "Windows":
                result = subprocess.run(["where", command], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10)
            else:
                result = subprocess.run(["which", command], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10)
            
            available = result.returncode == 0
            app_logger.debug(f"Command {command} available: {available}")
            return available
            
        except subprocess.TimeoutExpired:
            app_logger.warning(f"Timeout checking command availability: {command}")
            return False
        except Exception as e:
            app_logger.error(f"Error checking command availability: {e}", exc_info=True)
            return False
    
    def generate_ssh_key(self, email: str = None, passphrase: str = "", use_passphrase: bool = False, overwrite: bool = False, key_name: str = None) -> Dict[str, any]:
        """
        Generate SSH key following GitHub best practices
        
        Args:
            email: Email for key comment (if None, will prompt user)
            passphrase: Passphrase for the key. If None, interactive input will be used.
            use_passphrase: Whether to use a passphrase for the key (deprecated, now inferred from 'passphrase' argument)
            overwrite: Whether to overwrite existing keys
            key_name: Optional name for the key file (e.g., 'github_key'). If None, uses default 'id_ed25519' or 'id_rsa'.
        """
        try:
            app_logger.info("Starting SSH key generation process")
            
            # Ensure SSH directory exists with proper permissions
            self._ensure_ssh_directory()
            
            # Check if ssh-keygen is available
            if not self.check_command_availability("ssh-keygen"):
                raise SSHKeyError("ssh-keygen command not found. Please install OpenSSH.")
            
            # Use provided email or generate a default one
            if not email:
                try:
                    import getpass
                    username = getpass.getuser()
                    hostname = platform.node()
                    email = f"{username}@{hostname}"
                except Exception:
                    email = "user@localhost"
            
            app_logger.info(f"Using email for key comment: {email}")
            
            # If passphrase is None, it means interactive input is desired
            if passphrase is None:
                app_logger.info("Abrindo novo terminal para entrada interativa da passphrase...")
                
                # Construct the ssh-keygen command for interactive input
                keygen_cmd_parts = [
                    "ssh-keygen",
                    "-t", "ed25519", # Default to ed25519 for interactive
                    "-C", email,
                    "-f", str(self.ssh_dir / (key_name or "id_ed25519"))
                ]
                
                # Add overwrite flag if necessary
                if overwrite:
                    keygen_cmd_parts.append("-f")
                    keygen_cmd_parts.append(str(self.ssh_dir / (key_name or "id_ed25519")))
                    keygen_cmd_parts.append("-N")
                    keygen_cmd_parts.append("") # Empty passphrase to allow interactive input

                # Convert command parts to a single string for shell execution
                keygen_cmd_str = ' '.join(f'"{arg}"' if ' ' in arg or '=' in arg else arg for arg in keygen_cmd_parts)

                if platform.system() == "Windows":
                    # Use powershell for Windows
                    full_command = f"{keygen_cmd_str}; Read-Host -Prompt \"Pressione Enter para fechar\""
                    subprocess.Popen(["powershell.exe", "-NoExit", "-Command", full_command], cwd=self.ssh_dir)
                else:
                    # Use xterm or gnome-terminal for Linux/macOS
                    full_command = f"{keygen_cmd_str}; bash -c \"read -p \"Pressione Enter para fechar\"\""
                    terminal_cmd = ["xterm", "-e", full_command]
                    try:
                        subprocess.Popen(terminal_cmd, cwd=self.ssh_dir)
                    except FileNotFoundError:
                        terminal_cmd[0] = "gnome-terminal"
                        subprocess.Popen(terminal_cmd, cwd=self.ssh_dir)
                
                # Return a special status indicating interactive generation
                return {"success": True, "interactive": True, "message": "Geração de chave interativa iniciada. Por favor, insira a passphrase no novo terminal."}
            else:
                # Non-interactive passphrase input
                # Try ed25519 first (recommended by GitHub)
                try:
                    return self._generate_key_type("ed25519", email, passphrase=passphrase, overwrite=overwrite, key_name=key_name)
                except SSHKeyError as e:
                    app_logger.warning(f"ed25519 generation failed: {e}")
                    
                    # Only fallback to RSA if ed25519 is not supported, not if keys exist
                    if "already exists" not in str(e).lower():
                        app_logger.info("Falling back to RSA key generation")
                        try:
                            return self._generate_key_type("rsa", email, passphrase=passphrase, overwrite=overwrite, key_name=key_name)
                        except SSHKeyError as rsa_error:
                            app_logger.error(f"RSA generation also failed: {rsa_error}")
                            raise SSHKeyError(f"Failed to generate both ed25519 and RSA keys: {rsa_error}")
                    else:
                        # If keys exist, don't fallback, just raise the original error
                        raise e
                        
        except Exception as e:
            app_logger.error(f"Unexpected error during key generation: {e}", exc_info=True)
            raise SSHKeyError(f"Key generation failed: {e}")
    
    def _generate_key_type(self, key_type: str, email: str, passphrase: str = "", overwrite: bool = False, key_name: str = None) -> Dict[str, any]:
        """Generate specific type of SSH key"""
        try:
            if key_name:
                private_path = self.ssh_dir / key_name
                public_path = self.ssh_dir / f"{key_name}.pub"
            elif key_type == "ed25519":
                private_path = self.ssh_dir / "id_ed25519"
                public_path = self.ssh_dir / "id_ed25519.pub"
            elif key_type == "rsa":
                private_path = self.ssh_dir / "id_rsa"
                public_path = self.ssh_dir / "id_rsa.pub"
            else:
                raise SSHKeyError(f"Unsupported key type: {key_type}")

            # Use provided passphrase or empty string if not using passphrase
            # The use_passphrase argument is now implicitly handled by checking if passphrase is provided
            cmd = [
                "ssh-keygen", "-t", key_type, "-C", email,
                "-f", str(private_path)
            ]

            if passphrase is not None: # If passphrase is not None, it means it's either an empty string or a provided passphrase
                cmd.extend([ "-N", passphrase])

            app_logger.info(f"Generating {key_type} key with command: {' '.join(cmd)}")

            # Check if key already exists
            if (private_path.exists() or public_path.exists()) and not overwrite:
                raise SSHKeyError(f"Key '{private_path.name}' already exists. Use overwrite=True to replace existing keys.")
            
            # Remove existing keys if overwrite is True
            if overwrite:
                for path in [private_path, public_path]:
                    if path.exists():
                        path.unlink()
                        app_logger.info(f"Removed existing key: {path}")
            
            # Run ssh-keygen command
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            
            # Verify key files were created
            if not private_path.exists() or not public_path.exists():
                raise SSHKeyError(f"Key files were not created: {private_path}, {public_path}")
            
            # Set proper permissions (600 for private key, 644 for public key)
            self._set_key_permissions(private_path, public_path)
            
            # Add key to ssh-agent if available
            self._add_key_to_agent(private_path, key_type)
            
            app_logger.info(f"Successfully generated {key_type} SSH key pair")
            
            return {
                "success": True,
                "key_type": key_type,
                "private_key_path": str(private_path),
                "public_key_path": str(public_path),
                "email": email,
                "message": f"Successfully generated {key_type} SSH key pair"
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"ssh-keygen failed: {e.stderr or e.stdout or str(e)}"
            app_logger.error(error_msg)
            raise SSHKeyError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "SSH key generation timed out"
            app_logger.error(error_msg)
            raise SSHKeyError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error generating {key_type} key: {e}"
            app_logger.error(error_msg, exc_info=True)
            raise SSHKeyError(error_msg)
    
    def _set_key_permissions(self, private_key_path: Path, public_key_path: Path):
        """Set proper permissions for SSH keys following security best practices"""
        try:
            if platform.system() == "Windows":
                # Windows permissions using icacls
                # Remove inheritance and set specific permissions
                
                # For private key: only current user has full control
                subprocess.run([
                    "icacls", str(private_key_path), "/inheritance:r", "/grant:r", 
                    f"{os.getlogin()}:F"
                ], check=False, capture_output=True)
                
                # For public key: current user has full control, others can read
                subprocess.run([
                    "icacls", str(public_key_path), "/inheritance:r", "/grant:r", 
                    f"{os.getlogin()}:F", "/grant:r", "Everyone:R"
                ], check=False, capture_output=True)
                
                app_logger.info("Set Windows permissions for SSH keys")
                
            else:
                # Unix-like systems: use chmod
                # Private key: 600 (read/write for owner only)
                private_key_path.chmod(0o600)
                
                # Public key: 644 (read/write for owner, read for others)
                public_key_path.chmod(0o644)
                
                # Also ensure .ssh directory has correct permissions (700)
                ssh_dir = private_key_path.parent
                ssh_dir.chmod(0o700)
                
                app_logger.info("Set Unix permissions for SSH keys (600/644) and .ssh directory (700)")
                
        except Exception as e:
            app_logger.warning(f"Could not set key permissions: {e}")
            # Continue anyway as the keys are still functional
    
    def _add_key_to_agent(self, private_key_path: Path, key_type: str):
        """Add SSH key to ssh-agent following best practices"""
        try:
            # Check if ssh-agent is running and start if needed
            if platform.system() == "Windows":
                # On Windows, ensure ssh-agent service is running
                try:
                    # Check if service exists and is running
                    result = subprocess.run([
                        "powershell", "-Command", 
                        "Get-Service ssh-agent -ErrorAction SilentlyContinue | Select-Object Status"
                    ], capture_output=True, text=True)
                    
                    if "Running" not in result.stdout:
                        # Try to start the service
                        start_result = subprocess.run([
                            "powershell", "-Command", 
                            "Start-Service ssh-agent -ErrorAction SilentlyContinue"
                        ], capture_output=True, text=True)
                        
                        if start_result.returncode == 0:
                            app_logger.info("Started ssh-agent service on Windows")
                        else:
                            app_logger.info("ssh-agent service not available on Windows, skipping key addition")
                            return
                    
                except Exception as e:
                    app_logger.warning(f"Could not manage ssh-agent service on Windows: {e}")
                    return
            else:
                # On Unix-like systems, start ssh-agent if not running
                if not os.environ.get('SSH_AUTH_SOCK'):
                    try:
                        # Try to start ssh-agent
                        result = subprocess.run(
                            ['ssh-agent', '-s'], 
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            # Parse the output to set environment variables
                            for line in result.stdout.split('\n'):
                                if 'SSH_AUTH_SOCK' in line:
                                    sock_path = line.split('=')[1].split(';')[0]
                                    os.environ['SSH_AUTH_SOCK'] = sock_path
                                elif 'SSH_AGENT_PID' in line:
                                    pid = line.split('=')[1].split(';')[0]
                                    os.environ['SSH_AGENT_PID'] = pid
                            app_logger.info("Started ssh-agent")
                        else:
                            app_logger.info("Could not start ssh-agent, skipping key addition")
                            return
                    except Exception as e:
                        app_logger.warning(f"Could not start ssh-agent: {e}")
                        return
            
            # Add key to ssh-agent
            result = subprocess.run(
                ["ssh-add", str(private_key_path)],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                app_logger.info(f"Successfully added {key_type} key to ssh-agent")
                
                # On macOS, also add to keychain if available
                if platform.system() == "Darwin":
                    try:
                        keychain_result = subprocess.run([
                            "ssh-add", "--apple-use-keychain", str(private_key_path)
                        ], capture_output=True, text=True, timeout=10)
                        
                        if keychain_result.returncode == 0:
                            app_logger.info("Successfully added key to macOS keychain")
                        else:
                            app_logger.info("Could not add key to macOS keychain (normal if no passphrase)")
                    except Exception as e:
                        app_logger.warning(f"Could not add key to macOS keychain: {e}")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                app_logger.warning(f"Could not add key to ssh-agent: {error_msg}")
                
        except Exception as e:
            app_logger.warning(f"Could not add key to ssh-agent: {e}")
    
            output = result.stderr or result.stdout or ""
            app_logger.info(f"SSH test output (exit code {result.returncode}): {output}")
            
            if result.returncode == 1 and "successfully authenticated" in output:
                # Extract username from output if available
                username = "your account"
                if "Hi " in output:
                    try:
                        username = output.split("Hi ")[1].split("!")[0]
                    except:
                        pass
                
                app_logger.info("GitHub SSH connection successful")
                return {
                    'success': True,
                    'message': f"✅ Successfully authenticated with GitHub as {username}!",
                    'output': output,
                    'username': username
                }
            else:
                # Analyze the error and provide specific guidance
                if "Permission denied (publickey)" in output:
                    guidance = "❌ Authentication failed. Please:\n1. Add your public key to GitHub (Settings → SSH and GPG keys)\n2. Ensure your key is added to ssh-agent (ssh-add ~/.ssh/id_ed25519)"
                elif "Could not resolve hostname" in output:
                    guidance = "❌ Network error. Check your internet connection and DNS settings."
                elif "Connection timed out" in output or "Connection refused" in output:
                    guidance = "❌ Connection blocked. Check firewall settings or try a different network."
                elif "No such file or directory" in output or "No such identity" in output:
                    guidance = "❌ SSH key not found. Generate an SSH key first."
                elif "Agent admitted failure to sign" in output:
                    guidance = "❌ Key not loaded in ssh-agent. Run: ssh-add ~/.ssh/id_ed25519"
                elif result.returncode == 255:
                    guidance = "❌ SSH connection failed. Verify your SSH configuration."
                else:
                    guidance = "❌ Unknown error. Verify your SSH key is correctly configured."
                
                app_logger.warning(f"GitHub SSH connection failed (exit code {result.returncode}): {output}")
                return {
                    'success': False,
                    'message': guidance,
                    'output': output,
                    'exit_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            app_logger.error("GitHub SSH connection test timed out")
            return {
                'success': False,
                'message': "❌ Connection timeout (45s). Check your internet connection or try again.",
                'output': "Connection timed out after 45 seconds"
            }
        except Exception as e:
            app_logger.error(f"Error testing GitHub connection: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"❌ Connection test error: {str(e)}",
                'output': str(e)
            }