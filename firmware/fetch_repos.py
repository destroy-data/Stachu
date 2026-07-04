import os
import subprocess
import sys
import json


def clone_or_update_repo(
    repo_url, path, ref=None, with_submodules=False, patch_path=None
):
    import os

    if not os.path.exists(path):
        subprocess.run(["git", "clone", repo_url, path], check=True)
    else:
        subprocess.run(["git", "-C", path, "fetch"], check=True)

    if ref:
        subprocess.run(["git", "-C", path, "checkout", ref], check=True)

    if with_submodules:
        subprocess.run(
            ["git", "-C", path, "submodule", "update", "--init", "--recursive"],
            check=True,
        )

    if patch_path:
        patch_full_path = (
            patch_path
            if os.path.isabs(patch_path)
            else os.path.join(os.getcwd(), patch_path)
        )
        forward = subprocess.run(
            ["git", "-C", path, "apply", patch_full_path],
            capture_output=True,
            text=True,
        )
        if forward.returncode == 0:
            print(f"Applied patch {patch_path} to {path}")
            return

        # Forward failed — maybe the patch is already applied. Check reverse.
        reverse = subprocess.run(
            ["git", "-C", path, "apply", "--reverse", "--check", patch_full_path],
            capture_output=True,
            text=True,
        )
        if reverse.returncode == 0:
            print(f"Patch {patch_path} already applied to {path}, skipping.")
            return

        sys.stderr.write(
            f"ERROR: patch {patch_path} does not apply cleanly to {path}.\n"
            f"  forward stderr:\n{forward.stderr}"
            f"  reverse check stderr:\n{reverse.stderr}"
        )
        sys.exit(1)


def fetch_dependencies():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "repos.json")

    with open(config_path) as f:
        repos = json.load(f)

    for repo in repos:
        repo_path = os.path.join(script_dir, repo["path"])
        branch = repo.get("branch")
        with_submodules = repo.get("with_submodules", False)
        patch = repo.get("patch")
        if patch and not os.path.isabs(patch):
            patch = os.path.join(script_dir, patch)
        clone_or_update_repo(repo["url"], repo_path, branch, with_submodules, patch)


if __name__ == "__main__":
    fetch_dependencies()