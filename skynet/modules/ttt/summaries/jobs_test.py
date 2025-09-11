from typing import Iterator
from unittest.mock import patch

import pytest

from skynet.modules.ttt.persistence import db
from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, DocumentPayload, Job, JobType


@pytest.fixture(scope='module', autouse=True)
def default_session_fixture() -> Iterator[None]:
    with patch('skynet.modules.ttt.persistence.db.set'), patch('skynet.modules.ttt.persistence.db.rpush'), patch(
        'skynet.modules.ttt.persistence.db.llen'
    ):
        yield


class TestCreateJob:
    @pytest.mark.asyncio
    async def test_queues_job(self, mocker):
        '''Test that a job is queued in processor-specific queue and queue size metric is updated.'''

        mocker.patch('skynet.modules.monitoring.SUMMARY_DURATION_METRIC.observe')
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        from skynet.constants import PENDING_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import create_job, update_summary_queue_metric

        job_id = await create_job(JobType.SUMMARY, DocumentPayload(text='test'), DocumentMetadata(customer_id='test'))

        # Job should be queued in LOCAL processor queue since 'test' customer defaults to LOCAL
        db.rpush.assert_called_once_with(PENDING_JOBS_LOCAL_KEY, job_id.id)
        update_summary_queue_metric.assert_called_once()


@pytest.fixture()
def run_job_fixture(mocker):
    mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_DURATION_METRIC.labels')
    mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_FULL_DURATION_METRIC.observe')
    mocker.patch('skynet.modules.ttt.summaries.jobs.update_job')
    mocker.patch('skynet.modules.ttt.summaries.jobs.process')
    mocker.patch('skynet.modules.ttt.summaries.jobs.db.db')

    return mocker


class TestRunJob:
    @pytest.mark.asyncio
    async def test_run_job(self, run_job_fixture):
        '''Test that a job is sent for inference.'''

        from skynet.modules.ttt.summaries.jobs import process, run_job

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id=None),
            type=JobType.SUMMARY,
            id='job_id',
        )

        await run_job(job)

        process.assert_called_once()


class TestCanRunNextJob:
    def test_returns_true_if_executor_enabled(self, mocker):
        '''Test that it returns true if executor module is enabled and processor has capacity.'''

        from skynet.modules.ttt.summaries.jobs import can_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.current_tasks', {Processors.LOCAL: set()})

        assert can_run_next_job(Processors.LOCAL)

    def test_returns_false_if_executor_enabled(self, mocker):
        '''Test that it returns false if executor module is not enabled.'''

        from skynet.modules.ttt.summaries.jobs import can_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:dispatcher'})

        assert not can_run_next_job(Processors.LOCAL)


class TestRestoreStaleJobs:
    @pytest.mark.asyncio
    async def test_restore_stales_jobs(self, mocker):
        '''Test that if there are stale jobs, they will be restored to processor-specific queues.'''

        from skynet.constants import PENDING_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import restore_stale_jobs

        job_1 = Job(
            id='job_id_1',
            payload=DocumentPayload(text='some text'),
            type='summary',
            worker_id=1,
            metadata=DocumentMetadata(customer_id='test'),
        )
        job_2 = Job(
            id='job_id_2',
            payload=DocumentPayload(text='some text'),
            type='summary',
            worker_id=2,
            metadata=DocumentMetadata(customer_id='test'),
        )
        job_3 = Job(
            id='job_id_3',
            payload=DocumentPayload(text='some text'),
            type='summary',
            worker_id=2,
            metadata=DocumentMetadata(customer_id='test'),
        )
        job_1_json = Job.model_dump_json(job_1)
        job_2_json = Job.model_dump_json(job_2)
        job_3_json = Job.model_dump_json(job_3)

        client_list = [
            {'id': '1'}
        ]  # only one worker connected, any jobs that were running on worker 2 should be restored (jobs 2 and 3 in this case)

        def mock_lrange(key, start, end):
            # Only return running jobs for LOCAL processor queue to avoid duplicates
            if 'local' in key:
                return [job_1.id, job_2.id, job_3.id]
            return []

        def mock_mget(keys):
            if not keys:
                return []
            return [job_1_json, job_2_json, job_3_json]

        mocker.patch('skynet.modules.ttt.persistence.db.lrange', side_effect=mock_lrange)
        mocker.patch('skynet.modules.ttt.persistence.db.mget', side_effect=mock_mget)
        mocker.patch('skynet.modules.ttt.persistence.db.lpush')
        mocker.patch('skynet.modules.ttt.persistence.db.client_list', return_value=client_list)

        await restore_stale_jobs()

        # Should restore stale jobs (job_2 and job_3) to LOCAL queue
        assert db.lpush.call_count == 2
        db.lpush.assert_any_call(PENDING_JOBS_LOCAL_KEY, job_2.id)
        db.lpush.assert_any_call(PENDING_JOBS_LOCAL_KEY, job_3.id)
