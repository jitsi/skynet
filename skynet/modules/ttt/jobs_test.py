from typing import Iterator
import pytest

from unittest.mock import patch
from skynet.logs import get_logger

from skynet.models.v1.document import DocumentPayload
from skynet.models.v1.job import JobType
from skynet.modules.persistence import db
from skynet.modules.ttt.jobs import PENDING_JOBS_KEY

log = get_logger('skynet.jobs_test')


@pytest.fixture(scope='module', autouse=True)
def default_session_fixture() -> Iterator[None]:
    with patch('skynet.modules.persistence.db.set'), patch('skynet.modules.persistence.db.rpush'):
        yield


class TestCreateJob:
    @pytest.mark.asyncio
    async def test_runs_job(self, mocker):
        '''Test that a job is run.'''

        mocker.patch('skynet.modules.ttt.jobs.create_run_job_task'),

        from skynet.modules.ttt.jobs import create_job, create_run_job_task

        job_id = await create_job(JobType.SUMMARY, DocumentPayload(text='test'))

        create_run_job_task.assert_called_once()
        assert job_id.id is not None

    @pytest.mark.asyncio
    async def test_queues_job(self, mocker):
        '''Test that a job is queued and queue size metric is updated.'''

        mocker.patch('skynet.modules.ttt.jobs.can_run_next_job', return_value=False)
        mocker.patch('skynet.modules.ttt.jobs.update_summary_queue_metric')

        from skynet.modules.ttt.jobs import create_job, update_summary_queue_metric

        job_id = await create_job(JobType.SUMMARY, DocumentPayload(text='test'))

        db.rpush.assert_called_once_with(PENDING_JOBS_KEY, job_id.id)
        update_summary_queue_metric.assert_called_once()
