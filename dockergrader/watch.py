from pathlib import Path
from collections import namedtuple, defaultdict
from datetime import datetime
from heapq import heappush, heappop
from subprocess import *
import sys
import time
import logging
import shelve
import re
from fcntl import flock, LOCK_EX
from functools import total_ordering

QueueEntryBase = namedtuple(
    'QueueEntryBase', ['attempts', 'time', 'version', 'name', 'tests', 'parent'])

TESTS_UPPER_BOUND = 5

@total_ordering
class QueueEntry:
    def __init__(self, attempts, time, version, name, tests, parent):
        self.attempts = attempts
        self.time = time
        self.version = version
        self.name = name
        self.tests = tests
        self.parent = parent

    @property
    def _adj_attempts(self):
        if self.tests:
            return self.attempts + min(len(self.tests), TESTS_UPPER_BOUND)
        else:
            return self.attempts + TESTS_UPPER_BOUND

    @property
    def _sortkey(self):
        # last three are completely arbitrary for sorting
        return (self._adj_attempts, self.time, self.version, self.name, self.tests)

    def __hash__(self):
        return hash(self._sortkey)

    def __eq__(self, other):
        return self._sortkey == other._sortkey

    def __le__(self, other):
        return self._sortkey <= other._sortkey


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

    def sorted(self):
        for qe in sorted(self.queue):
            if qe != self.names[qe.name]:
                continue
            yield qe

    def __str__(self):
        return '[{}]'.format(', '.join("{}v{} ({})".format(qe.name, qe.version,
                                                           qe.attempts) for qe in self.queue))

    def __len__(self):
        return len(self.names)

    def __bool__(self):
        return bool(self.names)


QUEUE = GradingQueue()


def dump_queue(current=None, queue=QUEUE, output="queue.html"):
    with open(output, 'w') as outfile:
        outfile.write('''
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <title>Autograder Queue</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
    <script>
''')
        outfile.write('''
      const update_time = new Date({0}, {1}-1, {2}, {3}, {4}, {5});
'''.format(*datetime.now().timetuple()))
        outfile.write('''
      function update() {
        var now = new Date();
        var delta = Math.floor((now - update_time)/1000);
        var html = '';
        if (delta > 60) {
          if (delta > 3600) {
            html = Math.floor(delta/3600) + " hours, ";
          }
          html += Math.floor(delta/60) % 60 + " minutes, ";
        }
        html += delta % 60 + " seconds ago";
        document.getElementById('ago').innerHTML = html;
      }
      setInterval(update, 1000);
      update();

      </script>
''')
        outfile.write('''
</head>
<body>
  <div class="container">
  <h1>Autograder Queue</h1>

  <p>Last updated: {}, <span id="ago"></p>

  <table class="table">
  <thead>
      <tr>
          <th>Team</th>
          <th>Version</th>
          <th>Test to run</th>
          <th>Waiting since</th>
          <th>Total attempts</th>
     </tr>
   </thead>
   <tbody>
'''.format(datetime.now().ctime()))
        first_class = ' class="active"'
        entries = list(queue.sorted())
        if current:
            entries.insert(0, current)
        for qe in entries:
            outfile.write('''
        <tr{}>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
        </tr>
'''.format(first_class, qe.name, qe.version, qe.tests and ', '.join(qe.tests) or "all", qe.time.strftime("%H:%M"), qe.attempts))
            first_class = ''
        outfile.write('''
    </tbody>
</table>
</div>
</body>
</html>
''')


GRADED = None   # make sure it's a global variable

OUTFILE = "GRADING_OUTPUTv1"
STOPFILE = Path("STOP_AUTOGRADER")


def scan_dir(svn_dir, version_pat, current=None):
    for version_filename in svn_dir.glob(version_pat):
        tests = []
        with version_filename.open() as version_file:
            try:
                version_line = version_file.readline().strip().split()
                version = int(version_line[0])
                if len(version_line) > 1:
                    tests = version_line[1:]
            except ValueError:
                log.error("Incorrect version format: %s", version_line)
                continue
        name = version_filename.parts[-3]
        # for output_path in (version_filename.parent.glob("{}.*".format(OUTFILE))):
        #     output_name = str(output_path)
        #     dot = output_name.rfind('.')
        #     GRADED[name].add(int(output_name[dot+1:]))
        if current and name == current.name:
            # skip currently graded user
            continue
        if version in GRADED[name]:
            continue
        prev_output = version_filename.parent / "{}.{}".format(OUTFILE, version-1)
        if not tests and prev_output.exists():
            with prev_output.open() as prev_output_file:
                for l in prev_output_file:
                    m = re.search(r"Test ([\w_.]+) Failed", l)
                    if m:
                        tests.append(m.group(1))
        if tests == ["all"]:
            tests = []
        attempts = len(GRADED[name])
        QUEUE.push(QueueEntry(attempts, datetime.now(), version, name,
                              tests, version_filename.parent))

def grade_one():
    try:
        out = check_output(["svn", "update", str(SVN_DIR)], input=b'')
        logging.error("Svn update: %s", out)
    except KeyboardInterrupt:
        logging.info("Terminating, cleaning up svn")
        out = check_call(["svn", "cleanup", str(SVN_DIR)])
        logging.info("Goodbye")
        sys.exit(0)
    except CalledProcessError:
        logging.error("Error during svn update")
    scan_dir(SVN_DIR, VERSION_PAT)
    logging.info("Queue is %s", QUEUE)
    dump_queue()
    if QUEUE:
        qe = QUEUE.pop()
        logging.info("Grading %s version %s tests %s", qe.name, qe.version, ' '.join(qe.tests))
        if "-n" not in sys.argv[1:]:
            p = Popen(["python3", "run_tests.py", str(qe.parent)] + qe.tests,
                      stdout=PIPE)
            while True:
                try:
                    out, _ = p.communicate(timeout=30)
                    break
                except TimeoutExpired:
                    scan_dir(SVN_DIR, VERSION_PAT, qe)
                    dump_queue(current=qe)

            GRADED[qe.name].add(qe.version)
            out_fn = qe.parent / "{}.{}".format(OUTFILE, qe.version)
            if out_fn.exists():
                logging.warning("Warning, overwriting output file %s", out_fn)
            with out_fn.open("wb") as outf:
                outf.write(out)
            if "-q" not in sys.argv[1:]:    # -q: don't commit
                try:
                    check_call(["svn", "add", str(out_fn)])
                    comment = "Autograder output for {} version {}".format(
                        qe.name, qe.version)
                    check_call(["svn", "commit", "-m", comment,
                                str(out_fn)], stdin=DEVNULL)
                except CalledProcessError:
                    logging.error("Error during svn commit of %s", str(out_fn))
    else:
        logging.info("Queue Empty, sleeping")
        time.sleep(30)


if __name__ == "__main__":
    sys.stdin.close()
    logging.basicConfig(format="%(asctime)-15s %(message)s",
                        filename="watch.log", level=logging.INFO)
    if STOPFILE.exists():
        log.info("Deleting old stop file")
        STOPFILE.unlink()
    SVN_DIR = Path(sys.argv[1])
    VERSION_PAT = "*/{}/VERSION".format(sys.argv[2])
    ATTEMPTS_FILE = "attempts.db"
    LOCK_FILE = Path(ATTEMPTS_FILE + ".lock")
    try:
        with LOCK_FILE.open('w') as lock_file:
            log.info("Acquiring shelf lock")
            flock(lock_file.fileno(), LOCK_EX)
            log.info("Shelf lock acquired")
            with shelve.open(ATTEMPTS_FILE, writeback=True) as db:
                if "attempts" not in db:
                    db["attempts"] = defaultdict(set)
                GRADED = db["attempts"]
                while True:
                    grade_one()
                    db['attempts'] = GRADED
                    db.sync()
                    if STOPFILE.exists():
                        break
    finally:
        log.info("Releasing lock")
        LOCK_FILE.unlink()
