import threading
import time
import requests
from config import OLLAMA_MODEL

class GpuWarmKeeper:
    """
    Mantiene la GPU en estado P2 (relojes máximos: SM ~1850MHz, MEM ~7300MHz)
    durante los silencios de la llamada para evitar la degradación de latencia
    por downclock (P8 a 405MHz) entre turnos.
    """
    
    def __init__(self, model_name: str = OLLAMA_MODEL, interval: float = 0.35):
        self.model_name = model_name
        self.interval = interval
        self._running = False
        self._thread = None
        self._url = "http://localhost:11434/api/generate"
        
    def _loop(self):
        payload = {
            "model": self.model_name,
            "prompt": " ",
            "options": {"num_predict": 1},
            "keep_alive": "24h"
        }
        while self._running:
            try:
                requests.post(self._url, json=payload, timeout=0.6)
            except Exception:
                pass
            time.sleep(self.interval)
            
    def start(self):
        """Inicia el pulso de keepalive en segundo plano."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            
    def stop(self):
        """Detiene el keepalive al finalizar la llamada."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.8)

# Instancia global reutilizable
gpu_keeper = GpuWarmKeeper()
