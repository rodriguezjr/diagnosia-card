# diagnosticos/utils/motor_inferencia.py

import re
from typing import Dict, Any, List
from diagnosticos.models import ReglaConocimiento

class MotorInferencia:
    def __init__(self):
        self.hechos = {}
    
    def evaluar_condicion(self, condicion: str, hechos: Dict[str, Any]) -> bool:
        condicion_eval = condicion
        for var, valor in hechos.items():
            if valor is not None:
                if isinstance(valor, (int, float)):
                    condicion_eval = condicion_eval.replace(var, str(valor))
                elif isinstance(valor, str):
                    condicion_eval = condicion_eval.replace(var, f"'{valor}'")
        
        try:
            patron_seguro = r'^[0-9\s\>\<\=\=\(\)ANDOR\']+$'
            if re.match(patron_seguro, condicion_eval):
                return eval(condicion_eval)
        except:
            return False
        return False
    
    def inferir(self, datos_paciente: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.hechos = datos_paciente
        recomendaciones = []
        
        reglas = ReglaConocimiento.objects.filter(activa=True).order_by('prioridad')
        
        for regla in reglas:
            if self.evaluar_condicion(regla.condicion, self.hechos):
                recomendaciones.append({
                    'regla': regla,
                    'protocolo': regla.protocolo,
                    'recomendacion': regla.recomendacion,
                })
        
        return recomendaciones
    
    def clasificar_hta(self, sistolica: int, diastolica: int) -> str:
        if sistolica < 120 and diastolica < 80:
            return 'OPTIMA'
        elif sistolica < 130 and diastolica < 85:
            return 'NORMAL'
        elif sistolica < 140 and diastolica < 90:
            return 'NORMAL_ALTA'
        elif sistolica < 160 and diastolica < 100:
            return 'GRADO_1'
        elif sistolica < 180 and diastolica < 110:
            return 'GRADO_2'
        else:
            return 'GRADO_3'
    
    def calcular_riesgo_score(self, edad: int, sexo: str, sistolica: int, fumador: bool = False) -> str:
        if sexo == 'M':
            if edad > 65 or sistolica > 160 or fumador:
                return 'ALTO'
        else:
            if edad > 70 or sistolica > 170 or fumador:
                return 'ALTO'
        
        if edad > 50 or sistolica > 140:
            return 'MODERADO'
        
        return 'BAJO'