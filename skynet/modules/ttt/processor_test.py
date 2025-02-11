import pytest

from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, DocumentPayload, Job, JobType


@pytest.fixture()
def process_fixture(mocker):
    mocker.patch('skynet.modules.ttt.processor.process_open_ai')
    mocker.patch('skynet.modules.ttt.processor.process_azure')
    mocker.patch('skynet.modules.ttt.processor.process_oci')
    mocker.patch('skynet.modules.ttt.processor.summarize')

    return mocker


class TestProcess:
    @pytest.mark.asyncio
    async def test_process(self, process_fixture):
        '''Test that a job is sent for inference.'''

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

    @pytest.mark.asyncio
    async def test_process_with_open_ai(self, process_fixture):
        '''Test that a job is sent for inference to openai if there is a customer id with a valid api key.'''

        from skynet.modules.ttt.processor import process, process_open_ai

        secret = 'secret'
        model = 'gpt-3.5-turbo'

        process_fixture.patch(
            'skynet.modules.ttt.processor.get_credentials',
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

        await process(job.payload, job.type, job.metadata.customer_id)

        process_open_ai.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_azure_open_ai(self, process_fixture):
        '''Test that a job is sent for inference to azure openai if there is a customer id with a valid api key.'''

        from skynet.modules.ttt.processor import process, process_azure

        secret = 'secret'
        deployment_name = 'gpt-3.5-turbo'
        endpoint = 'https://myopenai.azure.com'

        process_fixture.patch(
            'skynet.modules.ttt.processor.get_credentials',
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

        await process(job.payload, job.type, job.metadata.customer_id)

        process_azure.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_oci(self, process_fixture):
        '''Test that a job is sent for inference to oci if there is a customer id configured for it.'''

        from skynet.modules.ttt.processor import process, process_oci

        process_fixture.patch(
            'skynet.modules.ttt.processor.get_credentials',
            return_value={'type': 'OCI'},
        )

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
            id='job_id',
        )

        await process(job.payload, job.type, job.metadata.customer_id)

        process_oci.assert_called_once()
