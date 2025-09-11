from enum import Enum

response_prefix = 'SkynetResponse'

# Processor-specific queue keys
PENDING_JOBS_OPENAI_KEY = 'jobs:pending:openai'
PENDING_JOBS_AZURE_KEY = 'jobs:pending:azure'
PENDING_JOBS_OCI_KEY = 'jobs:pending:oci'
PENDING_JOBS_LOCAL_KEY = 'jobs:pending:local'

RUNNING_JOBS_OPENAI_KEY = 'jobs:running:openai'
RUNNING_JOBS_AZURE_KEY = 'jobs:running:azure'
RUNNING_JOBS_OCI_KEY = 'jobs:running:oci'
RUNNING_JOBS_LOCAL_KEY = 'jobs:running:local'

ERROR_JOBS_OPENAI_KEY = 'jobs:error:openai'
ERROR_JOBS_AZURE_KEY = 'jobs:error:azure'
ERROR_JOBS_OCI_KEY = 'jobs:error:oci'
ERROR_JOBS_LOCAL_KEY = 'jobs:error:local'


class Locale(Enum):
    ENGLISH = 'en'
    FRENCH = 'fr'
    GERMAN = 'de'
    ITALIAN = 'it'
    SPANISH = 'es'
