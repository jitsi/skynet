import pytest

from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, DocumentPayload, Job, JobType, Processors


@pytest.fixture()
def process_fixture(mocker):
    mocker.patch('skynet.modules.ttt.processor.summarize')
    mocker.patch('skynet.modules.ttt.processor.process_text')
    mocker.patch('skynet.modules.ttt.llm_selector.LLMSelector.select')

    return mocker


class TestProcess:
    @pytest.mark.asyncio
    async def test_process_action_items(self, process_fixture):
        '''Test that an action items job is sent for inference.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process, summarize

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id=None),
            type=JobType.ACTION_ITEMS,
            id='job_id',
        )

        await process(job.payload, job.type, job.metadata.customer_id)

        summarize.assert_called_once()
        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_summary(self, process_fixture):
        '''Test that a summary job is sent for inference.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process, summarize

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id=None),
            type=JobType.SUMMARY,
            id='job_id',
        )

        await process(job.payload, job.type, job.metadata.customer_id)

        summarize.assert_called_once()
        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_process_text(self, process_fixture):
        '''Test that a process-text job is sent for inference.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process, process_text

        job = Job(
            payload=DocumentPayload(
                prompt='Rewrite the following text in middle English',
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train.",
            ),
            metadata=DocumentMetadata(customer_id=None),
            type=JobType.PROCESS_TEXT,
            id='job_id',
        )

        await process(job.payload, job.type, job.metadata.customer_id)

        process_text.assert_called_once()
        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_open_ai(self, process_fixture):
        '''Test that a job is sent for inference to openai if there is a customer id with a valid api key.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        secret = 'secret'
        model = 'gpt-3.5-turbo'

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'secret': secret, 'type': 'OPENAI', 'metadata': {'model': model}},
        )

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
            id='job_id',
        )

        assert LLMSelector.get_job_processor('test') == Processors.OPENAI

        await process(job.payload, job.type, job.metadata.customer_id)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_azure_open_ai(self, process_fixture):
        '''Test that a job is sent for inference to azure openai if there is a customer id with a valid api key.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        secret = 'secret'
        deployment_name = 'gpt-3.5-turbo'
        endpoint = 'https://myopenai.azure.com'

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={
                'secret': secret,
                'type': 'AZURE_OPENAI',
                'metadata': {'deploymentName': deployment_name, 'endpoint': endpoint},
            },
        )

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
            id='job_id',
        )

        assert LLMSelector.get_job_processor('test') == Processors.AZURE

        await process(job.payload, job.type, job.metadata.customer_id)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_oci(self, process_fixture):
        '''Test that a job is sent for inference to oci if there is a customer id configured for it.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'type': 'OCI'},
        )
        process_fixture.patch('skynet.modules.ttt.llm_selector.oci_available', True)

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
            id='job_id',
        )

        assert LLMSelector.get_job_processor('test') == Processors.OCI

        await process(job.payload, job.type, job.metadata.customer_id)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_oci_fallback(self, process_fixture):
        '''Test that a job is sent for inference to oci if there is a customer id configured for it.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'type': 'OCI'},
        )
        process_fixture.patch('skynet.modules.ttt.llm_selector.oci_available', False)

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
            id='job_id',
        )

        assert LLMSelector.get_job_processor('test') == Processors.LOCAL

        await process(job.payload, job.type, job.metadata.customer_id)

        LLMSelector.select.assert_called_once()
