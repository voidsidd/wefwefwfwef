#!/usr/bin/env python3
"""
BUG HUNTER SPIDER - Find real bugs, not docs
Scans code for actual errors, TODOs, type issues, linting problems
"""

import os
import json
import subprocess
import tempfile
import re
import shutil
from datetime import datetime
from typing import List, Dict, Any
import time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
API_BASE = "https://api.github.com"

# Mega projects to hunt bugs in
BUG_TARGETS = [
    ("pytorch", "pytorch", "python"),
    ("facebook", "react", "javascript"),
    ("microsoft", "TypeScript", "typescript"),
    ("vuejs", "vue", "typescript"),
    ("nodejs", "node", "javascript"),
    ("golang", "go", "go"),
    ("rust-lang", "rust", "rust"),
    ("django", "django", "python"),
    ("apache", "airflow", "python"),
    ("elasticsearch", "elasticsearch", "java"),
]

class BugHunter:
    def __init__(self):
        self.bugs_found = []
        self.cache_dir = "/tmp/bug_hunter"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def clone_repo(self, owner: str, repo: str, language: str) -> str:
        """Clone repo to temp directory"""
        repo_dir = os.path.join(self.cache_dir, f"{owner}_{repo}")
        
        if os.path.exists(repo_dir):
            print(f"   ✓ Using cached repo")
            return repo_dir
        
        clone_url = f"https://github.com/{owner}/{repo}.git"
        
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, repo_dir],
                capture_output=True,
                timeout=60,
                check=True
            )
            print(f"   ✓ Cloned")
            return repo_dir
        except Exception as e:
            print(f"   ✗ Clone failed: {e}")
            return None
    
    def cleanup_repo(self, repo_dir: str) -> bool:
        """Clean up cloned repository after scanning"""
        if not repo_dir or not os.path.exists(repo_dir):
            return True
        
        try:
            shutil.rmtree(repo_dir)
            return True
        except Exception as e:
            print(f"   ⚠️  Could not cleanup {repo_dir}: {e}")
            return False
    
    def scan_todos(self, repo_dir: str, owner: str, repo: str) -> List[Dict]:
        """Find TODO/FIXME comments with context"""
        todos = []
        
        try:
            result = subprocess.run(
                ["grep", "-r", "-n", "-E", "TODO|FIXME|BUG|HACK|XXX|CHECKME", repo_dir, 
                 "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=vendor",
                 "--exclude-dir=build", "--exclude-dir=dist"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            lines = result.stdout.strip().split("\n")[:30]  # Top 30
            
            for line in lines:
                if line.strip():
                    # Extract file, line number, content
                    match = re.match(r"([^:]+):(\d+):(.*)", line)
                    if match:
                        filepath, linenum, content = match.groups()
                        # Remove repo prefix
                        filepath = filepath.replace(repo_dir, "").lstrip("/")
                        
                        # Skip test files and configs
                        if "test" not in filepath.lower() and ".json" not in filepath:
                            todos.append({
                                "type": "TODO/FIXME",
                                "file": filepath,
                                "line": linenum,
                                "content": content.strip()[:100],
                                "severity": "medium"
                            })
        
        except Exception as e:
            pass
        
        return todos
    
    def scan_python(self, repo_dir: str) -> List[Dict]:
        """Scan Python code for issues"""
        issues = []
        
        # Find Python files
        try:
            result = subprocess.run(
                ["find", repo_dir, "-name", "*.py", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            py_files = result.stdout.strip().split("\n")[:20]
            
            for pyfile in py_files:
                if not pyfile or "test" in pyfile or "__pycache__" in pyfile:
                    continue
                
                try:
                    with open(pyfile, "r", errors="ignore") as f:
                        content = f.read()
                        
                        # Check for common issues
                        if "except:" in content and "pass" in content:
                            issues.append({
                                "type": "Bare except clause",
                                "file": pyfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "high",
                                "description": "Bare except: clause swallows all exceptions"
                            })
                        
                        if re.search(r"print\(", content):
                            count = len(re.findall(r"print\(", content))
                            if count > 5:
                                issues.append({
                                    "type": "Debug print statements",
                                    "file": pyfile.replace(repo_dir, "").lstrip("/"),
                                    "severity": "medium",
                                    "description": f"Found {count} print() statements (likely debug code)"
                                })
                        
                        if re.search(r"import \*", content):
                            issues.append({
                                "type": "Wildcard import",
                                "file": pyfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "high",
                                "description": "from X import * makes code hard to trace"
                            })
                        
                        if "pickle" in content:
                            issues.append({
                                "type": "Pickle usage",
                                "file": pyfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "high",
                                "description": "pickle can execute arbitrary code - security risk"
                            })
                
                except:
                    pass
        
        except:
            pass
        
        return issues
    
    def scan_javascript(self, repo_dir: str) -> List[Dict]:
        """Scan JavaScript/TypeScript for issues"""
        issues = []
        
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "-E", "\.js$|\.ts$|\.jsx$|\.tsx$", repo_dir,
                 "--exclude-dir=node_modules", "--exclude-dir=dist", "--exclude-dir=build"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            js_files = result.stdout.strip().split("\n")[:20]
            
            for jsfile in js_files:
                if not jsfile or "test" in jsfile:
                    continue
                
                try:
                    with open(jsfile, "r", errors="ignore") as f:
                        content = f.read()
                        
                        # Check for console.log
                        console_count = len(re.findall(r"console\.(log|warn|error)", content))
                        if console_count > 3:
                            issues.append({
                                "type": "Debug console statements",
                                "file": jsfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "medium",
                                "description": f"Found {console_count} console.* calls (debug code left behind)"
                            })
                        
                        # Check for eval
                        if "eval(" in content:
                            issues.append({
                                "type": "eval() usage",
                                "file": jsfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "critical",
                                "description": "eval() is dangerous - security and performance risk"
                            })
                        
                        # Check for any
                        if ": any" in content:
                            any_count = len(re.findall(r": any", content))
                            issues.append({
                                "type": "'any' type used",
                                "file": jsfile.replace(repo_dir, "").lstrip("/"),
                                "severity": "medium",
                                "description": f"Found {any_count} uses of 'any' type (loses type safety)"
                            })
                        
                        # Check for async/await issues
                        if re.search(r"async\s+\w+\s*\(", content):
                            if "await" not in content:
                                issues.append({
                                    "type": "Async without await",
                                    "file": jsfile.replace(repo_dir, "").lstrip("/"),
                                    "severity": "high",
                                    "description": "async function but no await used - likely a bug"
                                })
                
                except:
                    pass
        
        except:
            pass
        
        return issues
    
    def scan_go(self, repo_dir: str) -> List[Dict]:
        """Scan Go code for issues"""
        issues = []
        
        try:
            result = subprocess.run(
                ["find", repo_dir, "-name", "*.go", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            go_files = result.stdout.strip().split("\n")[:20]
            
            for gofile in go_files:
                if not gofile or "test" in gofile:
                    continue
                
                try:
                    with open(gofile, "r", errors="ignore") as f:
                        content = f.read()
                        
                        # Check for error ignoring
                        if re.search(r"_\s*=\s*\w+\(.*\)", content):
                            issues.append({
                                "type": "Error ignored with _",
                                "file": gofile.replace(repo_dir, "").lstrip("/"),
                                "severity": "high",
                                "description": "Error return value ignored - should handle errors"
                            })
                        
                        # Check for nil dereference patterns
                        if re.search(r"if err != nil", content):
                            if "panic" not in content and "log.Fatal" not in content:
                                issues.append({
                                    "type": "Error not handled properly",
                                    "file": gofile.replace(repo_dir, "").lstrip("/"),
                                    "severity": "medium",
                                    "description": "Error checked but not properly handled"
                                })
                
                except:
                    pass
        
        except:
            pass
        
        return issues
    
    def scan_tests(self, repo_dir: str) -> List[Dict]:
        """Find skipped or broken tests"""
        issues = []
        
        try:
            # Look for skipped tests
            result = subprocess.run(
                ["grep", "-r", "-n", "-E", "skip|Skip|SKIP|pending|Pending|PENDING|xtest|xit|fdescribe",
                 repo_dir, "--include=*.py", "--include=*.js", "--include=*.ts", "--include=*.go"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            lines = result.stdout.strip().split("\n")[:10]
            
            for line in lines:
                if line.strip() and ("test" in line.lower() or "spec" in line.lower()):
                    match = re.match(r"([^:]+):(\d+):(.*)", line)
                    if match:
                        filepath, linenum, content = match.groups()
                        issues.append({
                            "type": "Skipped/Pending test",
                            "file": filepath.replace(repo_dir, "").lstrip("/"),
                            "line": linenum,
                            "severity": "medium",
                            "description": content.strip()[:80]
                        })
        
        except:
            pass
        
        return issues
    
    def hunt_bugs(self, owner: str, repo: str, language: str) -> Dict:
        """Hunt for bugs in a repo"""
        print(f"\n🔍 HUNTING BUGS in {owner}/{repo} ({language})...")
        
        repo_dir = self.clone_repo(owner, repo, language)
        if not repo_dir:
            return None
        
        all_issues = []
        
        # Scan TODOs
        todos = self.scan_todos(repo_dir, owner, repo)
        all_issues.extend(todos)
        print(f"   Found {len(todos)} TODOs/FIXMEs")
        
        # Language-specific scanning
        if language == "python":
            py_issues = self.scan_python(repo_dir)
            all_issues.extend(py_issues)
            print(f"   Found {len(py_issues)} Python issues")
        
        elif language in ["javascript", "typescript"]:
            js_issues = self.scan_javascript(repo_dir)
            all_issues.extend(js_issues)
            print(f"   Found {len(js_issues)} JS/TS issues")
        
        elif language == "go":
            go_issues = self.scan_go(repo_dir)
            all_issues.extend(go_issues)
            print(f"   Found {len(go_issues)} Go issues")
        
        # Check for skipped tests
        test_issues = self.scan_tests(repo_dir)
        all_issues.extend(test_issues)
        print(f"   Found {len(test_issues)} test issues")
        
        # Prioritize by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))
        
        result = {
            "repo": f"{owner}/{repo}",
            "url": f"https://github.com/{owner}/{repo}",
            "language": language,
            "issues": all_issues[:15],  # Top 15 issues
            "total_found": len(all_issues)
        }
        
        # Clean up the cloned repository
        self.cleanup_repo(repo_dir)
        print(f"   ✓ Cleanup complete")
        
        return result
    
    def run_hunt(self) -> List[Dict]:
        """Hunt for bugs across all targets"""
        print("🕷️  BUG HUNTER SPIDER - STARTING")
        print("=" * 70)
        
        results = []
        for owner, repo, language in BUG_TARGETS:
            result = self.hunt_bugs(owner, repo, language)
            if result:
                results.append(result)
            time.sleep(0.5)
        
        return results

def generate_bug_roadmap(results: List[Dict]) -> str:
    """Generate actionable bug roadmap"""
    
    roadmap = f"""# 🐛 BUG HUNTER REPORT - REAL ISSUES TO FIX
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
- **Projects Scanned:** {len(results)}
- **Total Issues Found:** {sum(r.get('total_found', 0) for r in results)}
- **Immediately Fixable:** {sum(len(r.get('issues', [])) for r in results)}

**Strategy:** Fix actual bugs → Get merged faster → Build real portfolio

---

## 🎯 RANKED BY IMPACT

"""
    
    # Score by severity and fixability
    all_issues_ranked = []
    
    for result in results:
        for issue in result.get("issues", []):
            severity_score = {"critical": 100, "high": 50, "medium": 20, "low": 5}.get(issue.get("severity", "low"), 5)
            
            all_issues_ranked.append({
                "repo": result["repo"],
                "url": result["url"],
                "issue": issue,
                "score": severity_score
            })
    
    all_issues_ranked.sort(key=lambda x: x["score"], reverse=True)
    
    # Group by severity
    critical = [x for x in all_issues_ranked if x["issue"].get("severity") == "critical"]
    high = [x for x in all_issues_ranked if x["issue"].get("severity") == "high"]
    medium = [x for x in all_issues_ranked if x["issue"].get("severity") == "medium"]
    
    if critical:
        roadmap += f"\n## 🚨 CRITICAL BUGS ({len(critical)}) - FIX IMMEDIATELY\n"
        for idx, item in enumerate(critical[:5], 1):
            roadmap += f"\n### {idx}. {item['issue']['type']}\n"
            roadmap += f"**Repo:** [{item['repo']}]({item['url']})\n"
            roadmap += f"**File:** `{item['issue'].get('file', 'unknown')}`\n"
            roadmap += f"**Description:** {item['issue'].get('description', item['issue'].get('content', 'N/A'))}\n"
            roadmap += f"**Impact:** This is a real bug affecting code execution\n"
    
    if high:
        roadmap += f"\n## ⚠️  HIGH PRIORITY BUGS ({len(high)}) - FIX SOON\n"
        for idx, item in enumerate(high[:8], 1):
            roadmap += f"\n### {idx}. {item['issue']['type']}\n"
            roadmap += f"**Repo:** [{item['repo']}]({item['url']})\n"
            roadmap += f"**File:** `{item['issue'].get('file', 'unknown')}`\n"
            roadmap += f"**Description:** {item['issue'].get('description', item['issue'].get('content', 'N/A'))}\n"
    
    if medium:
        roadmap += f"\n## 📋 MEDIUM PRIORITY ({len(medium)}) - FIX WHEN POSSIBLE\n"
        for idx, item in enumerate(medium[:5], 1):
            roadmap += f"\n### {idx}. {item['issue']['type']}\n"
            roadmap += f"**Repo:** [{item['repo']}]({item['url']})\n"
            roadmap += f"**File:** `{item['issue'].get('file', 'unknown')}`\n"
            roadmap += f"**Description:** {item['issue'].get('description', item['issue'].get('content', 'N/A'))}\n"
    
    roadmap += f"""

---

## 📊 DETAILED BREAKDOWN

"""
    
    for result in results:
        roadmap += f"\n### {result['repo']}\n"
        roadmap += f"🔗 [{result['url']}]({result['url']})\n"
        roadmap += f"**Language:** {result['language']}\n"
        roadmap += f"**Total Issues Found:** {result.get('total_found', 0)}\n"
        roadmap += f"**Top Issues to Fix:**\n"
        
        for issue in result.get("issues", [])[:5]:
            roadmap += f"- **{issue['type']}** ({issue.get('severity', 'unknown').upper()})\n"
            if 'file' in issue:
                roadmap += f"  File: `{issue['file']}`\n"
            roadmap += f"  {issue.get('description', issue.get('content', 'N/A'))}\n"
    
    return roadmap

def main():
    hunter = BugHunter()
    results = hunter.run_hunt()
    
    # Generate roadmap
    roadmap = generate_bug_roadmap(results)
    
    # Save files
    roadmap_path = "/workspaces/wefwefwfwef/BUG_ROADMAP.md"
    with open(roadmap_path, "w") as f:
        f.write(roadmap)
    
    json_path = "/workspaces/wefwefwfwef/bug_hunter_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("✅ BUG HUNT COMPLETE!")
    print("=" * 70)
    print(f"📄 Roadmap: {roadmap_path}")
    print(f"📊 JSON: {json_path}")
    
    # Show summary
    total_issues = sum(r.get('total_found', 0) for r in results)
    critical = sum(len([x for x in r.get('issues', []) if x.get('severity') == 'critical']) for r in results)
    high = sum(len([x for x in r.get('issues', []) if x.get('severity') == 'high']) for r in results)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Issues: {total_issues}")
    print(f"   Critical: {critical}")
    print(f"   High Priority: {high}")

if __name__ == "__main__":
    main()
