import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from file_manager import FileSystemAgent
from computer_tasks import ComputerTasks, parse_command
import orchestrator
import screen_agent

class Files(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = []
        self.agent = FileSystemAgent([self.root], protected=[], audit=self.events.append)
    def tearDown(self): self.temp.cleanup()
    def put(self, path, text='hello'):
        p=self.root/path; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def test_exact_duplicates_and_partial(self):
        self.put('a/brain.py');self.put('b/brain.py');self.put('brain_extra.py')
        report=self.agent.search('brain.py')
        self.assertEqual(len(report.matches),3)
        self.assertEqual(len(report.duplicates['brain.py']),2)
        self.assertEqual(len(self.agent.search('extra').matches),1)
    def test_extension_fuzzy_latest(self):
        a=self.put('Tahrun.py');b=self.put('web.html')
        self.assertEqual(self.agent.search('Tahrn.py').matches,[str(a)])
        self.assertEqual(self.agent.search(extensions=['html']).matches,[str(b)])
        os.utime(a,(1,1));os.utime(b,(2,2))
        self.assertEqual(self.agent.search(latest=True).matches[0],str(b))
    def test_bounds(self):
        self.put('a.py');self.put('b.py')
        self.assertTrue(self.agent.search(limit=1).truncated)
        self.assertTrue(self.agent.search(max_entries=1).truncated)
        with self.assertRaises(ValueError):self.agent.search(limit=0)
    def test_paths(self):
        with self.assertRaises(PermissionError): self.agent.path(self.root.parent/'escape')
        self.put('secret.py')
        (self.root/'link').symlink_to(self.root/'secret.py')
        with self.assertRaises(PermissionError):self.agent.read_text(self.root/'link')
        self.assertNotIn(str(self.root/'link'),self.agent.search().matches)
    def test_protected(self):
        a=FileSystemAgent([self.root],protected=[self.root/'protected'])
        with self.assertRaises(PermissionError):a.create_folder(self.root/'protected'/'x')
    def test_create_edit_permission_backup_and_read(self):
        p=self.root/'hello.py';self.agent.write_text(p,'one')
        with self.assertRaises(PermissionError):self.agent.write_text(p,'two')
        self.assertEqual(p.read_text(),'one')
        self.agent.approve=lambda op,path:True
        self.agent.write_text(p,'two')
        self.assertEqual(self.agent.read_text(p),'two')
        self.assertEqual(next(self.root.glob('hello.py.jarvis-backup-*')).read_text(),'one')
        self.assertTrue(self.events)
    def test_move_no_overwrite(self):
        a=self.put('a.py');b=self.put('b.py')
        with self.assertRaises(FileExistsError):self.agent.move(a,b)
        dst=self.root/'c.py';self.agent.move(a,dst)
        self.assertFalse(a.exists());self.assertEqual(dst.read_text(),'hello')
    def test_explorer_dispatch(self):
        p=self.put('file with spaces.py')
        with patch('file_manager.os.name','nt'),patch('file_manager.subprocess.Popen') as popen:
            # Patch Path factory to avoid Posix host selecting WindowsPath.
            with patch.object(self.agent,'path',return_value=p):
                self.agent.reveal(p)
            popen.assert_called_once_with(['explorer.exe','/select,',str(p)],shell=False)
    def test_disambiguation_and_expiry(self):
        self.put('a/brain.py');self.put('b/brain.py');c=ComputerTasks(self.agent)
        ok,msg=c.execute(parse_command('find brain.py and open it in File Explorer'))
        self.assertTrue(ok);self.assertIsNotNone(c.pending)
        with patch.object(self.agent,'reveal',return_value='dispatched') as reveal:
            self.assertEqual(c.execute(parse_command('choose 2')),(True,'dispatched'))
            reveal.assert_called_once()
        c.execute(parse_command('find brain.py'))
        c.pending=(0,c.pending[1],False)
        self.assertFalse(c.execute(parse_command('choose 1'))[0])
    def test_project_and_failure_recovery(self):
        c=ComputerTasks(self.agent)
        task=parse_command(f'create a Python project inside {self.root} with main.py, brain.py and requirements.txt')
        self.assertTrue(c.execute(task)[0]);self.assertEqual(len(list((self.root/'PythonProject').iterdir())),3)
        self.assertFalse(c.execute(task)[0])
        self.assertEqual(len(c.run_steps([{'operation':'bad'},task])),1)
    def test_project_traversal_rejected(self):
        c=ComputerTasks(self.agent)
        self.assertFalse(c.execute({'operation':'project','directory':str(self.root),'files':['../bad.py']})[0])
        self.assertFalse((self.root/'PythonProject').exists())
    def test_approval_change_detected(self):
        p=self.put('a.py','old')
        def approve(*_):p.write_text('external');return True
        self.agent.approve=approve
        with self.assertRaises(OSError):self.agent.write_text(p,'new')
        self.assertEqual(p.read_text(),'external')

class Routing(unittest.TestCase):
    def test_commands(self):
        for command in ['Jarvis, find Tahrun.py','where is brain.py?','find my Python coding files','search for my HTML files','find the latest project file']:
            self.assertEqual(parse_command(command)['operation'],'find')
        self.assertEqual(parse_command('find Tahrun.py')['query'],'Tahrun.py')
        self.assertIsNone(parse_command('find save on my screen'))
    def test_preserve_brain(self):
        calls=[]
        self.assertEqual(orchestrator.route('hello',lambda x:calls.append(x) or {'action':'chat'}),{'action':'chat'})
        self.assertEqual(calls,['hello'])
        self.assertEqual(orchestrator.route('find a.py',lambda _:self.fail())['action'],'computer_task')
    def test_tahrun_integrates_without_importing_audio(self):
        tree=ast.parse(Path('Tahrun.py').read_text())
        execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        self.assertIn('computer_task',ast.unparse(execute))
    def test_gui_failure(self):
        with patch.dict(sys.modules,{'pyautogui':None}):
            self.assertFalse(screen_agent.type_text('hello')[0])
    def test_ocr_missing(self):
        with patch.dict(sys.modules,{'pytesseract':None}):
            self.assertFalse(screen_agent.read_visible_text()[0])
    def test_ocr_success_and_cleanup(self):
        import screen_vision
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'screen.jpg';Image.new('RGB',(10,10),'white').save(p)
            fake=MagicMock();fake.image_to_string.return_value='Visible error text'
            with patch.dict(sys.modules,{'pytesseract':fake}),patch.object(screen_vision,'_capture',return_value=(p,10,10,10,10)):
                self.assertEqual(screen_agent.read_visible_text(),(True,'Visible error text'))
            self.assertFalse(p.exists())

if __name__=='__main__':unittest.main()

class GuiAndCommands(unittest.TestCase):
    def test_gui_dispatch_and_error(self):
        fake=MagicMock()
        with patch.dict(sys.modules,{'pyautogui':fake}):
            self.assertTrue(screen_agent.type_text('test')[0])
            self.assertTrue(screen_agent.press('enter')[0])
            self.assertTrue(screen_agent.scroll(-3)[0])
            fake.write.assert_called_once_with('test',interval=.01)
            fake.scroll.side_effect=RuntimeError('disconnected')
            self.assertFalse(screen_agent.scroll(-3)[0])
    def test_screenshot_failure_is_reported(self):
        fake=MagicMock();fake.screenshot.side_effect=RuntimeError('no display')
        with tempfile.TemporaryDirectory() as folder, patch.object(screen_agent,'SCREENSHOT_DIR',Path(folder)),patch.dict(sys.modules,{'pyautogui':fake}):
            self.assertFalse(screen_agent.screenshot()[0])
    def test_file_and_window_commands(self):
        for command,op in [('read file /tmp/a.py','read'),('write file /tmp/a.py with content print(1)','write'),('create folder /tmp/work','mkdir'),('rename file /tmp/a.py to /tmp/b.py','move'),('switch to window Visual Studio Code','switch')]:
            self.assertEqual(parse_command(command)['operation'],op)
    def test_window_ambiguity(self):
        fake=MagicMock();fake.Desktop.return_value.windows.return_value=[MagicMock(),MagicMock()]
        for window in fake.Desktop.return_value.windows.return_value:window.window_text.return_value='Editor'
        with patch.dict(sys.modules,{'pywinauto':fake}):
            self.assertFalse(screen_agent.switch_window('Editor')[0])
