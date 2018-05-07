from __future__ import absolute_import
from multiprocessing import Process
import os
import signal
from time import sleep

from celery import Celery
from celery.signals import worker_process_shutdown
from kombu.exceptions import OperationalError
import pytest

from .. import EternalTask, EternalProcessTask

# Celery application object.
# Use redis backend, because it supports locks (and thus singleton tasks).
app = Celery(__name__, broker='redis://')
app.conf['result_backend'] = app.conf.broker_url

# Only run these tests if a Redis server is running.
try:
    app.connection().ensure_connection(max_retries=1)
except OperationalError:
    pytestmark = pytest.mark.skip('No Redis server is running.')


def touch(path):
    """Touch a file."""
    with open(path, 'w'):
        pass


@app.task(base=EternalTask, bind=True, shared=False)
def example_task_aborts_gracefully(self):
    while not self.is_aborted():
        sleep(0.1)
        touch(os.path.join(os.environ['COV_TMP'], 'aborts_gracefully'))


@app.task(base=EternalTask, shared=False)
def example_task_always_succeeds():
    sleep(0.1)
    touch(os.path.join(os.environ['COV_TMP'], 'always_succeeds'))


@app.task(base=EternalTask, shared=False)
def example_task_always_fails():
    sleep(0.1)
    touch(os.path.join(os.environ['COV_TMP'], 'always_fails'))
    raise RuntimeError('Expected to fail!')


@app.task(base=EternalProcessTask, shared=False)
def example_task_never_returns():
    while True:
        touch(os.path.join(os.environ['COV_TMP'], 'never_returns'))
        sleep(1)


@app.task(base=EternalProcessTask, shared=False)
def example_task_ignores_sigint():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    while True:
        touch(os.path.join(os.environ['COV_TMP'], 'ignores_sigint'))
        sleep(1)


# Only needed if we are measuring test coverage
try:
    from pytest_cov.embed import multiprocessing_finish
except ImportError:
    pass
else:
    @worker_process_shutdown.connect
    def on_worker_process_shutdown(*args, **kwargs):
        multiprocessing_finish()


@pytest.fixture
def start_test_app_worker(tmpdir):
    """Start up a worker for the test app."""
    os.environ['COV_TMP'] = str(tmpdir)
    argv = ['worker', '-B', '-c', '5', '-l', 'info',
            '-s', str(tmpdir / 'celerybeat-schedule')]
    p = Process(target=app.worker_main, args=(argv,))
    p.daemon = True
    p.start()
    yield
    p.terminate()
    p.join()
    app.control.purge()
    del os.environ['COV_TMP']


def test_eternal(start_test_app_worker, tmpdir):
    """Test worker with two eternal tasks: one that always succeeds,
    and one that always fails."""
    filenames = ['aborts_gracefully',
                 'always_succeeds',
                 'always_fails',
                 'never_returns',
                 'ignores_sigint']
    for i in range(100):
        finished = all(os.path.exists(str(tmpdir / _)) for _ in filenames)
        if finished:
            break
        sleep(0.1)
    assert finished
