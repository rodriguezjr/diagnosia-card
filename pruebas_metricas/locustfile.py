from locust import HttpUser, task, between
import json

class DiagnosiaPacienteSimulado(HttpUser):
    # Simula el tiempo que el usuario 'médico' o 'paciente' tarda 
    # en leer la pantalla antes de escribir (entre 1 a 5 segundos)
    wait_time = between(1, 5)

    @task(3)
    def cargar_dashboard_estadisticas(self):
        # Mide el tiempo en recibir la página principal de estadísticas sin postear nada (solo carga UI y DB GETS)
        self.client.get("/estadisticas/")

    @task(5)
    def usar_procesamiento_chatbot(self):
        # Mide los tiempos de carga de la API bajo estrés al momento de la extracción NLP
        payload = {
            "texto": "Paciente hombre de 55 años, presenta un extremo dolor en el pecho durante 5 dias con una pa de 160/90."
        }
        
        headers = {'Content-Type': 'application/json'}
        
        with self.client.post("/api/procesar_texto/", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"La API de NLP respondió con error {response.status_code}")
