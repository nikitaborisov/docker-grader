import pathlib
from collections import namedtuple, defaultdict
from datetime import datetime
from heapq import heappush, heappop
from subprocess import Popen, PIPE, check_call, check_output, CalledProcessError
import sys
import time
import logging
import shelve
from fcntl import flock, LOCK_EX
import ago

QueueEntry = namedtuple(
    'QueueEntry', ['attempts', 'time', 'version', 'name', 'parent'])

log = logging.getLogger(__name__)

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

    def __str__(self):
        return '[{}]'.format(', '.join("{}v{} ({})".format(qe.name, qe.version,
            qe.attempts) for qe in self.queue))

    def __len__(self):
        return len(self.names)

    def __bool__(self):
        return bool(self.names)


QUEUE = GradingQueue()

def dump_queue(queue=QUEUE, output="queue.html"):
    with open(output, 'w') as outfile:
        outfile.write('''
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autograder Queue</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
</head>
<body>
  <div class="container">
  <h1>Autograder Queue</h1>

  <p>Last updated: {}</p>

  <table class="table">
  <thead>
      <tr>
          <th>Team</th>
          <th>Version</th>
          <th>Waiting since</th>
          <th>Total attempts</th>
     </tr>
   </thead>
   <tbody>
'''.format(datetime.now().ctime()))
        for qe in queue.queue:
            outfile.write('''
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
        </tr>
'''.format(qe.name, qe.version, ago.human(qe.time, precision=1), qe.attempts))
        outfile.write('''
    </tbody>
</table>
</div>
</body>
</html>
''')


GRADED = None   # make sure it's a global variable

OUTFILE = "GRADING_OUTPUTv1"

def scan_dir(svn_dir, version_pat):
    for version_filename in svn_dir.glob(version_pat):
        with version_filename.open() as version_file:
            try:
                version_line = version_file.readline().strip()
                version = int(version_line)
            except ValueError:
                log.error("Incorrect version format: %s", version_line)
                continue
        name = version_filename.parts[-3]
        # for output_path in (version_filename.parent.glob("{}.*".format(OUTFILE))):
        #     output_name = str(output_path)
        #     dot = output_name.rfind('.')
        #     GRADED[name].add(int(output_name[dot+1:]))
        if version in GRADED[name]:
            continue
        attempts = len(GRADED[name])
        QUEUE.push(QueueEntry(attempts, datetime.now(), version, name,
                              version_filename.parent))

def grade_one():
    try:
        out = check_output(["svn", "update", str(SVN_DIR)])
        logging.error("Svn update: %s", out)
    except CalledProcessError:
        logging.error("Error during svn update")
    scan_dir(SVN_DIR, VERSION_PAT)
    logging.info("Queue is %s", QUEUE)
    dump_queue()
    if QUEUE:
        qe = QUEUE.pop()
        logging.info("Grading %s version %s", qe.name, qe.version)
        if "-n" not in sys.argv[1:]:
            p = Popen(["python3", "run_tests.py", str(qe.parent)],
                      stdout=PIPE)
            out, _ = p.communicate()
            GRADED[qe.name].add(qe.version)
            out_fn = qe.parent / "{}.{}".format(OUTFILE, qe.version)
            if out_fn.exists():
                logging.warning("Warning, overwriting output file %s", out_fn)
            with out_fn.open("wb") as outf:
                outf.write(out)
            if "-q" not in sys.argv[1:]:    # -q: don't commit
                try:
                    check_call(["svn", "add", str(out_fn)])
                    check_call(["svn", "commit", "-m",
                                "Autograder output for {} version {}".format(qe.name,
                                                                             qe.version), str(out_fn)])
                except CalledProcessError:
                    logging.error("Error during svm commit of %s", str(out_fn))
    else:
        logging.info("Queue Empty, sleeping")
        time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)-15s %(message)s",
                        filename="watch.log", level=logging.INFO)
    SVN_DIR = pathlib.Path(sys.argv[1])
    VERSION_PAT = "*/{}/VERSION".format(sys.argv[2])
    ATTEMPTS_FILE = "attempts.db"
    LOCK_FILE = ATTEMPTS_FILE + ".lock"
    with open(LOCK_FILE, 'w') as lock_file:
        log.info("Acquiring shelf lock")
        flock(lock_file.fileno(), LOCK_EX)
        log.info("Shelf lock acquired")
        with shelve.open(ATTEMPTS_FILE, writeback=True) as db:
            if "attempts" not in db:
                db["attempts"] = defaultdict(set)
            GRADED = db["attempts"]
            while True:
                grade_one()
                db.sync()
