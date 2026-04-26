import sys
import os

# Añadimos la carpeta api/app al radar de Python cuando ejecutamos pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../api/app')))