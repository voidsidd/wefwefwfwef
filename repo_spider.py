#!/usr/bin/env python3
"""
GitHub Repo Spider - Automated contribution finder for popular repositories
Uses GitHub API to discover repos, analyze code, and identify contribution opportunities
"""

import os
import json
import subprocess
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile
import shutil

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
API_BASE = "https://api.github.com"

class GitHubSpider:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.findings = []
    
    def search_popular_repos(self, language: str = "", stars_min: int = 10000, limit: int = 10) -> List[Dict]:
        """Search for popular repositories on GitHub"""
        print(f"\n🔍 Searching for popular repos (stars>{stars_min})...")
        
        query = f"stars:>{stars_min}"
        if language:
            query += f" language:{language}"
        query += " sort:stars type:repository"
        
        params = {
            "q": query,
            "per_page": limit,
            "sort": "stars",
            "order": "desc"
        }
        
        try:
            response = self.session.get(f"{API_BASE}/search/repositories", params=params)
            response.raise_for_status()
            data = response.json()
            
            repos = []
            for item in data.get("items", []):
                repo_info = {
                    "name": item["name"],
                    "owner": item["owner"]["login"],
                    "url": item["html_url"],
                    "clone_url": item["clone_url"],
                    "stars": item["stargazers_count"],
                    "language": item["language"],
                    "description": item["description"],
                    "open_issues": item["open_issues_count"],
                    "last_push": item["pushed_at"]
                }
                repos.append(repo_info)
                print(f"  📦 {item['owner']['login']}/{item['name']} ({item['stargazers_count']} ⭐)")
            
            return repos
        except Exception as e:
            print(f"❌ Error searching repos: {e}")
            return []
    
    def get_open_issues(self, owner: str, repo: str, limit: int = 5) -> List[Dict]:
        """Fetch open issues from a repository"""
        try:
            params = {
                "state": "open",
                "per_page": limit,
                "sort": "updated",
                "direction": "desc"
            }
            response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/issues",
                params=params
            )
            response.raise_for_status()
            
            issues = []
            for item in response.json():
                if "pull_request" not in item:  # Filter out PRs
                    issues.append({
                        "title": item["title"],
                        "number": item["number"],
                        "url": item["html_url"],
                        "labels": [label["name"] for label in item.get("labels", [])]
                    })
            return issues
        except Exception as e:
            print(f"  ⚠️  Could not fetch issues: {e}")
            return []
    
    def analyze_repo(self, repo_info: Dict) -> Dict:
        """Clone and analyze a repository for issues"""
        owner = repo_info["owner"]
        repo_name = repo_info["name"]
        clone_url = repo_info["clone_url"]
        
        print(f"\n📊 Analyzing {owner}/{repo_name}...")
        
        findings = {
            "repo": f"{owner}/{repo_name}",
            "url": repo_info["url"],
            "stars": repo_info["stars"],
            "issues": [],
            "code_issues": [],
            "low_hanging_fruit": []
        }
        
        # Get open issues
        issues = self.get_open_issues(owner, repo_name)
        findings["issues"] = issues
        
        # Clone repo temporarily
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                print(f"  📥 Cloning repository...")
                subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, tmpdir],
                    capture_output=True,
                    timeout=60,
                    check=True
                )
                
                # Analyze code for common issues
                code_issues = self._scan_code(tmpdir)
                findings["code_issues"] = code_issues
                
                # Check for easy wins
                easy_wins = self._find_easy_wins(tmpdir)
                findings["low_hanging_fruit"] = easy_wins
                
            except subprocess.TimeoutExpired:
                print(f"  ⏱️  Clone timed out")
            except Exception as e:
                print(f"  ❌ Clone/analysis error: {e}")
        
        return findings
    
    def _scan_code(self, repo_path: str) -> List[str]:
        """Scan code for common issues"""
        issues = []
        
        # Look for TODO/FIXME comments
        try:
            result = subprocess.run(
                ["grep", "-r", "-E", "TODO|FIXME|BUG|HACK", repo_path],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.stdout:
                todos = result.stdout.split("\n")[:5]  # First 5
                for todo in todos:
                    if todo.strip():
                        issues.append(f"TODO/FIXME: {todo[:100]}")
        except:
            pass
        
        # Check for common anti-patterns
        try:
            # Look for console.log left behind (JavaScript)
            result = subprocess.run(
                ["grep", "-r", "console.log", repo_path, "--include=*.js", "--include=*.ts"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.stdout:
                issues.append("Found leftover console.log statements")
        except:
            pass
        
        # Check for empty/commented code blocks
        try:
            result = subprocess.run(
                ["grep", "-r", "^[ ]*#.*#[ ]*$", repo_path],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.stdout:
                issues.append("Found commented-out code blocks")
        except:
            pass
        
        return issues
    
    def _find_easy_wins(self, repo_path: str) -> List[str]:
        """Find easy wins for contributions"""
        wins = []
        
        # Check README
        readme_path = None
        for name in ["README.md", "README.rst", "README.txt"]:
            path = os.path.join(repo_path, name)
            if os.path.exists(path):
                readme_path = path
                break
        
        if readme_path:
            with open(readme_path, "r", errors="ignore") as f:
                content = f.read()
                # Check for outdated sections
                if "TODO" in content or "FIXME" in content:
                    wins.append("README has TODO/FIXME sections")
                if "deprecated" in content.lower():
                    wins.append("README mentions deprecated items")
                if "[WIP]" in content or "[Draft]" in content:
                    wins.append("README has draft/incomplete sections")
        
        # Check for missing CONTRIBUTING.md
        if not os.path.exists(os.path.join(repo_path, "CONTRIBUTING.md")):
            wins.append("Missing CONTRIBUTING.md file")
        
        # Check for inconsistent formatting
        py_files = subprocess.run(
            ["find", repo_path, "-name", "*.py", "-type", "f"],
            capture_output=True,
            text=True,
            timeout=10
        ).stdout.count("\n")
        
        if py_files > 0:
            # Check for PEP 8 violations
            try:
                subprocess.run(
                    ["python3", "-m", "py_compile", os.path.join(repo_path, "*.py")],
                    capture_output=True,
                    timeout=10
                )
            except:
                wins.append("Potential Python formatting issues")
        
        # Check for missing type hints
        try:
            result = subprocess.run(
                ["grep", "-r", "def.*:", repo_path, "--include=*.py"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.stdout:
                total_defs = len(result.stdout.split("\n"))
                # This is a heuristic
                if total_defs > 5:
                    wins.append("Potential missing type hints in Python code")
        except:
            pass
        
        return wins[:5]  # Return top 5
    
    def run_spider(self, languages: List[str] = None, stars_min: int = 20000, repos_per_lang: int = 5) -> List[Dict]:
        """Run the full spider workflow"""
        if languages is None:
            languages = ["python", "javascript"]
        
        results = []
        
        for language in languages:
            repos = self.search_popular_repos(language=language, stars_min=stars_min, limit=repos_per_lang)
            
            for repo in repos:
                findings = self.analyze_repo(repo)
                results.append(findings)
                self.findings.append(findings)
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a markdown report of findings"""
        report = f"""# 🕷️ GitHub Spider Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total repositories analyzed: {len(results)}
- Repositories with potential contributions: {len([r for r in results if r['issues'] or r['code_issues'] or r['low_hanging_fruit']])}

---

"""
        
        for finding in results:
            report += f"\n## {finding['repo'].upper()}\n"
            report += f"⭐ **Stars:** {finding['stars']}\n"
            report += f"🔗 **URL:** {finding['url']}\n\n"
            
            if finding['issues']:
                report += f"### 📋 Open Issues (Low-hanging fruit potential)\n"
                for issue in finding['issues'][:3]:
                    labels = f" `{', '.join(issue['labels'])}`" if issue['labels'] else ""
                    report += f"- [{issue['title']}]({issue['url']}){labels}\n"
                report += "\n"
            
            if finding['code_issues']:
                report += f"### 🐛 Code Issues Detected\n"
                for code_issue in finding['code_issues']:
                    report += f"- {code_issue}\n"
                report += "\n"
            
            if finding['low_hanging_fruit']:
                report += f"### 🍎 Low-Hanging Fruit\n"
                for fruit in finding['low_hanging_fruit']:
                    report += f"- {fruit}\n"
                report += "\n"
            
            report += "---\n"
        
        return report

def main():
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in environment")
        return
    
    print("🕷️  GitHub Repo Spider - Automated Contribution Finder")
    print("=" * 60)
    
    spider = GitHubSpider(GITHUB_TOKEN)
    
    # Search across multiple languages, aim for mega projects (20k+ stars)
    languages = ["python", "javascript", "typescript", "java", "golang"]
    
    print(f"\n🎯 TARGET: Mega projects with 20k+ stars across {len(languages)} languages")
    print(f"   Languages: {', '.join(languages)}")
    
    results = spider.run_spider(languages=languages, stars_min=20000, repos_per_lang=3)
    
    # Generate report
    report = spider.generate_report(results)
    
    # Save report
    report_path = "/workspaces/wefwefwfwef/contribution_opportunities.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n\n✅ Analysis complete!")
    print(f"📄 Report saved to: {report_path}")
    
    # Save detailed JSON
    json_path = "/workspaces/wefwefwfwef/spider_findings.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"📊 Detailed findings saved to: {json_path}")

if __name__ == "__main__":
    main()
