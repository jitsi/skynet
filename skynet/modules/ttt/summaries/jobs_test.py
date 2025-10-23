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


class TestMaybeRunNextJob:
    @pytest.mark.asyncio
    async def test_pulls_multiple_jobs_when_capacity_available(self, mocker):
        '''Test that multiple jobs are pulled when there's capacity for multiple.'''
        from skynet.constants import PENDING_JOBS_OPENAI_KEY
        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mock_get_job = mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mock_create_task = mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Create mock jobs
        job_ids = ['job:1:openai', 'job:2:openai', 'job:3:openai']
        mock_jobs = [
            Job(
                id=job_id,
                payload=DocumentPayload(text='test'),
                metadata=DocumentMetadata(customer_id='test'),
                type=JobType.SUMMARY,
            )
            for job_id in job_ids
        ]

        # Mock lpop to return None for OCI queue, then 3 jobs for OPENAI, then None
        openai_job_index = [0]

        def lpop_side_effect(key):
            if key == PENDING_JOBS_OPENAI_KEY:
                if openai_job_index[0] < len(job_ids):
                    job_id = job_ids[openai_job_index[0]]
                    openai_job_index[0] += 1
                    return job_id
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=lpop_side_effect)

        mock_get_job.side_effect = mock_jobs

        # Mock capacity: current_tasks starts empty, max_concurrency is 5
        mocker.patch(
            'skynet.modules.ttt.summaries.jobs.current_tasks',
            {
                Processors.OPENAI: set(),
                Processors.AZURE: set(),
                Processors.OCI: set(),
                Processors.LOCAL: set(),
            },
        )
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 5)

        await maybe_run_next_job()

        # Should have pulled all 3 jobs from OPENAI queue
        assert mock_get_job.call_count == 3
        assert mock_create_task.call_count == 3

    @pytest.mark.asyncio
    async def test_stops_when_capacity_reached(self, mocker):
        '''Test that job pulling stops when processor reaches max concurrency.'''
        import asyncio

        from skynet.constants import PENDING_JOBS_OPENAI_KEY
        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mock_get_job = mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mock_create_task = mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Mock 2 running tasks, max is 3, so should only pull 1 more job
        mock_tasks = {asyncio.create_task(asyncio.sleep(0)), asyncio.create_task(asyncio.sleep(0))}
        mocker.patch(
            'skynet.modules.ttt.summaries.jobs.current_tasks',
            {
                Processors.OPENAI: mock_tasks,
                Processors.AZURE: set(),
                Processors.OCI: set(),
                Processors.LOCAL: set(),
            },
        )
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 3)

        # Mock queue with jobs available - return one job for OPENAI, None for others
        job = Job(
            id='job:1:openai',
            payload=DocumentPayload(text='test'),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        openai_call_count = [0]

        def lpop_side_effect(key):
            if key == PENDING_JOBS_OPENAI_KEY and openai_call_count[0] == 0:
                openai_call_count[0] += 1
                return 'job:1:openai'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=lpop_side_effect)
        mock_get_job.return_value = job

        await maybe_run_next_job()

        # Should only pull 1 job (capacity is 3, currently 2 running)
        assert openai_call_count[0] == 1
        assert mock_create_task.call_count == 1

    @pytest.mark.asyncio
    async def test_processes_multiple_processors(self, mocker):
        '''Test that jobs are pulled from multiple processor queues in priority order.'''
        from skynet.constants import PENDING_JOBS_OCI_KEY, PENDING_JOBS_OPENAI_KEY
        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mock_get_job = mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mock_create_task = mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Create mock jobs for different processors
        oci_job = Job(
            id='job:1:oci',
            payload=DocumentPayload(text='test'),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )
        openai_job = Job(
            id='job:2:openai',
            payload=DocumentPayload(text='test'),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        # Track which queues have been popped
        oci_popped = [False]
        openai_popped = [False]

        def lpop_side_effect(key):
            if key == PENDING_JOBS_OCI_KEY and not oci_popped[0]:
                oci_popped[0] = True
                return 'job:1:oci'
            elif key == PENDING_JOBS_OPENAI_KEY and not openai_popped[0]:
                openai_popped[0] = True
                return 'job:2:openai'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=lpop_side_effect)

        def get_job_side_effect(job_id):
            if job_id == 'job:1:oci':
                return oci_job
            return openai_job

        mock_get_job.side_effect = get_job_side_effect

        # Mock capacity for all processors
        mocker.patch(
            'skynet.modules.ttt.summaries.jobs.current_tasks',
            {
                Processors.OPENAI: set(),
                Processors.AZURE: set(),
                Processors.OCI: set(),
                Processors.LOCAL: set(),
            },
        )
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 5)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_oci', 5)

        await maybe_run_next_job()

        # Should have pulled jobs from both OCI and OPENAI
        assert mock_create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_stops_when_queue_empty(self, mocker):
        '''Test that job pulling stops when queue is empty.'''
        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mock_get_job = mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mock_create_task = mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Mock empty queue (lpop returns None)
        mocker.patch('skynet.modules.ttt.persistence.db.lpop', return_value=None)

        # Mock capacity available
        mocker.patch(
            'skynet.modules.ttt.summaries.jobs.current_tasks',
            {
                Processors.OPENAI: set(),
                Processors.AZURE: set(),
                Processors.OCI: set(),
                Processors.LOCAL: set(),
            },
        )
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 5)

        await maybe_run_next_job()

        # Should not start any jobs
        assert mock_get_job.call_count == 0
        assert mock_create_task.call_count == 0

    @pytest.mark.asyncio
    async def test_skips_processor_without_capacity(self, mocker):
        '''Test that processors without capacity are skipped.'''
        import asyncio

        from skynet.constants import (
            PENDING_JOBS_AZURE_KEY,
            PENDING_JOBS_LOCAL_KEY,
            PENDING_JOBS_OCI_KEY,
            PENDING_JOBS_OPENAI_KEY,
        )
        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        keys_checked = []

        def lpop_side_effect(key):
            keys_checked.append(key)
            return None  # All queues empty

        mock_lpop = mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=lpop_side_effect)

        # OPENAI at capacity, others have capacity
        mock_openai_tasks = {asyncio.create_task(asyncio.sleep(0)) for _ in range(3)}
        mocker.patch(
            'skynet.modules.ttt.summaries.jobs.current_tasks',
            {
                Processors.OPENAI: mock_openai_tasks,
                Processors.AZURE: set(),
                Processors.OCI: set(),
                Processors.LOCAL: set(),
            },
        )
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 3)  # At capacity
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_oci', 5)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_azure', 5)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_local', 5)

        await maybe_run_next_job()

        # Should check OCI, AZURE, and LOCAL queues but NOT OPENAI (since it's at capacity)
        assert PENDING_JOBS_OCI_KEY in keys_checked
        assert PENDING_JOBS_AZURE_KEY in keys_checked
        assert PENDING_JOBS_LOCAL_KEY in keys_checked
        assert PENDING_JOBS_OPENAI_KEY not in keys_checked
