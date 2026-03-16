#!/usr/bin/env python3
"""gitgrep - Search across multiple git repositories."""
import subprocess, argparse, os, sys, concurrent.futures

def find_repos(base, max_depth=3):
    repos = []
    for root, dirs, files in os.walk(base):
        depth = root[len(base):].count(os.sep)
        if depth >= max_depth:
            dirs.clear(); continue
        if '.git' in dirs:
            repos.append(root)
            dirs.remove('.git')
            dirs[:] = []  # Don't recurse into repo
    return repos

def search_repo(repo, pattern, file_pattern=None):
    cmd = ['git', '-C', repo, 'grep', '-n', '-I', pattern]
    if file_pattern: cmd.extend(['--', file_pattern])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return [(repo, line) for line in r.stdout.strip().split('\n') if line]
    except: pass
    return []

def main():
    p = argparse.ArgumentParser(description='Search across git repos')
    p.add_argument('pattern', help='Search pattern')
    p.add_argument('base', nargs='?', default='.', help='Base directory')
    p.add_argument('-f', '--file', help='File pattern (e.g., "*.py")')
    p.add_argument('-d', '--depth', type=int, default=3)
    p.add_argument('-j', '--jobs', type=int, default=8)
    p.add_argument('-l', '--files-only', action='store_true', help='Show filenames only')
    args = p.parse_args()

    repos = find_repos(os.path.abspath(args.base), args.depth)
    if not repos:
        print("No git repos found."); return
    
    print(f"Searching {len(repos)} repos for '{args.pattern}'...\n")
    total = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futures = {ex.submit(search_repo, repo, args.pattern, args.file): repo for repo in repos}
        for f in concurrent.futures.as_completed(futures):
            results = f.result()
            if results:
                repo = os.path.basename(results[0][0])
                if args.files_only:
                    files = set(line.split(':')[0] for _, line in results)
                    for fn in sorted(files):
                        print(f"  {repo}/{fn}")
                else:
                    for _, line in results[:10]:
                        print(f"  {repo}/{line}")
                    if len(results) > 10:
                        print(f"  ... +{len(results)-10} more in {repo}")
                total += len(results)
    
    print(f"\n{total} matches across {len(repos)} repos")

if __name__ == '__main__':
    main()
