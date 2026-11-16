import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch
import httpx
from agent import run_cmd, Decision, decide, execute_tool

class AgentTests(unittest.TestCase):
    def test_python_write_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'even_or_odd.py'
            invalid = Decision(type='write_file', path=str(path), content='def f():\nreturn 1')
            self.assertFalse(execute_tool(invalid, folder)['success'])
            self.assertFalse(path.exists())
            code = 'def parity(n):\n    return "Even" if n % 2 == 0 else "Odd"\n'
            valid = Decision(type='write_file', path=str(path), content=code)
            self.assertTrue(execute_tool(valid, folder)['success'])
            self.assertEqual(path.read_text(), code)
            self.assertFalse(execute_tool(valid, folder)['success'])
            namespace = {}
            exec(code, namespace)
            for n in (0, 2, -4):
                self.assertEqual(namespace['parity'](n), 'Even')
            for n in (1, -3):
                self.assertEqual(namespace['parity'](n), 'Odd')

    def test_quoted_paths(self):
        with tempfile.TemporaryDirectory(prefix='agent space ') as folder:
            target = Path(folder) / 'rishi test.txt'
            self.assertEqual(run_cmd(f'echo hello>"{target}"', folder)['exit_code'], 0)
            self.assertIn('hello', run_cmd(f'type "{target}"', folder)['stdout'])
            result = run_cmd(f'dir /b "{folder}"', folder)
            self.assertEqual(result['exit_code'], 0, result)
            self.assertIn(target.name, result['stdout'])

    def test_repair_prose_response(self):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={'content': 'It seems there was an issue.' if len(requests) == 1 else '{"type":"tool","command":"tasklist"}'})
        client = httpx.Client(transport=httpx.MockTransport(handler))
        history = [{'role':'user','content':'List processes'}]
        with patch('agent.httpx.Client', return_value=client):
            self.assertEqual(decide('https://example.test', 'key', history).command, 'tasklist')
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(history), 1)

    def test_file_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(run_cmd('echo hello>test.txt', folder)['exit_code'], 0)
            self.assertIn('hello', run_cmd('type test.txt', folder)['stdout'])
            self.assertEqual(run_cmd('exit /b 7', folder)['exit_code'], 7)

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(run_cmd('ping -n 10 127.0.0.1', folder, 1)['timed_out'])

    def test_protocol(self):
        self.assertEqual(Decision.model_validate_json('{"type":"tool","command":"tasklist"}').command, 'tasklist')
        with self.assertRaises(ValueError):
            Decision.model_validate_json('{"type":"execute","command":"tasklist"}')

if __name__ == '__main__':
    unittest.main()
