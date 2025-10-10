import time, os, sys, subprocess
from git import Repo, InvalidGitRepositoryError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIRS = ["ritt", "."]  # katalogi do śledzenia
IGNORE_EXT = {".pyc", ".log"}
COMMIT_MSG = "autosync: save"

def is_ignored(path):
    _, ext = os.path.splitext(path)
    return ext in IGNORE_EXT or "/.git/" in path.replace("\\", "/")

class Handler(FileSystemEventHandler):
    def __init__(self, repo):
        self.repo = repo
        self._pending = False

    def on_any_event(self, event):
        if event.is_directory or is_ignored(event.src_path):
            return
        self._pending = True

def main():
    try:
        repo = Repo(os.getcwd())
    except InvalidGitRepositoryError:
        print("Init git first: git init && git add . && git commit -m 'init'")
        sys.exit(1)

    event_handler = Handler(repo)
    observer = Observer()
    for d in WATCH_DIRS:
        if os.path.isdir(d):
            observer.schedule(event_handler, d, recursive=True)
    observer.start()

    print("Auto-sync ON. Watching for changes… Ctrl+C to stop.")
    try:
        while True:
            if event_handler._pending:
                event_handler._pending = False
                time.sleep(2)  # debounce
                repo.git.add(all=True)
                if repo.is_dirty(index=True, working_tree=True, untracked_files=True):
                    repo.index.commit(COMMIT_MSG)
                    try:
                        repo.git.push("-u", "origin", repo.active_branch.name)
                    except Exception:
                        subprocess.run(["git", "push", "-u", "origin", "main"], check=False)
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
