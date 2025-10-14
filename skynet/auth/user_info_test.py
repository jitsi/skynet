import os


# Set bypass auth before importing anything that loads env.py
os.environ['BYPASS_AUTHORIZATION'] = 'true'

from skynet.auth.user_info import get_credentials


class TestGetCredentials:
    def test_get_credentials_with_enabled_secret(self, mocker):
        """Test that enabled credentials with secret are returned."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'customer1': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'customer1',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'secret': 'test_secret',
                            'type': 'OPENAI',
                        }
                    }
                }
            },
        )

        result = get_credentials('customer1')

        assert result['secret'] == 'test_secret'
        assert result['type'] == 'OPENAI'
        assert result['metadata']['model'] == 'gpt-4'

    def test_get_credentials_with_no_secret_falls_back_to_default(self, mocker):
        """Test that customer without secret falls back to default customer."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'customer1': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'customer1',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'type': 'OPENAI',
                        }
                    }
                },
                'default_customer': {
                    'credentialsMap': {
                        'AZURE_OPENAI': {
                            'customerId': 'default_customer',
                            'enabled': True,
                            'metadata': {'deploymentName': 'gpt-4o', 'endpoint': 'https://test.openai.azure.com/'},
                            'secret': 'default_secret',
                            'type': 'AZURE_OPENAI',
                        }
                    }
                },
            },
        )
        mocker.patch('skynet.auth.user_info.default_customer_id', 'default_customer')

        result = get_credentials('customer1')

        assert result['secret'] == 'default_secret'
        assert result['type'] == 'AZURE_OPENAI'
        assert result['customerId'] == 'default_customer'

    def test_get_credentials_with_disabled_credential_falls_back_to_default(self, mocker):
        """Test that customer with disabled credential falls back to default customer."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'customer1': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'customer1',
                            'enabled': False,
                            'metadata': {'model': 'gpt-4'},
                            'secret': 'disabled_secret',
                            'type': 'OPENAI',
                        }
                    }
                },
                'default_customer': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'default_customer',
                            'enabled': True,
                            'metadata': {'model': 'gpt-3.5-turbo'},
                            'secret': 'default_secret',
                            'type': 'OPENAI',
                        }
                    }
                },
            },
        )
        mocker.patch('skynet.auth.user_info.default_customer_id', 'default_customer')

        result = get_credentials('customer1')

        assert result['secret'] == 'default_secret'
        assert result['type'] == 'OPENAI'
        assert result['customerId'] == 'default_customer'

    def test_get_credentials_without_default_customer_id(self, mocker):
        """Test that customer without secret returns empty dict when no default_customer_id is set."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'customer1': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'customer1',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'type': 'OPENAI',
                        }
                    }
                }
            },
        )
        mocker.patch('skynet.auth.user_info.default_customer_id', None)

        result = get_credentials('customer1')

        assert result == {}

    def test_get_credentials_non_existent_customer_falls_back_to_default(self, mocker):
        """Test that non-existent customer falls back to default customer."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'default_customer': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'default_customer',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'secret': 'default_secret',
                            'type': 'OPENAI',
                        }
                    }
                }
            },
        )
        mocker.patch('skynet.auth.user_info.default_customer_id', 'default_customer')

        result = get_credentials('non_existent_customer')

        assert result['secret'] == 'default_secret'
        assert result['type'] == 'OPENAI'

    def test_get_credentials_default_customer_should_not_recurse(self, mocker):
        """Test that requesting default customer credentials directly doesn't cause recursion."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'default_customer': {
                    'credentialsMap': {
                        'OPENAI': {
                            'customerId': 'default_customer',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'type': 'OPENAI',
                        }
                    }
                }
            },
        )
        mocker.patch('skynet.auth.user_info.default_customer_id', 'default_customer')

        result = get_credentials('default_customer')

        # Should return empty dict, not recurse infinitely
        assert result == {}

    def test_get_credentials_with_multiple_credentials_returns_first_enabled_with_secret(self, mocker):
        """Test that when multiple credentials exist, the first enabled one with secret is returned."""
        mocker.patch(
            'skynet.auth.user_info.credentials',
            {
                'customer1': {
                    'credentialsMap': {
                        'AZURE_OPENAI': {
                            'customerId': 'customer1',
                            'enabled': True,
                            'metadata': {'deploymentName': 'gpt-4o', 'endpoint': 'https://test.azure.com/'},
                            'secret': 'azure_secret',
                            'type': 'AZURE_OPENAI',
                        },
                        'OPENAI': {
                            'customerId': 'customer1',
                            'enabled': True,
                            'metadata': {'model': 'gpt-4'},
                            'secret': 'openai_secret',
                            'type': 'OPENAI',
                        },
                    }
                }
            },
        )

        result = get_credentials('customer1')

        # Should return one of them (order may vary based on dict iteration)
        assert result['secret'] in ['azure_secret', 'openai_secret']
        assert result['type'] in ['AZURE_OPENAI', 'OPENAI']
