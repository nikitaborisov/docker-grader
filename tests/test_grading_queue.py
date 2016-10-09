from dockergrader.watch import GradingQueue, QueueEntry

def test_queue_entry_sort():
    # time is the sort of last resort
    assert QueueEntry(attempts=0, time=0, version=0, name='foo', tests=[],
        parent=None) < QueueEntry(attempts=0, time=10, version=0, name='bar',
        tests=[], parent=None)

    # attempts trumps time
    assert QueueEntry(attempts=0, time=10, version=0, name='foo', tests=[],
        parent=None) < QueueEntry(attempts=1, time=0, version=0, name='bar',
        tests=[], parent=None)


    # short tests are better than all tests
    qe1 = QueueEntry(attempts=1, time=0, version=0, name='foo', tests=['one'],
        parent=None)
    qe2 = QueueEntry(attempts=0, time=0, version=0, name='bar',
        tests=[], parent=None)
    assert qe1._adj_attempts < qe2._adj_attempts
    assert qe1 != qe2
    assert qe1 < qe2

    # short tests are better than a lot of tests
    assert QueueEntry(attempts=0, time=0, version=0, name='foo', tests=['one'],
        parent=None) < QueueEntry(attempts=0, time=0, version=0, name='bar',
        tests=['a','b','c','d'], parent=None)

    assert qe1 != None
    assert "asdf" != qe2
