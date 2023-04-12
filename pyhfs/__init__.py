# Exposed code by default
from .session import Session
from .client import Client
from .client import ClientSession
from .exception import *  # Automatically imports all public exception

# Returns installed version
import importlib.metadata
__version__ = importlib.metadata.version("pyhfs")
