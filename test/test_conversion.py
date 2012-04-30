import json
import os.path
import shutil
import sys
import tempfile
import time

from mvc import video
from mvc import converter
from mvc import conversion

import base


class FakeConverterInfo(converter.ConverterInfo):

    extension = 'fake'

    def get_executable(self):
        return sys.executable

    def get_arguments(self, video, output):
        return ['-u', os.path.join(
                os.path.dirname(__file__), 'testdata', 'fake_converter.py'),
                video.filename, output]

    def process_status_line(self, video, line):
        return json.loads(line)


class ConversionManagerTest(base.Test):

    def setUp(self):
        base.Test.setUp(self)
        self.converter = FakeConverterInfo('Fake')
        self.manager = conversion.ConversionManager()
        self.temp_dir = tempfile.mkdtemp()
        self.changes = []

    def tearDown(self):
        base.Test.tearDown(self)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def changed(self, conversion):
        self.changes.append(
            {'status': conversion.status,
             'duration': conversion.duration,
             'progress': conversion.progress,
             'eta': conversion.eta
             })

    def spin(self, timeout):
        finish_by = time.time() + timeout
        while time.time() < finish_by and self.manager.running:
            self.manager.check_notifications()
            time.sleep(0.1)

    def start_conversion(self, filename, timeout=5):
        vf = video.VideoFile(filename)
        c = self.manager.start_conversion(vf, self.converter)
        c.listen(self.changed)
        self.assertTrue(self.manager.running)
        self.assertTrue(c in self.manager.in_progress)
        self.spin(timeout)
        self.assertFalse(self.manager.running)
        self.assertFalse(os.path.exists(c.temp_output))
        return c

    def test_initial(self):
        self.assertEqual(self.manager.notify_queue, set())
        self.assertEqual(self.manager.in_progress, set())
        self.assertFalse(self.manager.running)

    def test_conversion(self):
        filename = os.path.join(self.temp_dir, 'webm-0.webm')
        shutil.copyfile(os.path.join(self.testdata_dir, 'webm-0.webm'),
                        filename)
        c = self.start_conversion(filename)
        self.assertEqual(c.status, 'finished')
        self.assertEqual(c.progress, c.duration)
        self.assertEqual(c.progress_percent, 1.0)
        self.assertTrue(os.path.exists(c.output))
        self.assertEqual(file(c.output).read(), 'blank')
        self.assertEqual(self.changes, [
                {'status': 'converting', 'duration': 5.0, 'eta': 5.0,
                 'progress': 0.0},
                {'status': 'converting', 'duration': 5.0, 'eta': 4.0,
                 'progress': 1.0},
                {'status': 'converting', 'duration': 5.0, 'eta': 3.0,
                 'progress': 2.0},
                {'status': 'converting', 'duration': 5.0, 'eta': 2.0,
                 'progress': 3.0},
                {'status': 'converting', 'duration': 5.0, 'eta': 1.0,
                 'progress': 4.0},
                {'status': 'finished', 'duration': 5.0, 'eta': 0.0,
                 'progress': 5.0}
                ])

    def test_conversion_with_error(self):
        filename = os.path.join(self.temp_dir, 'error.webm')
        shutil.copyfile(os.path.join(self.testdata_dir, 'webm-0.webm'),
                        filename)
        c = self.start_conversion(filename)
        self.assertFalse(os.path.exists(c.output))
        self.assertEqual(c.status, 'failed')
        self.assertEqual(c.error, 'test error')

    def test_conversion_with_missing_executable(self):
        missing = sys.executable + '.does-not-exist'
        self.converter.get_executable = lambda: missing
        filename = os.path.join(self.temp_dir, 'webm-0.webm')
        shutil.copyfile(os.path.join(self.testdata_dir, 'webm-0.webm'),
                        filename)
        c = self.start_conversion(filename)
        self.assertEqual(c.status, 'failed')
        self.assertEqual(c.error, '%r does not exist' % missing)
        self.assertFalse(os.path.exists(c.output))