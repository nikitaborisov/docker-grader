import pathlib
from collections import namedtuple, defaultdict
from datetime import datetime
from heapq import heappush, heappop
from subprocess import Popen, PIPE
import sys
import time


QueueEntry = namedtuple('QueueEntry', ['attempts', 'time', 'version', 'name', 'parent'])

class GradingQueue():
    """ Grading queue is sorted by:
    - smallest # of attempts
    - then by earliest addition time
    """
    def __init__(self):
        self.queue = []
        self.names = {}

    def push(self, qe):
        if qe.name in self.names and qe.version == self.names[qe.name].version:
            return
            # already in queue, don't bother waiting
        heappush(self.queue, qe)
        self.names[qe.name] = qe

    def pop(self):
        while True:
            qe = heappop(self.queue)
            if qe == self.names[qe.name]:
                # this one actually needs to be processed
                break
        del self.names[qe.name]
        return qe

    def __len__(self):
        return len(self.names)

    def __bool__(self):
        return bool(self.names)

QUEUE = GradingQueue()
GRADED = defaultdict(list)

def scan_dir(svn_dir, version_pat):
    for version_filename in svn_dir.glob(version_pat):
        with version_filename.open() as version_file:
            version = int(version_file.readline().strip())
        name = version_filename.parts[-3]
        attempts = 0
        if version in GRADED[name]:
                continue
        attempts = len(GRADED[name])
        QUEUE.push(QueueEntry(attempts, datetime.now(), version, name,
                              version_filename.parent))

if __name__=="__main__":
    SVN_DIR=pathlib.Path(sys.argv[1])
    VERSION_PAT="*/{}/VERSION".format(sys.argv[2])
    while True:
        scan_dir(SVN_DIR, VERSION_PAT)
        if QUEUE:
            qe = QUEUE.pop()
            print("Grading {} version {}".format(qe.name, qe.version))
            p = Popen(["python3", "run_tests.py", str(qe.parent)],
                      stdout=PIPE)
            out, _ = p.communicate()
            GRADED[qe.name].append(qe.version)
            with (qe.parent / "GRADED.{}".format(qe.version)).open("wb") as outf:
                outf.write(out)
        else:
            print("Queue Empty, sleeping")
            time.sleep(30)