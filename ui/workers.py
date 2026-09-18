"""Bakgrundsarbete som delas av dialogerna.

Klassen låg i ui/radio_dialog.py. Tema-dialogen behövde samma sak för sina
GitHub-anrop, men körde dem rakt på GUI-tråden: katalogen hämtades när
dialogen öppnades, sökningen vid knapptryck och installationen när zip-filen
skulle hämtas — alla med urllib-timeouts på 5-8 sekunder, alltså upp till
flera sekunders fryst fönster.
"""
from PyQt6.QtCore import QObject, pyqtSignal


class BackgroundWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, target_fn, *args, **kwargs):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.target_fn(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))
