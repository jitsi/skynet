from typing import Iterator
from unittest.mock import patch

import pytest

from skynet.modules.ttt.summaries.persistence import db
from skynet.modules.ttt.summaries.v1.models import DocumentPayload, Job, JobType


@pytest.fixture(scope='module', autouse=True)
def default_session_fixture() -> Iterator[None]:
    with patch('skynet.modules.ttt.summaries.persistence.db.set'), patch(
        'skynet.modules.ttt.summaries.persistence.db.rpush'
    ), patch('skynet.modules.ttt.summaries.persistence.db.llen'):
        yield


class TestCreateJob:
    @pytest.mark.asyncio
    async def test_creates_run_job(self, mocker):
        '''Test that a job run task is created.'''

        mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        from skynet.modules.ttt.summaries.jobs import create_job, create_run_job_task

        job_id = await create_job(JobType.SUMMARY, DocumentPayload(text='test'))

        create_run_job_task.assert_called_once()
        assert job_id.id is not None

    @pytest.mark.asyncio
    async def test_queues_job(self, mocker):
        '''Test that a job is queued and queue size metric is updated.'''

        mocker.patch('skynet.modules.monitoring.SUMMARY_DURATION_METRIC.observe')
        mocker.patch('skynet.modules.ttt.summaries.jobs.can_run_next_job', return_value=False)
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        from skynet.modules.ttt.summaries.jobs import create_job, PENDING_JOBS_KEY, update_summary_queue_metric

        job_id = await create_job(JobType.SUMMARY, DocumentPayload(text='test'))

        db.rpush.assert_called_once_with(PENDING_JOBS_KEY, job_id.id)
        update_summary_queue_metric.assert_called_once()


@pytest.fixture()
def run_job_fixture(mocker):
    mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_DURATION_METRIC.observe')
    mocker.patch('skynet.modules.ttt.summaries.jobs.update_job')
    mocker.patch('skynet.modules.ttt.summaries.jobs.process')
    mocker.patch('skynet.modules.ttt.summaries.jobs.db.db')

    yield 'run_job_fixture'


class TestRunJob:
    @pytest.mark.asyncio
    async def test_does_not_run_job(self, run_job_fixture):
        '''Test that a job with a short payload is not sent for inference.'''

        from skynet.modules.ttt.summaries.jobs import process, run_job

        await run_job(
            Job(payload=DocumentPayload(text="Hello. It’s me . . . Where are you?"), type=JobType.SUMMARY, id='job_id')
        )

        process.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_job(self, run_job_fixture):
        '''Test that a job with a long enough payload is sent for inference.'''

        from skynet.modules.ttt.summaries.jobs import process, run_job

        await run_job(
            Job(
                payload=DocumentPayload(
                    text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
                ),
                type=JobType.SUMMARY,
                id='job_id',
            )
        )

        process.assert_called_once()


class TestCanRunNextJob:
    def test_returns_true_if_executor_enabled(self, mocker):
        '''Test that it returns true if executor module is enabled.'''

        from skynet.modules.ttt.summaries.jobs import can_run_next_job

        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})

        assert can_run_next_job()

    def test_returns_false_if_executor_enabled(self, mocker):
        '''Test that it returns false if executor module is not enabled.'''

        from skynet.modules.ttt.summaries.jobs import can_run_next_job

        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:dispatcher'})

        assert not can_run_next_job()


class TestRestoreStaleJobs:
    @pytest.mark.asyncio
    async def test_restore_stales_jobs(self, mocker):
        '''Test that if there are stale jobs, they will be restored. A job is considered stale if it is running and the worker is no longer connected.'''

        from skynet.modules.ttt.summaries.jobs import PENDING_JOBS_KEY, restore_stale_jobs

        job_1 = Job(id='job_id_1', payload=DocumentPayload(text='some text'), type='summary', worker_id=1)
        job_2 = Job(id='job_id_2', payload=DocumentPayload(text='some text'), type='summary', worker_id=2)
        job_3 = Job(id='job_id_3', payload=DocumentPayload(text='some text'), type='summary', worker_id=2)
        job_1_json = Job.model_dump_json(job_1)
        job_2_json = Job.model_dump_json(job_2)
        job_3_json = Job.model_dump_json(job_3)

        running_jobs = [job_1_json, job_2_json, job_3_json]
        client_list = [
            {'id': '1'}
        ]  # only one worker connected, any jobs that were running on worker 2 should be restored (jobs 2 and 3 in this case)

        mocker.patch('skynet.modules.ttt.summaries.persistence.db.lrange')
        mocker.patch('skynet.modules.ttt.summaries.persistence.db.mget', return_value=running_jobs)
        mocker.patch('skynet.modules.ttt.summaries.persistence.db.lpush')
        mocker.patch('skynet.modules.ttt.summaries.persistence.db.client_list', return_value=client_list)

        await restore_stale_jobs()

        db.lpush.assert_called_once_with(PENDING_JOBS_KEY, job_2.id, job_3.id)
