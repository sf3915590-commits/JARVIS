"""Thin desktop/file coordinator; does not replace existing agents or brain."""
import os
import re
import time
from pathlib import Path
from file_manager import FileSystemAgent, _CODE


def parse_command(command):
    text = re.sub(r'^(?:hey\s+)?jarvis[,\s:-]*', '', str(command).strip(), flags=re.I)
    if re.fullmatch(r'(?:choose|select|use)\s+\d+', text, re.I):
        return {'action':'computer_task', 'operation':'choose', 'number':int(text.split()[-1])}
    match = re.fullmatch(r'(?:find|search for|where is|locate)\s+(.+?)(?:\s+and\s+(open it in file explorer|show it in file explorer))?[?.]?', text, re.I)
    if match and not re.search(r'\bon (?:my |the )?screen\b', text, re.I):
        query = match.group(1).rstrip('?')
        extensions = None
        for word, suffix in [('python','.py'), ('html','.html'), ('javascript','.js'), ('css','.css'), ('json','.json'), ('java','.java'), ('cpp','.cpp')]:
            if re.search(r'\b'+word+r'\s+(?:coding\s+)?files\b', query, re.I):
                extensions, query = [suffix], ''
                break
        if re.fullmatch(r'(?:my )?(?:coding|code) files', query, re.I): extensions, query = sorted(_CODE), ''
        latest = bool(re.fullmatch(r'(?:the |my )?latest project file', query, re.I))
        if latest: query, extensions = '', sorted(_CODE)
        return {'action':'computer_task','operation':'find','query':query,'extensions':extensions,'latest':latest,'reveal':bool(match.group(2))}
    match = re.fullmatch(r'create a python project inside (.+?) with (.+)', text, re.I)
    if match:
        return {'action':'computer_task','operation':'project','directory':match.group(1),'files':re.split(r'\s*,\s*|\s+and\s+',match.group(2))}
    match = re.fullmatch(r'(?:open folder|navigate to|go to folder)\s+(.+)', text, re.I)
    if match: return {'action':'computer_task','operation':'folder','path':match.group(1)}
    match = re.fullmatch(r'(read file|create folder|open in explorer|switch to window)\s+(.+)', text, re.I)
    if match:
        return {'action':'computer_task','operation':{'read file':'read','create folder':'mkdir','open in explorer':'folder','switch to window':'switch'}[match.group(1).casefold()], 'path':match.group(2)}
    match = re.fullmatch(r'(?:write file|edit file)\s+(.+?)\s+with content\s+([\s\S]+)', text, re.I)
    if match: return {'action':'computer_task','operation':'write','path':match.group(1),'content':match.group(2)}
    match = re.fullmatch(r'(?:move file|rename file)\s+(.+?)\s+to\s+(.+)', text, re.I)
    if match: return {'action':'computer_task','operation':'move','path':match.group(1),'destination':match.group(2)}
    if text.casefold() in {'read visible text','read screen text','ocr screen'}:
        return {'action':'computer_task','operation':'ocr'}
    return None


class ComputerTasks:
    def __init__(self, files=None):
        self.files = files or FileSystemAgent()
        self.pending = None

    def directory(self, value):
        aliases = {'my desktop folder':'Desktop','desktop':'Desktop','my documents folder':'Documents','documents':'Documents','downloads':'Downloads'}
        return self.files.path(Path.home()/aliases[value.casefold()] if value.casefold() in aliases else value)

    def execute(self, task):
        try:
            op = task.get('operation')
            if op == 'choose':
                pending, self.pending = self.pending, None
                if not pending or time.monotonic() > pending[0]:
                    return False, 'Selection expire ho gayi; dobara search karo.'
                n = task['number']
                if not 1 <= n <= len(pending[1]): return False, 'Invalid result number; dobara search karo.'
                path = pending[1][n-1]
                return True, self.files.reveal(path) if pending[2] else path
            self.pending = None  # New command invalidates old disambiguation.
            if op == 'find':
                result = self.files.search(task.get('query',''), extensions=task.get('extensions'), latest=task.get('latest',False))
                paths = result.matches
                if not paths: return False, 'Koi matching file nahi mili.' + (' Search incomplete thi.' if result.truncated or result.errors else '')
                summary = '\n'.join(f'{i}. {p}' for i,p in enumerate(paths,1))
                if result.truncated or result.errors:
                    return True, summary + '\nSearch incomplete; limited results hain. Automatic selection nahi ki.'
                if len(paths) == 1 and task.get('reveal'): return True, self.files.reveal(paths[0])
                if len(paths)>1:
                    self.pending = (time.monotonic()+60, paths, task.get('reveal',False))
                    summary += '\nMultiple matches; choose <number> bolo. Selection 60 seconds valid hai.'
                return True, summary
            if op == 'read': return True, self.files.read_text(task['path'])
            if op == 'write': return True, 'Write verify hua: '+self.files.write_text(task['path'],task['content'])
            if op == 'mkdir': return True, 'Folder verify hua: '+self.files.create_folder(task['path'])
            if op == 'move': return True, 'Move verify hua: '+self.files.move(task['path'],task['destination'])
            if op == 'switch':
                import screen_agent
                return screen_agent.switch_window(task['path'])
            if op == 'folder': return True, self.files.reveal(self.directory(task['path']))
            if op == 'project':
                parent = self.directory(task['directory'])
                names = [n.strip() for n in task['files']]
                if not names or len(names)>30 or len(set(n.casefold() for n in names)) != len(names): raise ValueError('Invalid/duplicate filenames')
                for name in names:
                    if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:py|txt|json|md)', name): raise ValueError('Use simple Python project filenames')
                target = parent/'PythonProject'
                # Preflight all paths before creating anything. No existing project overwritten.
                self.files.path(target, write=True)
                if target.exists(): raise FileExistsError('PythonProject already exists; choose a different directory')
                self.files.create_folder(target)
                written = []
                try:
                    for name in names:
                        self.files.write_text(target/name, '')
                        written.append(name)
                except Exception as exc:
                    return False, f'Partial project: {target}; created {written}; error: {exc}. Existing work delete nahi kiya.'
                return True, f'Project files verify ho gayi: {target}: '+', '.join(written)
            if op == 'ocr':
                import screen_agent
                return screen_agent.read_visible_text()
            return False, 'Unsupported computer task'
        except Exception as exc:
            return False, f'Computer task failed: {exc}'

    def run_steps(self, steps):
        """Bounded deterministic plan: no implicit retry of side effects."""
        if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
            raise ValueError('Plan needs 1-20 steps')
        outcomes = []
        for step in steps:
            ok, message = self.execute(step)
            outcomes.append({'success':ok, 'message':message})
            if not ok or self.pending:
                break
        return outcomes

_service = None

def execute_task(task, approve=None):
    global _service
    if _service is None:
        roots = os.environ.get('JARVIS_FILE_ROOTS','').split(os.pathsep)
        import logging
        from logging.handlers import RotatingFileHandler
        logger = logging.getLogger('jarvis.computer.files')
        if not logger.handlers:
            logdir = Path.home()/'.jarvis'/'logs'
            logdir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(logdir/'computer-actions.jsonl', maxBytes=1024*1024, backupCount=2, encoding='utf-8')
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
        _service = ComputerTasks(FileSystemAgent(roots=[r for r in roots if r] or None))
    _service.files.approve = approve or (lambda operation, path: False)
    return _service.execute(task)
