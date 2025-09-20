import subprocess
import os
from pydantic import BaseModel

class Config(BaseModel):
    webhook_port: int = int(os.environ.get('WEBHOOK_PORT', 8080))
    webhook_secret: str = os.environ.get('WEBHOOK_SECRET', '')
    repo_url: str = os.environ.get('REPO_URL', '')
    project_dir: str = os.environ.get('PROJECT_DIR', '')
    home_dir: str = os.environ.get('HOME', '')
    ssh_key: str =  os.path.expanduser('~/.ssh/id_ed25519')

    @property
    def project_path(self):
        return os.path.join(self.home_dir, self.project_dir)


def run_command(command, cwd=None, check=True):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    return result


def ensure_ssh_key(config: Config):
    """Check if SSH key is added to agent, if not add it."""
    try:
        result = subprocess.run(
            f'ssh-add -l | grep "$(ssh-keygen -lf {config.ssh_key} | awk \'{{print $2}}\')"',
            shell=True
        )
        if result.returncode != 0:
            subprocess.run('eval "$(ssh-agent -s)"', shell=True, check=True)
            run_command(f'ssh-add "{config.ssh_key}"')
    except Exception as e:
        print(f"Failed to load SSH key: {e}")
        return False
    return True


def clone_or_update_repo(repo_url, project_path):
    """Clone repo if not exists, otherwise fetch and reset to main/master."""
    if not os.path.exists(os.path.join(project_path, ".git")):
        print("Cloning repository...")
        run_command(f"git clone {repo_url} {project_path}")
    else:
        print("Repository exists. Updating...")
        os.chdir(project_path)
        run_command("git switch main", check=False)
        run_command("git switch master", check=False)
        run_command("git fetch origin")
        run_command("git reset --hard origin/main", check=False)
        run_command("git reset --hard origin/master", check=False)
        print("Repository updated.")


def run_project(project_path):
    """Ensure run.sh exists, make executable, and run it in PROD mode."""
    run_script = os.path.join(project_path, "run.sh")
    if not os.path.isfile(run_script):
        raise FileNotFoundError(f"run.sh not found in {project_path}")
    os.chmod(run_script, 0o755)
    print("Launching run.sh in production mode...")
    subprocess.Popen(["./run.sh", "PROD"], cwd=project_path)


def pipeline(config: Config):
    """Full deployment pipeline."""
    if not ensure_ssh_key(config):
        print("Could not load SSH key. Make sure your environment is set correctly.")
        return

    clone_or_update_repo(config.repo_url, config.project_path)
    run_project(config.project_path)
    print("Deployment pipeline finished successfully.")
