# diagnosticos/utils/nlp_processor.py

import spacy
import re
from typing import List, Dict, Optional
from django.db import connection

class NLPProcessor:
    def __init__(self):
        self._sintomas_db = None
        self._nlp = None
        self.palabras_severidad = {
            'leve': 1, 'ligero': 1, 'suave': 1, 'leve': 1,
            'moderado': 2, 'regular': 2, 'medio': 2,
            'intenso': 3, 'severo': 3, 'grave': 3, 'fuerte': 3, 
            'insoportable': 3, 'muy fuerte': 3
        }
        
    @property
    def nlp(self):
        if self._nlp is None:
            try:
                self._nlp = spacy.load("es_core_news_md")
                print("✅ spaCy cargado correctamente")
            except OSError:
                import subprocess
                import sys
                print("🔄 Descargando modelo de spaCy...")
                subprocess.run([sys.executable, "-m", "spacy", "download", "es_core_news_md"])
                self._nlp = spacy.load("es_core_news_md")
        return self._nlp
    
    @property
    def sintomas_db(self):
        if self._sintomas_db is None:
            self._cargar_sintomas()
        return self._sintomas_db
    
    def _cargar_sintomas(self):
        """Carga síntomas de la BD de manera segura"""
        try:
            from diagnosticos.models import Sintoma
            
            # Verificar si la tabla existe
            table_name = Sintoma._meta.db_table
            if table_name in connection.introspection.table_names():
                sintomas = Sintoma.objects.all()
                self._sintomas_db = {}
                
                # Crear múltiples variaciones de cada síntoma para mejor matching
                for s in sintomas:
                    nombre = s.nombre.lower()
                    self._sintomas_db[nombre] = s
                    
                    # Crear variaciones comunes
                    if 'dolor de cabeza' in nombre:
                        self._sintomas_db['cefalea'] = s
                        self._sintomas_db['dolor cabeza'] = s
                    elif 'dolor de pecho' in nombre:
                        self._sintomas_db['dolor pecho'] = s
                        self._sintomas_db['dolor torácico'] = s
                    elif 'dificultad para respirar' in nombre:
                        self._sintomas_db['falta de aire'] = s
                        self._sintomas_db['disnea'] = s
                        self._sintomas_db['ahogo'] = s
                    elif 'presión arterial' in nombre:
                        self._sintomas_db['presion'] = s
                        self._sintomas_db['pa'] = s
                
                print(f"✅ {len(self._sintomas_db)} variaciones de síntomas cargadas")
            else:
                print(f"⚠️ Tabla {table_name} no existe aún")
                self._sintomas_db = {}
        except Exception as e:
            print(f"⚠️ Error cargando síntomas: {e}")
            self._sintomas_db = {}
    
    def extraer_sintomas(self, texto: str) -> List[Dict]:
        """Extrae síntomas mencionados en texto libre"""
        if not self.sintomas_db:
            self._cargar_sintomas()
        
        if not self.sintomas_db:
            print("⚠️ No hay síntomas en la base de datos")
            return []
        
        texto_lower = texto.lower()
        print(f"🔍 Procesando texto: '{texto_lower}'")
        
        sintomas_encontrados = []
        
        # Buscar coincidencias exactas y parciales
        for sintoma_nombre, sintoma_obj in self.sintomas_db.items():
            if sintoma_nombre in texto_lower:
                print(f"  ✅ Encontrado: '{sintoma_nombre}'")
                
                severidad = self._detectar_severidad(texto, sintoma_nombre)
                duracion = self._detectar_duracion(texto)
                
                sintomas_encontrados.append({
                    'sintoma': sintoma_obj,
                    'confianza': 0.9,
                    'severidad': severidad,
                    'duracion': duracion,
                    'texto_encontrado': sintoma_nombre
                })
        
        # Búsqueda más flexible si no se encontraron síntomas
        if len(sintomas_encontrados) == 0:
            # Palabras clave comunes
            palabras_clave = {
                'pecho': 'Dolor de pecho',
                'dolor': 'Dolor',
                'cabeza': 'Dolor de cabeza',
                'mareo': 'Mareos',
                'falta aire': 'Dificultad para respirar',
                'presion': 'Presión arterial alta',
                'palpitacion': 'Palpitaciones'
            }
            
            for palabra, sintoma_nombre in palabras_clave.items():
                if palabra in texto_lower:
                    # Buscar el síntoma en la BD
                    for s_nombre, s_obj in self.sintomas_db.items():
                        if sintoma_nombre.lower() in s_nombre:
                            print(f"  ✅ Encontrado por palabra clave: '{palabra}' -> '{s_nombre}'")
                            sintomas_encontrados.append({
                                'sintoma': s_obj,
                                'confianza': 0.7,
                                'severidad': 2,
                                'duracion': None
                            })
                            break
        
        print(f"📊 Total síntomas encontrados: {len(sintomas_encontrados)}")
        return sintomas_encontrados
    
    def _detectar_severidad(self, texto: str, sintoma: str) -> int:
        """Detecta nivel de severidad cerca del síntoma"""
        texto_lower = texto.lower()
        idx = texto_lower.find(sintoma)
        if idx == -1:
            return 2
        
        inicio = max(0, idx - 50)
        fin = min(len(texto), idx + len(sintoma) + 50)
        contexto = texto_lower[inicio:fin]
        
        for palabra, nivel in self.palabras_severidad.items():
            if palabra in contexto:
                return nivel
        
        return 2
    
    def _detectar_duracion(self, texto: str) -> Optional[int]:
        """Extrae duración mencionada en días"""
        patrones = [
            r'(\d+)\s*(días|dias|día|dia)',
            r'desde hace\s*(\d+)\s*(días|dias)',
            r'hace\s*(\d+)\s*(días|dias)',
            r'(\d+)\s*(horas|hora)',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto.lower())
            if match:
                valor = int(match.group(1))
                unidad = match.group(2) if len(match.groups()) > 1 else ""
                
                if 'hora' in unidad:
                    valor = valor // 24 if valor >= 24 else 1
                return valor
        return None
    
    def extraer_presion_arterial(self, texto: str) -> Dict:
        """Extrae valores de presión arterial del texto"""
        patrones = [
            r'(\d{2,3})\s*[/\-]\s*(\d{2,3})',
            r'presion\s*(\d{2,3})\s*[/\-]\s*(\d{2,3})',
            r'pa\s*(\d{2,3})\s*[/\-]\s*(\d{2,3})',
            r'(\d{2,3})\s*sobre\s*(\d{2,3})',
        ]
        
        for patron in patrones:
            match = re.search(patron, texto.lower())
            if match:
                return {
                    'sistolica': int(match.group(1)),
                    'diastolica': int(match.group(2))
                }
        return {}
    
    def extraer_edad(self, texto: str) -> Optional[int]:
        """Extrae edad del paciente del texto"""
        patrones = [
            r'(\d+)\s*(años|año)',
            r'edad[:\s]+(\d+)',
            r'paciente[^\d]*(\d+)\s*(años|año)'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto.lower())
            if match:
                return int(match.group(1))
        return None
    
    def extraer_sexo(self, texto: str) -> Optional[str]:
        """Extrae sexo del paciente del texto"""
        texto_lower = texto.lower()
        if any(p in texto_lower for p in ['masculino', 'hombre', 'varón', 'sr', 'señor']):
            return 'M'
        elif any(p in texto_lower for p in ['femenino', 'mujer', 'sra', 'señora']):
            return 'F'
        return None
    
    def generar_resumen(self, caso) -> str:
        """Genera resumen clínico"""
        try:
            sintomas_list = []
            if caso and hasattr(caso, 'detallesintomacaso_set'):
                sintomas_list = [d.sintoma.nombre for d in caso.detallesintomacaso_set.all()[:3]]
            
            sintomas_text = ', '.join(sintomas_list) if sintomas_list else 'sin síntomas específicos'
            
            edad = getattr(caso, 'edad', '?')
            sexo = caso.get_sexo_display() if hasattr(caso, 'get_sexo_display') else '?'
            clasificacion = caso.get_clasificacion_hta_display() if hasattr(caso, 'get_clasificacion_hta_display') else '?'
            riesgo = getattr(caso, 'riesgo_cv', '?')
            
            return f"Paciente {edad} años, {sexo}, con {clasificacion}. Riesgo {riesgo}. Presenta {sintomas_text}."
        except Exception as e:
            return f"Resumen no disponible: {str(e)}"