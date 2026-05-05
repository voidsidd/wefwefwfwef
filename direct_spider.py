#!/usr/bin/env python3
"""
Direct Target Spider - Hardcoded mega-projects with proven contribution culture
"""

import os
import json
import requests
import time
from datetime import datetime
from typing import List, Dict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
API_BASE = "https://api.github.com"

# Pre-selected mega-projects known for accepting contributions
MEGA_PROJECTS = [
    # Python
    ("pallets", "flask"),
    ("psf", "cpython"),
    ("django", "django"),
    ("apache", "airflow"),
    ("pytorch", "pytorch"),
    # JavaScript/TypeScript
    ("facebook", "react"),
    ("microsoft", "TypeScript"),
    ("nodejs", "node"),
    ("vuejs", "vue"),
    ("angular", "angular"),
    # Go
    ("golang", "go"),
    ("kubernetes", "kubernetes"),
    ("moby", "moby"),
    # Rust
    ("rust-lang", "rust"),
    # Java
    ("apache", "kafka"),
    ("elastic", "elasticsearch"),
]

class DirectSpider:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_repo_details(self, owner: str, repo: str) -> Dict:
        """Get detailed info about a repo"""
        try:
            response = self.session.get(f"{API_BASE}/repos/{owner}/{repo}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "owner": owner,
                    "name": repo,
                    "full_name": data["full_name"],
                    "url": data["html_url"],
                    "clone_url": data["clone_url"],
                    "stars": data["stargazers_count"],
                    "language": data["language"],
                    "description": data["description"],
                    "open_issues": data["open_issues_count"],
                    "forks": data["forks_count"],
                    "watchers": data["watchers_count"],
                    "created": data["created_at"],
                    "pushed": data["pushed_at"],
                }
            else:
                print(f"   ⚠️  {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def get_labeled_issues(self, owner: str, repo: str, labels: List[str] = None) -> List[Dict]:
        """Get issues with specific labels (good for beginners)"""
        if labels is None:
            labels = ["good-first-issue", "good first issue", "beginner-friendly", "easy", "documentation"]
        
        try:
            all_issues = []
            
            for label in labels[:3]:  # Try top 3 labels
                params = {
                    "state": "open",
                    "labels": label,
                    "per_page": 5,
                    "sort": "updated",
                    "direction": "desc"
                }
                
                response = self.session.get(
                    f"{API_BASE}/repos/{owner}/{repo}/issues",
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    for item in response.json():
                        if "pull_request" not in item:
                            all_issues.append({
                                "title": item["title"],
                                "number": item["number"],
                                "url": item["html_url"],
                                "labels": [l["name"] for l in item["labels"]],
                                "created": item["created_at"],
                                "difficulty": label
                            })
                
                time.sleep(0.5)
            
            # Remove duplicates
            seen = set()
            unique = []
            for issue in all_issues:
                if issue["number"] not in seen:
                    seen.add(issue["number"])
                    unique.append(issue)
            
            return unique[:5]
        
        except Exception as e:
            print(f"   ❌ Could not fetch issues: {e}")
            return []
    
    def analyze_repo(self, owner: str, repo: str) -> Dict:
        """Full analysis of a repo"""
        print(f"\n📊 Analyzing {owner}/{repo}...")
        
        # Get repo details
        details = self.get_repo_details(owner, repo)
        if not details:
            return None
        
        print(f"   ⭐ Stars: {details['stars']} | 🔓 Issues: {details['open_issues']}")
        
        # Get issues
        issues = self.get_labeled_issues(owner, repo)
        print(f"   📋 Found {len(issues)} opportunity issues")
        
        result = {
            "repo": f"{owner}/{repo}",
            "full_name": details["full_name"],
            "url": details["url"],
            "stars": details["stars"],
            "language": details["language"],
            "forks": details["forks"],
            "watchers": details["watchers"],
            "open_issues": details["open_issues"],
            "last_push": details["pushed"],
            "created": details["created"],
            "opportunity_issues": issues,
            "pr_ideas": []
        }
        
        # Get README for PR ideas
        try:
            readme_response = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/readme",
                headers={**self.headers, "Accept": "application/vnd.github.v3.raw"},
                timeout=10
            )
            
            if readme_response.status_code == 200:
                readme = readme_response.text
                
                if "TODO" in readme:
                    result["pr_ideas"].append("Fix README TODOs")
                if "FIXME" in readme:
                    result["pr_ideas"].append("Fix README FIXMEs")
                if "## Contributing" not in readme and "# Contributing" not in readme:
                    result["pr_ideas"].append("Add Contributing guide to README")
                if len(readme) < 1000:
                    result["pr_ideas"].append("Expand minimal README")
        except:
            pass
        
        # Check for missing files
        for filename in ["CONTRIBUTING.md", ".github/ISSUE_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE.md"]:
            try:
                check_response = self.session.get(
                    f"{API_BASE}/repos/{owner}/{repo}/contents/{filename}",
                    timeout=10
                )
                if check_response.status_code == 404:
                    result["pr_ideas"].append(f"Add missing {filename}")
            except:
                pass
        
        time.sleep(0.5)
        return result
    
    def scan_all(self) -> List[Dict]:
        """Analyze all mega-projects"""
        results = []
        
        print("🕷️  DIRECT TARGET SPIDER - MEGA PROJECTS")
        print("=" * 70)
        print(f"🎯 Analyzing {len(MEGA_PROJECTS)} known mega-projects...")
        
        for i, (owner, repo) in enumerate(MEGA_PROJECTS, 1):
            print(f"\n[{i}/{len(MEGA_PROJECTS)}] {owner}/{repo}")
            
            result = self.analyze_repo(owner, repo)
            if result:
                results.append(result)
            
            time.sleep(1)
        
        return results

def generate_comprehensive_guide(results: List[Dict]) -> str:
    """Generate comprehensive contribution guide"""
    
    guide = f"""# 🚀 MEGA-PROJECT CONTRIBUTION GUIDE
*Your Path to Open Source Stardom*

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- **Projects Analyzed:** {len(results)}
- **Total Opportunities:** {sum(len(r.get('opportunity_issues', [])) for r in results)}
- **PR Ideas:** {sum(len(r.get('pr_ideas', [])) for r in results)}

---

## 🏆 TIER 1: EASIEST ENTRY POINTS (START HERE)

"""
    
    # Sort by easiest entry
    easy_first = sorted(results, key=lambda x: (
        -len(x.get('pr_ideas', [])),
        -len(x.get('opportunity_issues', [])),
        x['stars']
    ))
    
    for idx, repo in enumerate(easy_first[:10], 1):
        guide += f"\n### {idx}. **{repo['repo']}**\n"
        guide += f"⭐ **{repo['stars']}** stars | 🍴 **{repo['forks']}** forks | 📋 **{repo['open_issues']}** issues\n"
        guide += f"🔗 [{repo['url']}]({repo['url']})\n"
        guide += f"💻 Language: **{repo['language']}**\n"
        
        if repo['opportunity_issues']:
            guide += f"\n#### 🎯 Good First Issues\n"
            for issue in repo['opportunity_issues'][:3]:
                guide += f"- [**{issue['title']}**]({issue['url']})\n"
                guide += f"  `{issue['difficulty']}` | Issue #{issue['number']}\n"
        
        if repo['pr_ideas']:
            guide += f"\n#### 💡 PR Ideas\n"
            for idea in repo['pr_ideas'][:3]:
                guide += f"- {idea}\n"
        
        guide += "\n---\n"
    
    guide += "\n\n## 🎓 CONTRIBUTION STRATEGY\n\n"
    guide += """### Phase 1: Scout (This Week)
1. Pick 3 repos from Tier 1
2. Fork each repo locally
3. Read their CONTRIBUTING.md
4. Join their community (Discord/issues/discussions)

### Phase 2: Light Wins (Week 2)
1. README improvements
2. Documentation fixes
3. Add missing CONTRIBUTING guidelines
4. Fix typos/formatting

### Phase 3: Real Contributions (Week 3+)
1. Pick an open, labeled issue
2. Leave a comment asking to work on it
3. Create a feature branch
4. Submit a polished PR
5. Engage with reviewers

### Phase 4: Deep Dives (Month 2+)
1. Identify complex issues
2. Implement substantial features
3. Build relationships with maintainers
4. Become a recognized contributor

---

## 📝 RESUME BULLET FORMAT

Use this structure for each contribution:

```
• Contributed Python type hints to TypeScript repository (XYZ accepted PRs)
• Fixed documentation in Flask framework used by 100k+ projects  
• Added missing CONTRIBUTING.md to Kubernetes project (50k+ stars)
```

---

## 🔗 USEFUL LINKS

- [First Timers Only](https://www.firsttimersonly.com/)
- [Open Source Guide](https://opensource.guide/)
- [How to Contribute](https://github.com/firstcontributions/first-contributions)

---

## 📊 PROJECT DETAILS

"""
    
    for idx, repo in enumerate(results, 1):
        guide += f"\n### {idx}. {repo['repo']}\n"
        guide += f"- URL: {repo['url']}\n"
        guide += f"- Stars: {repo['stars']}\n"
        guide += f"- Language: {repo['language']}\n"
        guide += f"- Open Issues: {repo['open_issues']}\n"
        guide += f"- Last Updated: {repo['last_push']}\n"
        
        if repo['opportunity_issues']:
            guide += f"\n  **Issues with Opportunity Labels:**\n"
            for issue in repo['opportunity_issues']:
                guide += f"  - {issue['title']} (#{issue['number']})\n"
        
        if repo['pr_ideas']:
            guide += f"\n  **PR Ideas:**\n"
            for idea in repo['pr_ideas']:
                guide += f"  - {idea}\n"
    
    return guide

def main():
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found!")
        return
    
    spider = DirectSpider(GITHUB_TOKEN)
    results = spider.scan_all()
    
    # Generate guide
    guide = generate_comprehensive_guide(results)
    
    # Save files
    guide_path = "/workspaces/wefwefwfwef/MEGA_PROJECT_GUIDE.md"
    with open(guide_path, "w") as f:
        f.write(guide)
    
    json_path = "/workspaces/wefwefwfwef/mega_projects_analysis.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 70)
    print(f"📄 Guide: {guide_path}")
    print(f"📊 JSON: {json_path}")
    print(f"\n📍 Recommended repos with easiest entry points:")
    
    # Show top 5 easiest
    easy_first = sorted(results, key=lambda x: (
        -len(x.get('pr_ideas', [])),
        -len(x.get('opportunity_issues', []))
    ))
    
    for idx, repo in enumerate(easy_first[:5], 1):
        pr_count = len(repo.get('pr_ideas', []))
        issue_count = len(repo.get('opportunity_issues', []))
        print(f"{idx}. {repo['repo']} ({pr_count} PR ideas, {issue_count} issues)")

if __name__ == "__main__":
    main()
