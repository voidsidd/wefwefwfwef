#!/usr/bin/env python3
"""
PR TOOLKIT - Your command-line companion for submitting contributions
"""

import os
import json
import subprocess
import argparse
from datetime import datetime
import sys

class PRToolkit:
    def __init__(self):
        self.pr_tracker_file = "/workspaces/wefwefwfwef/pr_tracker.json"
        self.pr_tracker = self.load_tracker()
    
    def load_tracker(self):
        """Load PR tracking data"""
        if os.path.exists(self.pr_tracker_file):
            with open(self.pr_tracker_file) as f:
                return json.load(f)
        return {"prs": [], "completed": []}
    
    def save_tracker(self):
        """Save PR tracking data"""
        with open(self.pr_tracker_file, "w") as f:
            json.dump(self.pr_tracker, f, indent=2)
    
    def clone_repo(self, owner: str, repo: str):
        """Clone a repository and set up for contribution"""
        repo_dir = f"/workspaces/{owner}_{repo}"
        
        if os.path.exists(repo_dir):
            print(f"✓ Repository already exists at {repo_dir}")
            return repo_dir
        
        print(f"📥 Cloning {owner}/{repo}...")
        
        clone_url = f"https://github.com/{owner}/{repo}.git"
        subprocess.run(["git", "clone", clone_url, repo_dir], check=True)
        
        # Set up git
        os.chdir(repo_dir)
        subprocess.run(["git", "config", "user.name", "Your Name"], check=True)
        subprocess.run(["git", "config", "user.email", "your@email.com"], check=True)
        
        print(f"✓ Cloned to {repo_dir}")
        return repo_dir
    
    def create_feature_branch(self, repo_dir: str, issue_number: int):
        """Create a feature branch for an issue"""
        branch_name = f"fix/issue-{issue_number}"
        
        os.chdir(repo_dir)
        subprocess.run(["git", "fetch", "origin"], check=True)
        subprocess.run(["git", "checkout", "-b", branch_name, "origin/main"], check=True)
        
        print(f"✓ Created branch: {branch_name}")
        return branch_name
    
    def commit_and_push(self, repo_dir: str, message: str, branch: str):
        """Commit changes and push"""
        os.chdir(repo_dir)
        
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push", "origin", branch], check=True)
        
        print(f"✓ Pushed changes to {branch}")
    
    def open_pr(self, owner: str, repo: str, branch: str, title: str, body: str = ""):
        """Open a PR using gh CLI"""
        cmd = ["gh", "pr", "create", "--repo", f"{owner}/{repo}", 
               "--base", "main", "--head", branch, 
               "--title", title]
        
        if body:
            cmd.extend(["--body", body])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            pr_url = result.stdout.strip()
            print(f"✓ PR created: {pr_url}")
            return pr_url
        else:
            print(f"✗ Failed to create PR: {result.stderr}")
            return None
    
    def track_pr(self, repo: str, issue_num: int, pr_url: str, description: str):
        """Track a PR"""
        pr_entry = {
            "timestamp": datetime.now().isoformat(),
            "repo": repo,
            "issue": issue_num,
            "url": pr_url,
            "description": description,
            "status": "pending"
        }
        self.pr_tracker["prs"].append(pr_entry)
        self.save_tracker()
        print(f"📝 Tracked PR: {repo}")
    
    def show_tracker(self):
        """Show all tracked PRs"""
        print("\n" + "=" * 70)
        print("📊 YOUR PR TRACKER")
        print("=" * 70)
        
        if not self.pr_tracker["prs"]:
            print("No PRs tracked yet!")
            return
        
        for idx, pr in enumerate(self.pr_tracker["prs"], 1):
            print(f"\n{idx}. {pr['repo']} (Issue #{pr['issue']})")
            print(f"   URL: {pr['url']}")
            print(f"   Status: {pr['status']}")
            print(f"   Submitted: {pr['timestamp']}")

def main():
    parser = argparse.ArgumentParser(description="PR Toolkit - Contribution helper")
    subparsers = parser.add_subparsers(dest="command")
    
    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Clone a repository")
    clone_parser.add_argument("owner", help="Repository owner")
    clone_parser.add_argument("repo", help=" Repository name")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up local environment")
    setup_parser.add_argument("--git-name", help="Your Git name")
    setup_parser.add_argument("--git-email", help="Your Git email")
    
    # Tracker command
    subparsers.add_parser("tracker", help="Show PR tracker")
    
    # Guide command
    subparsers.add_parser("guide", help="Show quick start guide")
    
    args = parser.parse_args()
    
    toolkit = PRToolkit()
    
    if args.command == "clone":
        toolkit.clone_repo(args.owner, args.repo)
    elif args.command == "tracker":
        toolkit.show_tracker()
    elif args.command == "guide":
        show_quick_guide()
    elif args.command == "setup":
        setup_git(args.git_name, args.git_email)
    else:
        parser.print_help()

def show_quick_guide():
    guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║                   🚀 QUICK START GUIDE TO EASY WINS                        ║
╚════════════════════════════════════════════════════════════════════════════╝

## STEP 1: CHOOSE YOUR TARGET
1. Open: /workspaces/wefwefwfwef/MEGA_PROJECT_GUIDE.md
2. Pick a Tier 1 project (easiest entry points)
3. Start with a PR idea (documentation is easiest!)

## STEP 2: EASY WIN - README/DOCS

  Example: Django needs a Contributing guide

  $ python3 pr_toolkit.py clone django django
  $ cd /workspaces/django_django
  $ git checkout -b docs/add-contributing

  # Create CONTRIBUTING.md based on their patterns
  # Add to README if needed

  $ python3 pr_toolkit.py commit-push CONTRIBUTING.md\\
    "Add CONTRIBUTING.md with setup instructions"

## STEP 3: OPEN THE PR

  $ gh pr create --repo django/django\\
    --base main --head docs/add-contributing\\
    --title "Add CONTRIBUTING.md"\\
    --body "Similar to other Django projects,\\
    added CONTRIBUTING.md with setup instructions"

## STEP 4: TRACK YOUR PR

  $ python3 pr_toolkit.py tracker add\\
    --repo django/django\\
    --url [YOUR_PR_URL]

---

## COPY-PASTE RESUME BULLETS

✓ "Contributed documentation to Django (45k+ stars)"
✓ "Fixed README issues in PyTorch (100k+ stars)"
✓ "Added CONTRIBUTING.md to TypeScript (108k+ stars)"

Each PR = one bullet point on your resume!

---

## TIPS FOR SUCCESS

1. **Start with docs** - Easiest to get merged
2. **Read CONTRIBUTING.md** first - Some projects have specific rules
3. **Be respectful** - Comment on issues before starting work
4. **Test your changes** - Run tests locally before submitting
5. **Write good commit messages** - "Describe WHAT you did and WHY"
6. **Engage with reviewers** - They're helping you!

---

## TEMPLATE PR DESCRIPTIONS (COPY-PASTE)

### For Documentation:
  "Added CONTRIBUTING.md to help new contributors get started.
   Includes setup steps, testing instructions, and PR guidelines."

### For README fixes:
  "Updated README.md:
   - Fixed outdated example code
   - Clarified installation instructions
   - Updated links to current versions"

### For small bugs:
  "Fixed issue #XXXX:
   - [Describe the problem]
   - [Describe the solution]
   - Tested: [How you tested it]"

╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(guide)

def setup_git(name=None, email=None):
    """Set up git configuration"""
    name = name or input("Enter your Git name: ")
    email = email or input("Enter your Git email: ")
    
    subprocess.run(["git", "config", "--global", "user.name", name], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)
    
    print(f"✓ Git configured: {name} ({email})")

if __name__ == "__main__":
    main()
