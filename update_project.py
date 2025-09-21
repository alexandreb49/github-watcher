import subprocess
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Config(BaseModel):
    webhook_port: int = int(os.environ.get('WEBHOOK_PORT', 8080))
    webhook_secret: str = os.environ.get('WEBHOOK_SECRET', '')
    repo_url: str = os.environ.get('REPO_URL', '')
    project_dir: str = os.environ.get('PROJECT_DIR', '')
    home_dir: str = os.environ.get('HOME', '')
    ssh_key: str = os.environ.get('SSH_KEY_PATH', os.path.expanduser('~/.ssh/id_ed25519'))

    @property
    def project_path(self):
        return os.path.join(self.home_dir, self.project_dir)


def run_command(command, cwd=None, check=True):
    """Run a shell command and return result (stdout/stderr)."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    return result


def start_ssh_agent():
    """Start ssh-agent and set env vars for current Python process."""
    try:
        result = subprocess.run("ssh-agent -s", shell=True, capture_output=True, text=True, check=True)
        output = result.stdout
        for line in output.splitlines():
            if line.startswith("SSH_AUTH_SOCK"):
                sock = line.split(";")[0].split("=")[1]
                os.environ["SSH_AUTH_SOCK"] = sock
            elif line.startswith("SSH_AGENT_PID"):
                pid = line.split(";")[0].split("=")[1]
                os.environ["SSH_AGENT_PID"] = pid
        print("SSH agent started successfully")
        return True
    except Exception as e:
        print(f"Failed to start SSH agent: {e}")
        return False


def generate_ssh_key(ssh_key_path):
    """Generate a new SSH key if it doesn't exist."""
    try:
        # Create .ssh directory if it doesn't exist
        ssh_dir = os.path.dirname(ssh_key_path)
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        
        # Generate SSH key
        run_command(f'ssh-keygen -t ed25519 -f "{ssh_key_path}" -N ""')
        print(f"SSH key generated at {ssh_key_path}")
        
        # Display public key for adding to GitHub
        pub_key_path = f"{ssh_key_path}.pub"
        if os.path.exists(pub_key_path):
            with open(pub_key_path, 'r') as f:
                pub_key = f.read().strip()
            print("\n" + "="*60)
            print("🔑 ADD THIS PUBLIC KEY TO YOUR GITHUB ACCOUNT:")
            print("="*60)
            print(pub_key)
            print("="*60)
            print("1. Go to GitHub Settings > SSH and GPG keys")
            print("2. Click 'New SSH key'")
            print("3. Paste the key above")
            print("4. Save the key")
            print("="*60 + "\n")
        
        return True
    except Exception as e:
        print(f"Failed to generate SSH key: {e}")
        return False


def ensure_ssh_key(config: Config):
    """Check if SSH key exists and is loaded, otherwise create and add key."""
    # Check if SSH key file exists
    if not os.path.exists(config.ssh_key):
        print(f"SSH key not found at {config.ssh_key}")
        if not generate_ssh_key(config.ssh_key):
            return False
    
    # Check if ssh-agent is running
    if "SSH_AUTH_SOCK" not in os.environ:
        if not start_ssh_agent():
            return False
    
    try:
        # Check if key is already loaded
        result = subprocess.run("ssh-add -l", shell=True, capture_output=True, text=True)
        
        # If no keys loaded or our key is not loaded, add it
        if result.returncode != 0 or config.ssh_key not in result.stdout:
            print("Adding SSH key to agent...")
            run_command(f'ssh-add "{config.ssh_key}"')
            print("SSH key loaded successfully")
        else:
            print("SSH key already loaded")
            
    except Exception as e:
        print(f"Failed to load SSH key: {e}")
        return False
    
    return True


def test_github_connection(repo_url):
    """Test SSH connection to GitHub."""
    try:
        # Extract hostname from repo URL (github.com)
        if "github.com" in repo_url:
            result = subprocess.run(
                "ssh -T git@github.com", 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            # GitHub SSH test returns exit code 1 but with success message
            if "successfully authenticated" in result.stderr:
                print("✅ GitHub SSH connection successful")
                return True
            else:
                print("❌ GitHub SSH connection failed")
                print(f"STDERR: {result.stderr}")
                return False
    except subprocess.TimeoutExpired:
        print("❌ GitHub SSH connection timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to test GitHub connection: {e}")
        return False
    
    return True


def clone_or_update_repo(repo_url, project_path):
    """Clone repo if not exists, otherwise fetch and reset to main/master."""
    try:
        if not os.path.exists(os.path.join(project_path, ".git")):
            print("Cloning repository...")
            run_command(f"git clone {repo_url} {project_path}")
            print("Repository cloned successfully")
        else:
            print("Repository exists. Updating...")
            # Update repository
            run_command("git pull origin main", cwd=project_path)
            print("Repository updated successfully")
            
    except Exception as e:
        print(f"Failed to clone/update repository: {e}")
        raise


def run_project(project_path):
    """Ensure run.sh exists, make executable, and run it in PROD mode."""
    run_script = os.path.join(project_path, "run.sh")
    if not os.path.isfile(run_script):
        raise FileNotFoundError(f"run.sh not found in {project_path}")
    
    os.chmod(run_script, 0o755)
    print("Launching run.sh in production mode...")
    
    # Kill any existing processes on the same port (optional)
    try:
        run_command("pkill -f 'run.sh PROD'", check=False)
    except:
        pass
    
    subprocess.Popen(["./run.sh", "PROD"], cwd=project_path)
    print("Project launched successfully")


def pipeline(config: Config):
    """Full deployment pipeline."""
    print("Starting deployment pipeline...")

    try:
            run_command(f"git config --global --add safe.directory {config.project_path}", check=False)
            print(f"Added {config.project_path} as safe directory for git")
    except Exception as e:
            print(f"Warning: Could not add safe directory: {e}")
    
    
    # Validate configuration
    if not config.repo_url:
        print("❌ REPO_URL environment variable is not set")
        return False
    
    if not config.project_dir:
        print("❌ PROJECT_DIR environment variable is not set")
        return False
    
    print(f"Repository: {config.repo_url}")
    print(f"Project path: {config.project_path}")
    print(f"SSH key: {config.ssh_key}")
    
    # Ensure SSH key is available
    if not ensure_ssh_key(config):
        print("❌ Could not set up SSH key. Check the instructions above.")
        return False
    
    # Test GitHub connection
    if not test_github_connection(config.repo_url):
        print("❌ Cannot connect to GitHub. Make sure your SSH key is added to your GitHub account.")
        return False
    
    try:
        # Clone or update repository
        clone_or_update_repo(config.repo_url, config.project_path)
        
        # Run the project
        run_project(config.project_path)
        
        print("✅ Deployment pipeline finished successfully.")
        return True
        
    except Exception as e:
        print(f"❌ Deployment pipeline failed: {e}")
        return False