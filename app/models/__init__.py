# Import modeller, så de kan importeres direkte fra app.models
from app.models.sample import Sample
from app.models.container import Container
from app.models.test import Test

# __all__ definerer hvad der eksporteres, når nogen bruger "from app.models import *"
__all__ = ['Sample', 'Container', 'Test']