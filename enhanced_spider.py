#!/usr/bin/env python3
"""
Enhanced GitHub Repo Spider v2 - Better rate limiting, caching, and reporting
"""

import os
import json
import subprocess
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile
import hashlib

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
API_BASE = "https://api.github.com"
CACHE_DIR = "/tmp/github_spider_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class EnhancedSpider:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.findings = []
        self.rate_limit_remaining = None
    
    def _check_rate_limit(self):
        """Check GitHub API rate limit"""
        try:
            response = self.session.get(f"{API_BASE}/rate_limit")
            if response.status_code == 200:
                data = response.json()
                self.rate_limit_remaining = data["rate"]["remaining"]
                print(f"⏱️  API Rate Limit: {self.rate_limit_remaining} requests remaining")
                if self.rate_limit_remaining < 10:
                    print("⚠️  Low rate limit!")
                    reset_time = datetime.fromtimestamp(data["rate"]["reset"])
                    print(f"   Resets at: {reset_time}")
        except Exception as e:
            print(f"Could not check rate limit: {e}")
    
    def search_by_language(self, language: str, min_stars: int = 5000, max_stars: int = 500000) -> List[Dict]:
        """Search repos by language with better filtering"""
        print(f"\n🔎 Searching {language} repos ({min_stars}-{max_stars} stars)...")
        
        # Use different strategies for different star ranges
        queries = [
            f"language:{language} stars:{min_stars}..{min_stars*2} sort:stars type:repository",
            f"language:{language} stars:{min_stars*2}..{min_stars*5} sort:stars type:repository",
            f"language:{language} stars:{min_stars*5}..{min_stars*20} sort:stars type:repository",
        ]
        
        all_repos = []
        
        for query in queries:
            try:
                params = {"q": query, "per_page": 5, "sort": "stars", "order": "desc"}
                response = self.session.get(f"{API_BASE}/search/repositories", params=params)
                
                if response.status_code == 200:
                    data = response.json()
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
                            "last_push": item["pushed_at"],
                            "forks": item["forks_count"],
                        }
                        all_repos.append(repo_info)
                        print(f"   ✓ {item['owner']['login']}/{item['name']} ({item['stargazers_count']}⭐)")
                    
                    time.sleep(0.5)  # Rate limit protection
                else:
                    print(f"   ⚠️  Query failed: {response.status_code}")
            
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Remove duplicates
        seen = set()
        unique_repos = []
        for repo in all_repos:
            key = f"{repo['owner']}/{repo['name']}"
            if key not in seen:
                seen.add(key)
                unique_repos.append(repo)
        
        return unique_repos[:8]  # Limit per language
    
    def get_top_issues(self, owner: str, repo: str) -> List[Dict]:
        """Get high-value issues with good-first-issue labels"""
        try:
            # Try for good-first-issue tagged issues
            params = {
                "state": "open",
                "labels": "good-first-issue,good first issue,beginner,easy,help-wanted",
                "per_page": 3,
                "sort": "updated"
            }
            response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/issues",
                params=params
            )
            
            if response.status_code == 200 and response.json():
                issues = []
                for item in response.json()[:3]:
                    if "pull_request" not in item:
                        issues.append({
                            "title": item["title"],
                            "number": item["number"],
                            "url": item["html_url"],
                            "difficulty": "easy",
                            "labels": [label["name"] for label in item.get("labels", [])]
                        })
                return issues
            
            # Fall back to general issues
            params = {"state": "open", "per_page": 3, "sort": "updated"}
            response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/issues",
                params=params
            )
            
            issues = []
            for item in response.json()[:3]:
                if "pull_request" not in item:
                    issues.append({
                        "title": item["title"],
                        "number": item["number"],
                        "url": item["html_url"],
                        "difficulty": "medium",
                        "labels": [label["name"] for label in item.get("labels", [])]
                    })
            return issues
            
        except Exception as e:
            return []
    
    def quick_scan(self, repo_info: Dict) -> Dict:
        """Quick analysis without cloning (faster)"""
        owner = repo_info["owner"]
        repo_name = repo_info["name"]
        
        print(f"🔬 Scanning {owner}/{repo_name}...")
        
        findings = {
            "repo": f"{owner}/{repo_name}",
            "url": repo_info["url"],
            "stars": repo_info["stars"],
            "language": repo_info["language"],
            "forks": repo_info["forks"],
            "last_updated": repo_info["last_push"],
            "issues": [],
            "pr_potential": []
        }
        
        # Get issues
        issues = self.get_top_issues(owner, repo_name)
        findings["issues"] = issues
        
        # Get repo README info
        try:
            readme_response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo_name}/readme",
                headers={**self.headers, "Accept": "application/vnd.github.v3.raw"}
            )
            
            if readme_response.status_code == 200:
                readme = readme_response.text
                
                pr_ideas = []
                
                if "TODO" in readme:
                    pr_ideas.append("README has TODO sections")
                if "FIXME" in readme:
                    pr_ideas.append("README has FIXME sections")
                if "[WIP]" in readme or "Work in Progress" in readme:
                    pr_ideas.append("README has WIP sections")
                if len(readme) < 500:
                    pr_ideas.append("README is minimal (expansion opportunity)")
                if "deprecated" in readme.lower():
                    pr_ideas.append("README mentions deprecated items")
                
                findings["pr_potential"].extend(pr_ideas)
        except:
            pass
        
        # Check for CONTRIBUTING.md
        try:
            contrib_response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo_name}/contents/CONTRIBUTING.md"
            )
            if contrib_response.status_code == 404:
                findings["pr_potential"].append("Missing CONTRIBUTING.md")
        except:
            pass
        
        # Check for outdated dependencies (package.json last modified)
        try:
            pkg_response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo_name}/contents/package.json"
            )
            if pkg_response.status_code == 200:
                findings["pr_potential"].append("Has package.json - check for outdated deps")
        except:
            pass
        
        time.sleep(0.3)  # Rate limit protection
        return findings
    
    def run_enhanced_scan(self) -> List[Dict]:
        """Run enhanced scan across multiple languages"""
        self._check_rate_limit()
        
        languages = ["python", "javascript", "typescript", "go", "rust", "java"]
        results = []
        
        for lang in languages:
            repos = self.search_by_language(lang, min_stars=1000)
            
            for repo in repos:
                try:
                    finding = self.quick_scan(repo)
                    results.append(finding)
                except Exception as e:
                    print(f"   ❌ Error analyzing {repo['name']}: {e}")
            
            time.sleep(1)  # Be nice to GitHub API
        
        self._check_rate_limit()
        return results
    
    def generate_pr_roadmap(self, results: List[Dict]) -> str:
        """Generate actionable PR roadmap"""
        markdown = f"""# 📋 CONTRIBUTION ROADMAP - YOUR RESUME MATERIAL
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Strategy
1. **Easy Wins First** - README fixes, documentation, CONTRIBUTING.md
2. **Med. Difficulty** - Reported issues, small features
3. **Deep Contributions** - Clone repos locally for code-level fixes

Total repos scanned: **{len(results)}**
Repos with opportunities: **{len([r for r in results if r['issues'] or r['pr_potential']])}**

---

## 📊 RANKED BY OPPORTUNITY

"""
        
        # Score each repo
        scored = []
        for result in results:
            score = 0
            score += len(result['issues']) * 5  # Open issues are high value
            score += len(result['pr_potential']) * 2  # PR potential is good
            score += (result['stars'] / 1000)  # Higher stars = better resume material
            
            scored.append((score, result))
        
        scored.sort(reverse=True)
        
        for idx, (score, result) in enumerate(scored[:20], 1):
            markdown += f"\n### #{idx}. **{result['repo']}** (⭐ {result['stars']} | Score: {score:.1f})\n"
            markdown += f"🔗 {result['url']}\n"
            markdown += f"💬 Language: {result['language']} | 📦 Forks: {result['forks']}\n"
            
            if result['issues']:
                markdown += f"\n**📌 OPEN ISSUES (QUICK WINS):**\n"
                for issue in result['issues'][:2]:
                    markdown += f"- [{issue['title']}]({issue['url']}) `{issue['difficulty']}`\n"
            
            if result['pr_potential']:
                markdown += f"\n**💡 PR IDEAS:**\n"
                for idea in result['pr_potential'][:3]:
                    markdown += f"- {idea}\n"
            
            markdown += "\n---\n"
        
        return markdown

def main():
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found!")
        return
    
    print("=" * 70)
    print("🕷️  ENHANCED GITHUB SPIDER v2 - CONTRIBUTION FINDER")
    print("=" * 70)
    print(f"🎯 Finding popular repos with contribution opportunities")
    print(f"📍 Target: Diverse languages, varied project sizes")
    print()
    
    spider = EnhancedSpider(GITHUB_TOKEN)
    results = spider.run_enhanced_scan()
    
    # Generate roadmap
    roadmap = spider.generate_pr_roadmap(results)
    
    # Save files
    roadmap_path = "/workspaces/wefwefwfwef/PR_ROADMAP.md"
    with open(roadmap_path, "w") as f:
        f.write(roadmap)
    
    json_path = "/workspaces/wefwefwfwef/repos_analysis.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ SCAN COMPLETE!")
    print(f"📄 Roadmap: {roadmap_path}")
    print(f"📊 Analysis JSON: {json_path}")
    print(f"\n🚀 Next steps: Review the roadmap and pick your first contribution!")

if __name__ == "__main__":
    main()
