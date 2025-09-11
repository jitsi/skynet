from typing import Iterator
from unittest.mock import Mock, patch

import pytest

from skynet.modules.ttt.persistence import db
from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, DocumentPayload, Job, JobType


@pytest.fixture(autouse=True)
def reset_db_mocks():
    """Reset all database mocks before each test"""
    if hasattr(db, 'rpush'):
        db.rpush.reset_mock()
    if hasattr(db, 'lpush'):
        db.lpush.reset_mock()
    if hasattr(db, 'lrem'):
        db.lrem.reset_mock()
    yield


@pytest.fixture(scope='module', autouse=True)
def default_session_fixture() -> Iterator[None]:
    with patch('skynet.modules.ttt.persistence.db.set'), patch('skynet.modules.ttt.persistence.db.rpush'), patch(
        'skynet.modules.ttt.persistence.db.llen'
    ), patch('skynet.modules.ttt.persistence.db.lpush'), patch('skynet.modules.ttt.persistence.db.lrem'):
        yield


class TestProcessorSpecificQueues:
    @pytest.mark.asyncio
    async def test_create_job_routes_to_openai_queue(self, mocker):
        '''Test that jobs are routed to OpenAI processor queue when customer uses OpenAI.'''

        from skynet.constants import PENDING_JOBS_OPENAI_KEY
        from skynet.modules.ttt.summaries.jobs import create_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.OPENAI)

        job_id = await create_job(
            JobType.SUMMARY, DocumentPayload(text='test'), DocumentMetadata(customer_id='openai_customer')
        )

        db.rpush.assert_called_once_with(PENDING_JOBS_OPENAI_KEY, job_id.id)

    @pytest.mark.asyncio
    async def test_create_job_routes_to_azure_queue(self, mocker):
        '''Test that jobs are routed to Azure processor queue when customer uses Azure.'''

        from skynet.constants import PENDING_JOBS_AZURE_KEY
        from skynet.modules.ttt.summaries.jobs import create_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.AZURE)

        job_id = await create_job(
            JobType.SUMMARY, DocumentPayload(text='test'), DocumentMetadata(customer_id='azure_customer')
        )

        db.rpush.assert_called_once_with(PENDING_JOBS_AZURE_KEY, job_id.id)

    @pytest.mark.asyncio
    async def test_create_job_routes_to_oci_queue(self, mocker):
        '''Test that jobs are routed to OCI processor queue when customer uses OCI.'''

        from skynet.constants import PENDING_JOBS_OCI_KEY
        from skynet.modules.ttt.summaries.jobs import create_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.OCI)

        job_id = await create_job(
            JobType.SUMMARY, DocumentPayload(text='test'), DocumentMetadata(customer_id='oci_customer')
        )

        db.rpush.assert_called_once_with(PENDING_JOBS_OCI_KEY, job_id.id)

    @pytest.mark.asyncio
    async def test_high_priority_jobs_use_lpush(self, mocker):
        '''Test that high priority jobs are added to front of processor queue.'''

        from skynet.constants import PENDING_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import create_job
        from skynet.modules.ttt.summaries.v1.models import Priority, Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.LOCAL)

        high_priority_payload = DocumentPayload(text='urgent', priority=Priority.HIGH)
        job_id = await create_job(JobType.SUMMARY, high_priority_payload, DocumentMetadata(customer_id='test'))

        db.lpush.assert_called_once_with(PENDING_JOBS_LOCAL_KEY, job_id.id)


class TestProcessorConcurrencyLimits:
    def test_can_run_next_job_respects_processor_limits(self, mocker):
        '''Test that concurrency limits are enforced per processor.'''

        from skynet.modules.ttt.summaries.jobs import can_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.modules', {'summaries:executor'})
        mocker.patch('skynet.modules.ttt.summaries.jobs.get_processor_max_concurrency', return_value=2)

        # Mock current tasks - 1 task running for OPENAI
        mock_task = Mock()
        mock_tasks = {
            Processors.OPENAI: {mock_task},  # 1 task
            Processors.AZURE: set(),
            Processors.OCI: set(),
            Processors.LOCAL: set(),
        }
        mocker.patch('skynet.modules.ttt.summaries.jobs.current_tasks', mock_tasks)

        # Should allow more jobs for OPENAI (1 < 2)
        assert can_run_next_job(Processors.OPENAI)

        # Add another task to reach limit
        mock_tasks[Processors.OPENAI].add(Mock())

        # Should not allow more jobs for OPENAI (2 >= 2)
        assert not can_run_next_job(Processors.OPENAI)

        # Should still allow jobs for other processors
        assert can_run_next_job(Processors.AZURE)
        assert can_run_next_job(Processors.LOCAL)

    def test_get_processor_max_concurrency_returns_correct_limits(self, mocker):
        '''Test that max concurrency values are returned correctly for each processor.'''

        from skynet.modules.ttt.summaries.jobs import get_processor_max_concurrency
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_openai', 10)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_azure', 8)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_oci', 5)
        mocker.patch('skynet.modules.ttt.summaries.jobs.max_concurrency_local', 2)

        assert get_processor_max_concurrency(Processors.OPENAI) == 10
        assert get_processor_max_concurrency(Processors.AZURE) == 8
        assert get_processor_max_concurrency(Processors.OCI) == 5
        assert get_processor_max_concurrency(Processors.LOCAL) == 2


class TestProcessorQueueSelection:
    @pytest.mark.asyncio
    async def test_maybe_run_next_job_follows_priority_order(self, mocker):
        '''Test that processors are checked in the defined priority order.'''

        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job

        mocker.patch('skynet.modules.ttt.summaries.jobs.can_run_next_job', return_value=True)
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')
        mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Mock lpop to return job only for OCI queue (first in priority)
        def mock_lpop(key):
            if 'oci' in key:
                return 'test_job_id:OCI'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=mock_lpop)

        await maybe_run_next_job()

        # Should check OCI first (highest priority) and find job there
        db.lpop.assert_any_call('jobs:pending:oci')

    @pytest.mark.asyncio
    async def test_maybe_run_next_job_skips_processors_at_capacity(self, mocker):
        '''Test that processors at capacity are skipped.'''

        from skynet.modules.ttt.summaries.jobs import maybe_run_next_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        def mock_can_run(processor):
            # OCI and OPENAI are at capacity, AZURE has capacity
            return processor == Processors.AZURE

        mocker.patch('skynet.modules.ttt.summaries.jobs.can_run_next_job', side_effect=mock_can_run)
        mocker.patch('skynet.modules.ttt.summaries.jobs.get_job')
        mocker.patch('skynet.modules.ttt.summaries.jobs.create_run_job_task')

        # Mock lpop to return job for AZURE queue
        def mock_lpop(key):
            if 'azure' in key:
                return 'test_job_id:AZURE'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=mock_lpop)

        await maybe_run_next_job()

        # Should skip OCI and OPENAI, go to AZURE
        db.lpop.assert_any_call('jobs:pending:azure')


class TestProcessorHelperFunctions:
    def test_get_processor_queue_keys_returns_correct_keys(self):
        '''Test that correct queue keys are returned for each processor.'''

        from skynet.constants import (
            ERROR_JOBS_AZURE_KEY,
            ERROR_JOBS_LOCAL_KEY,
            ERROR_JOBS_OCI_KEY,
            ERROR_JOBS_OPENAI_KEY,
            PENDING_JOBS_AZURE_KEY,
            PENDING_JOBS_LOCAL_KEY,
            PENDING_JOBS_OCI_KEY,
            PENDING_JOBS_OPENAI_KEY,
            RUNNING_JOBS_AZURE_KEY,
            RUNNING_JOBS_LOCAL_KEY,
            RUNNING_JOBS_OCI_KEY,
            RUNNING_JOBS_OPENAI_KEY,
        )
        from skynet.modules.ttt.summaries.jobs import get_processor_queue_keys
        from skynet.modules.ttt.summaries.v1.models import Processors

        assert get_processor_queue_keys(Processors.OPENAI) == (
            PENDING_JOBS_OPENAI_KEY,
            RUNNING_JOBS_OPENAI_KEY,
            ERROR_JOBS_OPENAI_KEY,
        )
        assert get_processor_queue_keys(Processors.AZURE) == (
            PENDING_JOBS_AZURE_KEY,
            RUNNING_JOBS_AZURE_KEY,
            ERROR_JOBS_AZURE_KEY,
        )
        assert get_processor_queue_keys(Processors.OCI) == (
            PENDING_JOBS_OCI_KEY,
            RUNNING_JOBS_OCI_KEY,
            ERROR_JOBS_OCI_KEY,
        )
        assert get_processor_queue_keys(Processors.LOCAL) == (
            PENDING_JOBS_LOCAL_KEY,
            RUNNING_JOBS_LOCAL_KEY,
            ERROR_JOBS_LOCAL_KEY,
        )

    def test_get_all_processor_queue_keys_returns_all_processors(self):
        '''Test that all processor queue keys are returned.'''

        from skynet.modules.ttt.summaries.jobs import get_all_processor_queue_keys
        from skynet.modules.ttt.summaries.v1.models import Processors

        all_keys = get_all_processor_queue_keys()

        assert len(all_keys) == 4
        assert Processors.OPENAI in all_keys
        assert Processors.AZURE in all_keys
        assert Processors.OCI in all_keys
        assert Processors.LOCAL in all_keys


class TestTaskTrackingPerProcessor:
    @pytest.mark.asyncio
    async def test_create_run_job_task_adds_to_correct_processor_set(self, mocker):
        '''Test that tasks are tracked in the correct processor-specific set.'''

        from skynet.modules.ttt.summaries.jobs import create_run_job_task
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock the run_job function to return immediately
        async def mock_run_job(job):
            return "completed"

        mocker.patch('skynet.modules.ttt.summaries.jobs.run_job', side_effect=mock_run_job)

        # Create a job with OPENAI processor in ID
        job = Job(
            id='test_job_id:OPENAI',
            payload=DocumentPayload(text='test'),
            type=JobType.SUMMARY,
            metadata=DocumentMetadata(customer_id='test'),
        )

        # Mock the current_tasks to avoid modifying the real one
        mock_tasks = {
            Processors.OPENAI: set(),
            Processors.AZURE: set(),
            Processors.OCI: set(),
            Processors.LOCAL: set(),
        }
        mocker.patch('skynet.modules.ttt.summaries.jobs.current_tasks', mock_tasks)

        task = create_run_job_task(job)

        # Should be added to OPENAI processor set
        assert len(mock_tasks[Processors.OPENAI]) == 1
        assert task in mock_tasks[Processors.OPENAI]

        # Should not be in other processor sets
        assert len(mock_tasks[Processors.AZURE]) == 0
        assert len(mock_tasks[Processors.OCI]) == 0
        assert len(mock_tasks[Processors.LOCAL]) == 0

        # Wait for task to complete and be removed
        await task

        # Should be removed from OPENAI processor set after completion
        assert len(mock_tasks[Processors.OPENAI]) == 0


class TestProcessorSpecificRunningQueues:
    @pytest.mark.asyncio
    async def test_update_done_job_uses_processor_specific_error_queue(self, mocker):
        '''Test that failed LOCAL jobs are added to processor-specific error queues (since non-LOCAL jobs expire).'''

        from skynet.constants import ERROR_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import update_done_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock all the dependencies
        mock_update_job = mocker.patch('skynet.modules.ttt.summaries.jobs.update_job')
        mock_update_job.return_value = Mock(
            metadata=Mock(customer_id='test'),
            computed_duration=5.0,
            computed_full_duration=10.0,
            payload=Mock(text='test text'),
            id='test_job_id',
        )

        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_DURATION_METRIC')
        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_FULL_DURATION_METRIC')
        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_INPUT_LENGTH_METRIC')
        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_ERROR_COUNTER')

        job = Mock()
        job.id = 'test_job_id'

        # Use LOCAL processor since failed LOCAL jobs don't expire and go to error queue
        await update_done_job(job, "Error occurred", Processors.LOCAL, has_failed=True)

        # Should add to LOCAL-specific error queue
        db.rpush.assert_called_with(ERROR_JOBS_LOCAL_KEY, job.id)

    @pytest.mark.asyncio
    async def test_update_done_job_removes_from_processor_specific_running_queue(self, mocker):
        '''Test that completed jobs are removed from processor-specific running queues.'''

        from skynet.constants import RUNNING_JOBS_AZURE_KEY
        from skynet.modules.ttt.summaries.jobs import update_done_job
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock all the dependencies
        mock_update_job = mocker.patch('skynet.modules.ttt.summaries.jobs.update_job')
        mock_update_job.return_value = Mock(
            metadata=Mock(customer_id='test'),
            computed_duration=5.0,
            computed_full_duration=10.0,
            payload=Mock(text='test text'),
            id='test_job_id',
        )

        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_DURATION_METRIC')
        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_FULL_DURATION_METRIC')
        mocker.patch('skynet.modules.ttt.summaries.jobs.SUMMARY_INPUT_LENGTH_METRIC')

        job = Mock()
        job.id = 'test_job_id'

        await update_done_job(job, "Success", Processors.AZURE, has_failed=False)

        # Should remove from AZURE-specific running queue
        db.lrem.assert_called_with(RUNNING_JOBS_AZURE_KEY, 0, job.id)


class TestLegacyQueueMigration:
    @pytest.mark.asyncio
    async def test_migrate_legacy_queues_moves_pending_jobs(self, mocker):
        '''Test that pending jobs are migrated from legacy queue to processor-specific queues.'''

        from skynet.constants import PENDING_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import migrate_legacy_queues
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock job data
        job = Job(
            id='test_job_id',
            payload=DocumentPayload(text='test'),
            type=JobType.SUMMARY,
            metadata=DocumentMetadata(customer_id='test'),
        )
        job_json = Job.model_dump_json(job)

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.LOCAL)
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        # Mock database operations
        def mock_lpop(key):
            if key == 'jobs:pending' and not hasattr(mock_lpop, 'called'):
                mock_lpop.called = True
                return 'test_job_id'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=mock_lpop)
        mocker.patch('skynet.modules.ttt.persistence.db.get', return_value=job_json)
        mocker.patch('skynet.modules.ttt.persistence.db.rpush')
        mocker.patch('skynet.modules.ttt.persistence.db.lrange', return_value=[])

        await migrate_legacy_queues()

        # Should move job from legacy pending to LOCAL processor pending queue
        db.rpush.assert_called_with(PENDING_JOBS_LOCAL_KEY, 'test_job_id')

    @pytest.mark.asyncio
    async def test_migrate_legacy_queues_preserves_high_priority(self, mocker):
        '''Test that high priority jobs are migrated to front of processor queues.'''

        from skynet.constants import PENDING_JOBS_LOCAL_KEY
        from skynet.modules.ttt.summaries.jobs import migrate_legacy_queues
        from skynet.modules.ttt.summaries.v1.models import Priority, Processors

        # Mock high priority job
        job = Job(
            id='high_priority_job',
            payload=DocumentPayload(text='urgent', priority=Priority.HIGH),
            type=JobType.SUMMARY,
            metadata=DocumentMetadata(customer_id='test'),
        )
        job_json = Job.model_dump_json(job)

        # Mock dependencies
        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', return_value=Processors.LOCAL)
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        # Mock database operations
        def mock_lpop(key):
            if key == 'jobs:pending' and not hasattr(mock_lpop, 'called'):
                mock_lpop.called = True
                return 'high_priority_job'
            return None

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=mock_lpop)
        mocker.patch('skynet.modules.ttt.persistence.db.get', return_value=job_json)
        mocker.patch('skynet.modules.ttt.persistence.db.lpush')
        mocker.patch('skynet.modules.ttt.persistence.db.lrange', return_value=[])

        await migrate_legacy_queues()

        # High priority job should use lpush (add to front)
        db.lpush.assert_called_with(PENDING_JOBS_LOCAL_KEY, 'high_priority_job')

    @pytest.mark.asyncio
    async def test_migrate_legacy_queues_handles_different_processors(self, mocker):
        '''Test that jobs are routed to correct processor-specific queues based on customer.'''

        from skynet.constants import PENDING_JOBS_AZURE_KEY, PENDING_JOBS_OPENAI_KEY
        from skynet.modules.ttt.summaries.jobs import migrate_legacy_queues
        from skynet.modules.ttt.summaries.v1.models import Processors

        # Mock jobs for different processors
        openai_job = Job(
            id='openai_job',
            payload=DocumentPayload(text='test'),
            type=JobType.SUMMARY,
            metadata=DocumentMetadata(customer_id='openai_customer'),
        )
        azure_job = Job(
            id='azure_job',
            payload=DocumentPayload(text='test'),
            type=JobType.SUMMARY,
            metadata=DocumentMetadata(customer_id='azure_customer'),
        )

        jobs_data = {
            'openai_job': Job.model_dump_json(openai_job),
            'azure_job': Job.model_dump_json(azure_job),
        }

        # Mock processor selection
        def mock_get_processor(customer_id, job_id=None):
            if 'openai' in customer_id:
                return Processors.OPENAI
            elif 'azure' in customer_id:
                return Processors.AZURE
            return Processors.LOCAL

        mocker.patch('skynet.modules.ttt.summaries.jobs.LLMSelector.get_job_processor', side_effect=mock_get_processor)
        mocker.patch('skynet.modules.ttt.summaries.jobs.update_summary_queue_metric')

        # Mock database operations
        job_queue = ['openai_job', 'azure_job']

        def mock_lpop(key):
            if key == 'jobs:pending' and job_queue:
                return job_queue.pop(0)
            return None

        def mock_get(job_id):
            return jobs_data.get(job_id)

        mocker.patch('skynet.modules.ttt.persistence.db.lpop', side_effect=mock_lpop)
        mocker.patch('skynet.modules.ttt.persistence.db.get', side_effect=mock_get)
        mocker.patch('skynet.modules.ttt.persistence.db.rpush')
        mocker.patch('skynet.modules.ttt.persistence.db.lrange', return_value=[])

        await migrate_legacy_queues()

        # Should route jobs to correct processor queues
        db.rpush.assert_any_call(PENDING_JOBS_OPENAI_KEY, 'openai_job')
        db.rpush.assert_any_call(PENDING_JOBS_AZURE_KEY, 'azure_job')
