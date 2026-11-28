import os


# ==========================================
# TAHRUN FILE MANAGER
# ==========================================

def get_folder(folder_name):

    home = os.path.expanduser("~")

    folders = {
        "downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "desktop": os.path.join(home, "Desktop"),
        "pictures": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "music": os.path.join(home, "Music"),
    }

    return folders.get(folder_name.lower())


def open_folder(folder_name):

    folder = get_folder(folder_name)

    if not folder:
        print("❌ Folder identify nahi hua.")
        return False

    if not os.path.exists(folder):
        print("❌ Folder nahi mila:", folder)
        return False

    try:
        os.startfile(folder)

        print("📁 Folder opened:", folder)

        return True

    except Exception as error:

        print("❌ Folder open error:", error)

        return False


def search_files(search_text, search_location=None):

    if not search_location:
        search_location = os.path.expanduser("~")

    search_text = search_text.lower()

    results = []

    print("\n🔎 File search:", search_text)

    try:

        for root, dirs, files in os.walk(search_location):

            for filename in files:

                if search_text in filename.lower():

                    full_path = os.path.join(
                        root,
                        filename
                    )

                    results.append(full_path)

                    print("📄", full_path)

                    # First 20 results only
                    if len(results) >= 20:
                        return results

    except PermissionError:

        pass

    except Exception as error:

        print("❌ Search error:", error)

    return results


def open_file(file_path):

    if not os.path.exists(file_path):

        print("❌ File nahi mili.")

        return False

    try:

        os.startfile(file_path)

        print("📄 File opened:", file_path)

        return True

    except Exception as error:

        print("❌ File open error:", error)

        return False


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("📁 Tahrun File Manager")
    print("----------------------")

    print(
        "Downloads:",
        get_folder("downloads")
    )

    print(
        "Documents:",
        get_folder("documents")
    )
# ==========================================
# PDF READER
# ==========================================

def read_pdf(file_path):
    import PyPDF2

    if not os.path.exists(file_path):
        print("❌ PDF nahi mili:", file_path)
        return False, ""

    try:
        with open(file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        print("📕 PDF read complete:", file_path)
        print("📄 Pages:", len(reader.pages))

        return True, text

    except Exception as error:
        print("❌ PDF read error:", error)
        return False, ""

# Scoped advanced operations; legacy APIs above remain compatible.
from pathlib import Path
from dataclasses import dataclass
import difflib
import json
import time
import logging
import stat
import subprocess

_AUDIT = logging.getLogger('jarvis.computer.files')
_SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'AppData'}
_CODE = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.java', '.cpp', '.c', '.h'}

@dataclass
class SearchReport:
    matches: list
    duplicates: dict
    truncated: bool = False
    errors: int = 0

class FileSystemAgent:
    """Local owner-scoped operations, with no shell or code execution."""
    def __init__(self, roots=None, protected=None, approve=None, audit=None):
        self.roots = tuple(Path(p).expanduser().resolve(strict=True) for p in (roots or [Path.home()]))
        self.protected = tuple(Path(p).resolve() for p in (protected if protected is not None else [Path(__file__).parent]))
        self.approve = approve or (lambda operation, path: False)
        self.audit = audit or (lambda event: _AUDIT.info(json.dumps(event)))

    def path(self, value, write=False):
        raw = Path(value).expanduser().absolute()
        for part in (raw, *raw.parents):
            if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
                raise PermissionError('Symlink/junction paths are not permitted')
            if part.exists() and getattr(part.stat(), 'st_file_attributes', 0) & 0x400:
                raise PermissionError('Reparse paths are not permitted')
        p = raw.resolve()
        if any(part.casefold() in {'.ssh', '.aws', '.azure', '.gnupg', '.env', '.jarvis'} or part.casefold().startswith('.env.') for part in p.parts):
            raise PermissionError('Credential/private configuration location is restricted')
        if not any(p == root or root in p.parents for root in self.roots):
            raise PermissionError('Path is outside permitted roots')
        if write and any(p == root or root in p.parents for root in self.protected):
            raise PermissionError('Protected project directory')
        return p

    def search(self, query='', root=None, extensions=None, fuzzy=True, latest=False,
               limit=100, max_entries=100000, seconds=5):
        if not 1 <= limit <= 1000 or not 1 <= max_entries <= 1000000 or not 0 < seconds <= 30:
            raise ValueError('Invalid search bounds')
        roots = [self.path(root)] if root else self.roots
        query = str(query).strip().casefold()
        exts = {'.' + str(e).lstrip('.').casefold() for e in (extensions or [])}
        candidates, errors, count, truncated = [], 0, 0, False
        deadline = time.monotonic() + seconds
        def error(_):
            nonlocal errors
            errors += 1
        for base in roots:
            for folder, dirs, files in os.walk(base, followlinks=False, onerror=error):
                count += 1
                if count > max_entries or time.monotonic() > deadline:
                    truncated = True
                    break
                safe_dirs = []
                for d in sorted(dirs):
                    if d in _SKIP:
                        continue
                    try:
                        self.path(Path(folder) / d)
                        safe_dirs.append(d)
                    except (OSError, ValueError):
                        errors += 1
                dirs[:] = safe_dirs
                for name in sorted(files):
                    count += 1
                    if count > max_entries or time.monotonic() > deadline:
                        truncated = True
                        break
                    try:
                        p = self.path(Path(folder) / name)
                        if not p.is_file() or (exts and p.suffix.casefold() not in exts):
                            continue
                        folded = name.casefold()
                        score = 3 if folded == query else 2 if query in folded else 0
                        if not score and fuzzy and query:
                            ratio = difflib.SequenceMatcher(None, query, folded).ratio()
                            score = ratio if ratio >= .70 else 0
                        if not query or score:
                            candidates.append((score, p.stat().st_mtime, str(p)))
                    except (OSError, ValueError):
                        errors += 1
                if truncated:
                    break
            if truncated:
                break
        candidates.sort(key=lambda row: (-row[1], row[2].casefold()) if latest else (-row[0], row[2].casefold()))
        truncated = truncated or len(candidates) > limit
        matches = [row[2] for row in candidates[:limit]]
        names = {}
        for p in matches:
            names.setdefault(Path(p).name.casefold(), []).append(p)
        return SearchReport(matches, {k:v for k,v in names.items() if len(v)>1}, truncated, errors)

    def read_text(self, value, max_bytes=1024*1024):
        p = self.path(value)
        if p.stat().st_size > max_bytes:
            raise ValueError('File exceeds read limit')
        return p.read_text(encoding='utf-8')

    def create_folder(self, value):
        p = self.path(value, write=True)
        self.audit({'operation':'mkdir', 'path':str(p), 'phase':'intent'})
        p.mkdir(parents=True, exist_ok=False)
        if not p.is_dir():
            raise OSError('Folder verification failed')
        return str(p)

    def write_text(self, value, content):
        p = self.path(value, write=True)
        if not isinstance(content, str) or len(content.encode('utf-8')) > 1024*1024:
            raise ValueError('Text must be at most 1 MiB')
        exists = p.exists()
        old = p.read_bytes() if exists else None
        if exists and not self.approve('overwrite', str(p)):
            raise PermissionError('Explicit overwrite approval required')
        if exists and p.read_bytes() != old:
            raise OSError('File changed during approval')
        self.audit({'operation':'write', 'path':str(p), 'phase':'intent'})
        if exists:
            # Exclusive backup retained beside edited file; never replace an old backup.
            import uuid
            backup = p.with_name(p.name + '.jarvis-backup-' + uuid.uuid4().hex)
            with backup.open('xb') as stream:
                stream.write(old)
            import tempfile
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.jarvis-')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, p)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
        else:
            with p.open('x', encoding='utf-8', newline='') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        if p.read_text(encoding='utf-8') != content:
            raise OSError('Write verification failed')
        self.audit({'operation':'write', 'path':str(p), 'phase':'verified'})
        return str(p)

    def move(self, source, destination):
        src, dst = self.path(source, write=True), self.path(destination, write=True)
        if not src.is_file(): raise ValueError('Only regular-file moves supported')
        if dst.exists(): raise FileExistsError(str(dst))
        self.audit({'operation':'move', 'path':str(src), 'destination':str(dst), 'phase':'intent'})
        # Hard-link + unlink avoids silently overwriting a raced destination.
        # Cross-volume moves fail safely and leave the source untouched.
        os.link(src, dst)
        try:
            src.unlink()
        except OSError:
            dst.unlink()
            raise
        if src.exists() or not dst.is_file(): raise OSError('Move verification failed')
        return str(dst)

    def reveal(self, value):
        p = self.path(value)
        if not p.exists(): raise FileNotFoundError(str(p))
        if os.name != 'nt': raise OSError('Windows File Explorer requires Windows')
        args = ['explorer.exe', '/select,', str(p)] if p.is_file() else ['explorer.exe', str(p)]
        self.audit({'operation':'explorer', 'path':str(p), 'phase':'dispatch'})
        subprocess.Popen(args, shell=False)
        return 'Explorer request bheji; window selection live verify nahi hui.'
