import fcntl

class FileLock:
    def __init__(self, filename, mode = fcntl.LOCK_EX):
        self.filename = filename
        self.mode = mode
        self.file = None

    def lock(self):
        self.file = open(self.filename, 'w')
        fcntl.flock(self.file, self.mode)

    def unlock(self):
        if not self.file:
            raise RuntimeError("Called unlock without calling lock")
        self.file.close()   # lock released automatically
        self.file = None


    def __enter__(self):
        self.lock()

    def __exit__(self, exc_type, exc_value, traceback):
        self.unlock()
