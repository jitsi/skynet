import pytest

from oci.exceptions import TransientServiceError

from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, DocumentPayload, Job, JobType, Processors


@pytest.fixture()
def process_fixture(mocker):
    mocker.patch('skynet.modules.ttt.processor.summarize')
    mocker.patch('skynet.modules.ttt.processor.process_text')
    mocker.patch('skynet.modules.ttt.llm_selector.LLMSelector.select')

    return mocker


@pytest.fixture()
def summarize_fixture(mocker):
    from skynet.modules.ttt.summaries.v1.models import HintType, JobType

    # Mock the prompt dictionary with correct enum keys
    mock_prompts = {JobType.SUMMARY: {HintType.TEXT: 'Default summary prompt for text'}}
    mocker.patch('skynet.modules.ttt.processor.hint_type_to_prompt', mock_prompts)

    # Mock the chain loading function
    mock_chain = mocker.AsyncMock()
    mock_chain.ainvoke = mocker.AsyncMock(return_value={"output_text": "Test result"})
    mocker.patch('skynet.modules.ttt.processor.load_summarize_chain', return_value=mock_chain)

    # Mock customer config utility
    mocker.patch('skynet.modules.ttt.customer_configs.utils.get_existing_customer_config')

    # Mock other dependencies
    mocker.patch('skynet.modules.ttt.processor.set_response_language', return_value='')
    mocker.patch('skynet.modules.ttt.processor.ChatPromptTemplate')

    return mocker


class TestSummarize:
    @pytest.mark.asyncio
    async def test_summarize_uses_payload_prompt_when_provided(self, summarize_fixture):
        """Test that payload.prompt is used when provided."""

        from skynet.modules.ttt.processor import summarize
        from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, JobType

        mock_model = summarize_fixture.Mock()
        mock_model.get_num_tokens.return_value = 100

        payload = DocumentPayload(prompt="Custom user prompt", text="Test text", hint=HintType.TEXT)

        result = await summarize(mock_model, payload, JobType.SUMMARY, "customer123")

        # Verify that get_existing_customer_config was not called since payload.prompt exists
        from skynet.modules.ttt.customer_configs.utils import get_existing_customer_config
        from skynet.modules.ttt.processor import ChatPromptTemplate

        get_existing_customer_config.assert_not_called()

        # Verify ChatPromptTemplate was called with the payload prompt
        ChatPromptTemplate.assert_called_once()
        call_args = ChatPromptTemplate.call_args[0][0]  # Get the first positional argument (the messages list)
        system_message = call_args[1][1]  # Second message should be the system prompt
        assert system_message == "Custom user prompt"

        assert result == "Test result"

    @pytest.mark.asyncio
    async def test_summarize_falls_back_to_default_when_no_payload_prompt_and_no_is_live_summary(
        self, summarize_fixture
    ):
        """Test that default prompt is used when payload.prompt is empty and is_live_summary is not True."""

        from skynet.modules.ttt.customer_configs.utils import get_existing_customer_config
        from skynet.modules.ttt.processor import summarize
        from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, JobType

        mock_model = summarize_fixture.Mock()
        mock_model.get_num_tokens.return_value = 100

        # Mock customer config with custom summary prompt (but it shouldn't be used since is_live_summary is not True)
        get_existing_customer_config.return_value = {'live_summary_prompt': 'Custom customer live summary prompt'}

        payload = DocumentPayload(prompt="", text="Test text", hint=HintType.TEXT)  # Empty prompt, no is_live_summary

        result = await summarize(mock_model, payload, JobType.SUMMARY, "customer123")

        # Verify that get_existing_customer_config was NOT called since is_live_summary is not True
        get_existing_customer_config.assert_not_called()

        # Verify ChatPromptTemplate was called with the default prompt
        from skynet.modules.ttt.processor import ChatPromptTemplate

        ChatPromptTemplate.assert_called_once()
        call_args = ChatPromptTemplate.call_args[0][0]  # Get the first positional argument (the messages list)
        system_message = call_args[1][1]  # Second message should be the system prompt
        assert system_message == "Default summary prompt for text"

        assert result == "Test result"

    @pytest.mark.asyncio
    async def test_summarize_falls_back_to_default_when_no_customer_config(self, summarize_fixture):
        """Test that default prompt is used when no customer config exists but is_live_summary=True."""

        from skynet.modules.ttt.customer_configs.utils import get_existing_customer_config
        from skynet.modules.ttt.processor import summarize
        from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, JobType

        mock_model = summarize_fixture.Mock()
        mock_model.get_num_tokens.return_value = 100

        # Mock no customer config
        get_existing_customer_config.return_value = None

        payload = DocumentPayload(
            prompt="", text="Test text", hint=HintType.TEXT, is_live_summary=True
        )  # Empty prompt, is_live_summary=True

        result = await summarize(mock_model, payload, JobType.SUMMARY, "customer123")

        # Verify that get_existing_customer_config was called
        get_existing_customer_config.assert_called_once_with("customer123")

        # Verify ChatPromptTemplate was called with the default prompt
        from skynet.modules.ttt.processor import ChatPromptTemplate

        ChatPromptTemplate.assert_called_once()
        call_args = ChatPromptTemplate.call_args[0][0]  # Get the first positional argument (the messages list)
        system_message = call_args[1][1]  # Second message should be the system prompt
        assert system_message == "Default summary prompt for text"

        assert result == "Test result"

    @pytest.mark.asyncio
    async def test_summarize_uses_live_summary_prompt_when_is_live_summary_true(self, summarize_fixture):
        """Test that live_summary_prompt is used when is_live_summary=True."""

        from skynet.modules.ttt.customer_configs.utils import get_existing_customer_config
        from skynet.modules.ttt.processor import summarize
        from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType, JobType

        mock_model = summarize_fixture.Mock()
        mock_model.get_num_tokens.return_value = 100

        # Mock customer config with live summary prompt
        get_existing_customer_config.return_value = {'live_summary_prompt': 'Custom live summary prompt'}

        payload = DocumentPayload(prompt="", text="Test text", hint=HintType.TEXT, is_live_summary=True)

        result = await summarize(mock_model, payload, JobType.SUMMARY, "customer123")

        # Verify that get_existing_customer_config was called
        get_existing_customer_config.assert_called_once_with("customer123")

        # Verify ChatPromptTemplate was called with the live summary prompt
        from skynet.modules.ttt.processor import ChatPromptTemplate

        ChatPromptTemplate.assert_called_once()
        call_args = ChatPromptTemplate.call_args[0][0]
        system_message = call_args[1][1]
        assert system_message == "Custom live summary prompt"

        assert result == "Test result"


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
        )

        await process(job)

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
        )

        await process(job)

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
        )

        await process(job)

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
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.OPENAI

        await process(job)

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
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.AZURE

        await process(job)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_local(self, process_fixture):
        '''Test that a job is sent for local inference if there is a customer id configured for it.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'type': 'LOCAL'},
        )
        process_fixture.patch('skynet.modules.ttt.llm_selector.oci_available', True)

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.LOCAL

        await process(job)

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
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.OCI

        await process(job)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_oci_fallback(self, process_fixture):
        '''Test that a job is sent for inference to local if there is a customer id configured for oci but oci is not available.'''

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
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.LOCAL

        await process(job)

        LLMSelector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_oci_error_fallback(self, process_fixture):
        '''Test that a job is sent for inference to oci and retries on local if an error occurs.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'type': 'OCI'},
        )
        process_fixture.patch(
            'skynet.modules.ttt.processor.use_oci', False
        )  # allow fallback to local (when GPU is available)
        process_fixture.patch('skynet.modules.ttt.llm_selector.oci_available', True)
        process_fixture.patch('skynet.modules.ttt.processor.summarize', side_effect=[Exception('error'), None])

        job = Job(
            payload=DocumentPayload(
                text="Andrew: Hello. Beatrix: Honey? It’s me . . . Andrew: Where are you? Beatrix: At the station. I missed my train."
            ),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.OCI

        await process(job)

        assert LLMSelector.get_job_processor(job.metadata.customer_id, job.id) == Processors.LOCAL
        assert LLMSelector.select.call_count == 2

    @pytest.mark.asyncio
    async def test_process_with_transient_service_error_blackout(self, process_fixture):
        '''Test that TransientServiceError triggers blackout and subsequent jobs use LOCAL processor.'''

        from skynet.modules.ttt.llm_selector import LLMSelector
        from skynet.modules.ttt.processor import process

        # Create TransientServiceError with circuit breaker message
        circuit_breaker_msg = (
            'Circuit "test-id" OPEN until 2025-09-04 13:23:43.823175+00:00 (12 failures, 17 sec remaining)'
        )
        transient_error = TransientServiceError(status=429, code='429', headers={}, message=circuit_breaker_msg)

        process_fixture.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value={'type': 'OCI'},
        )
        process_fixture.patch('skynet.modules.ttt.llm_selector.oci_available', True)
        process_fixture.patch('skynet.modules.ttt.processor.use_oci', False)  # allow fallback
        process_fixture.patch('skynet.modules.ttt.processor.summarize', side_effect=[transient_error, None, None])

        job1 = Job(
            payload=DocumentPayload(text="First job"),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        job2 = Job(
            payload=DocumentPayload(text="Second job"),
            metadata=DocumentMetadata(customer_id='test'),
            type=JobType.SUMMARY,
        )

        # First job should trigger TransientServiceError and set blackout
        await process(job1)
        assert LLMSelector.get_job_processor(job1.metadata.customer_id, job1.id) == Processors.LOCAL

        # Second job should immediately go to LOCAL due to active blackout
        await process(job2)
        # Check that blackout causes LOCAL processor selection
        from skynet.modules.ttt.processor import is_oci_blackout_active

        blackout_active = is_oci_blackout_active()
        assert blackout_active == True, "Blackout should be active after TransientServiceError"
        assert (
            LLMSelector.get_job_processor(job2.metadata.customer_id, job2.id, oci_blackout=blackout_active)
            == Processors.LOCAL
        )
