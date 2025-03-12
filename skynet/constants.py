from enum import Enum


PENDING_JOBS_KEY = "jobs:pending"
RUNNING_JOBS_KEY = "jobs:running"
ERROR_JOBS_KEY = "jobs:error"


class Locale(Enum):
    ENGLISH = 'en'
    FRENCH = 'fr'
    GERMAN = 'de'
    ITALIAN = 'it'
    SPANISH = 'es'
