import pytest

from oci.exceptions import TransientServiceError

from skynet.modules.ttt.oci import utils


@pytest.fixture(autouse=True)
def reset_state(mocker):
    utils._disabled_reason = None
    mocker.patch('skynet.modules.ttt.oci.utils.oci_available', True)
    yield
    utils._disabled_reason = None


def _mock_llm(mocker, side_effect=None):
    llm = mocker.MagicMock()
    llm.ainvoke = mocker.AsyncMock(side_effect=side_effect)
    mocker.patch('skynet.modules.ttt.oci.utils.ChatOCIGenAI', return_value=llm)
    return llm


class TestInitialize:
    @pytest.mark.asyncio
    async def test_successful_warmup_keeps_oci_enabled(self, mocker):
        llm = _mock_llm(mocker)

        await utils.initialize()

        llm.ainvoke.assert_awaited_once()
        assert not utils.is_oci_disabled()

    @pytest.mark.asyncio
    async def test_failed_warmup_disables_oci_without_raising(self, mocker):
        # e.g. a model id that does not exist on the configured endpoint (HTTP 404)
        _mock_llm(mocker, side_effect=Exception('Entity with key ocid1.generativeaimodel... not found'))

        await utils.initialize()

        assert utils.is_oci_disabled()

    @pytest.mark.asyncio
    async def test_transient_error_keeps_oci_enabled(self, mocker):
        _mock_llm(mocker, side_effect=TransientServiceError(503, 'ServiceUnavailable', {}, 'busy'))

        await utils.initialize()

        assert not utils.is_oci_disabled()

    @pytest.mark.asyncio
    async def test_noop_when_oci_not_configured(self, mocker):
        mocker.patch('skynet.modules.ttt.oci.utils.oci_available', False)
        oci_client = mocker.patch('skynet.modules.ttt.oci.utils.ChatOCIGenAI')

        await utils.initialize()

        oci_client.assert_not_called()
        assert not utils.is_oci_disabled()
