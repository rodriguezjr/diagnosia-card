# diagnosticos/utils/ml_predictor.py

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
from datetime import datetime
from diagnosticos.models import CasoClinico

class MLPredictor:
    """
    Modelo de Machine Learning para predecir riesgo cardiovascular
    Basado en Random Forest Classifier
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.entrenado = False
        self.precision = 0
        self.feature_names = ['edad', 'sistolica', 'diastolica', 'sexo_m', 'num_sintomas', 'num_factores']
        self.modelo_path = 'modelos/random_forest_riesgo.pkl'
        self.scaler_path = 'modelos/scaler.pkl'
        self.reporte_path = 'modelos/reporte_entrenamiento.txt'
        
        # Crear directorio si no existe
        os.makedirs('modelos', exist_ok=True)
    
    def preparar_datos(self):
        """
        Prepara los datos de casos clínicos para entrenamiento
        """
        casos = CasoClinico.objects.all().select_related('diagnostico').prefetch_related('sintomas', 'factores_riesgo')
        
        if casos.count() < 10:
            print(f"⚠️ Pocos casos para entrenar: {casos.count()} (mínimo 10)")
            return None, None, None, None
        
        print(f"📊 Preparando {casos.count()} casos para entrenamiento...")
        
        datos = []
        etiquetas = []
        
        # Mapeo de riesgo a número
        riesgo_map = {
            'BAJO': 0,
            'MODERADO': 1,
            'ALTO': 2,
            'MUY_ALTO': 3
        }
        
        for caso in casos:
            try:
                # Características del caso
                features = {
                    'edad': caso.edad,
                    'sistolica': caso.presion_sistolica,
                    'diastolica': caso.presion_diastolica,
                    'sexo_m': 1 if caso.sexo == 'M' else 0,
                    'num_sintomas': caso.sintomas.count(),
                    'num_factores': caso.factores_riesgo.count(),
                }
                
                # Target (riesgo cardiovascular)
                target = riesgo_map.get(caso.riesgo_cv, 1)
                
                datos.append(features)
                etiquetas.append(target)
                
            except Exception as e:
                print(f"⚠️ Error procesando caso {caso.id}: {e}")
                continue
        
        if len(datos) < 10:
            print(f"⚠️ Datos insuficientes después del filtrado: {len(datos)}")
            return None, None, None, None
        
        # Convertir a DataFrame y arrays
        X = pd.DataFrame(datos)
        y = np.array(etiquetas)
        
        print(f"✅ Datos preparados: {len(X)} muestras, {len(X.columns)} características")
        print(f"📊 Distribución de clases: {np.bincount(y)}")
        
        return X, y, datos, etiquetas
    
    def entrenar(self, test_size=0.2, random_state=42):
        """
        Entrena el modelo de Random Forest con los datos disponibles
        """
        print("\n" + "="*60)
        print("🤖 ENTRENANDO MODELO DE IA PREDICTIVA")
        print("="*60)
        
        X, y, datos, etiquetas = self.preparar_datos()
        
        if X is None or len(X) < 10:
            print("❌ No hay suficientes datos para entrenar el modelo")
            return 0.0
        
        try:
            # Dividir en entrenamiento y prueba
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            print(f"📊 Entrenamiento: {len(X_train)} muestras")
            print(f"📊 Prueba: {len(X_test)} muestras")
            
            # Escalar características
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Crear y entrenar modelo
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                class_weight='balanced'
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluar
            y_pred = self.model.predict(X_test_scaled)
            self.precision = accuracy_score(y_test, y_pred)
            
            print(f"✅ Precisión del modelo: {self.precision:.2%}")
            
            # Mostrar importancia de características
            importancias = self.model.feature_importances_
            print("\n📊 Importancia de características:")
            for nombre, imp in zip(self.feature_names, importancias):
                print(f"   {nombre}: {imp:.2%}")
            
            # Guardar modelo
            joblib.dump(self.model, self.modelo_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            # Guardar reporte
            self._guardar_reporte(X_test, y_test, y_pred, importancias)
            
            self.entrenado = True
            return self.precision
            
        except Exception as e:
            print(f"❌ Error entrenando modelo: {e}")
            import traceback
            traceback.print_exc()
            return 0.0
    
    def _guardar_reporte(self, X_test, y_test, y_pred, importancias):
        """Guarda un reporte detallado del entrenamiento"""
        try:
            with open(self.reporte_path, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("REPORTE DE ENTRENAMIENTO - IA PREDICTIVA\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                
                f.write(f"Precisión del modelo: {self.precision:.2%}\n\n")
                
                f.write("Matriz de Confusión:\n")
                f.write(str(confusion_matrix(y_test, y_pred)) + "\n\n")
                
                f.write("Reporte de Clasificación:\n")
                f.write(classification_report(y_test, y_pred, 
                        target_names=['BAJO', 'MODERADO', 'ALTO', 'MUY_ALTO']))
                
                f.write("\nImportancia de Características:\n")
                for nombre, imp in zip(self.feature_names, importancias):
                    f.write(f"  {nombre}: {imp:.2%}\n")
                    
            print(f"✅ Reporte guardado en {self.reporte_path}")
        except Exception as e:
            print(f"⚠️ Error guardando reporte: {e}")
    
    def predecir(self, datos_paciente: dict) -> dict:
        """
        Predice el riesgo cardiovascular para un nuevo paciente
        
        Args:
            datos_paciente: Diccionario con edad, sexo, sistolica, diastolica, 
                           sintomas_ids, factores_nombres
        """
        if not self.entrenado:
            try:
                self.model = joblib.load(self.modelo_path)
                self.scaler = joblib.load(self.scaler_path)
                self.entrenado = True
                print("✅ Modelo cargado desde archivo")
            except Exception as e:
                print(f"⚠️ No se pudo cargar el modelo: {e}")
                return {
                    'error': 'Modelo no entrenado',
                    'riesgo': 'NO_DISPONIBLE',
                    'confianza': 0,
                    'probabilidades': {}
                }
        
        try:
            # Preparar características del paciente
            features = pd.DataFrame([{
                'edad': datos_paciente.get('edad', 50),
                'sistolica': datos_paciente.get('sistolica', 120),
                'diastolica': datos_paciente.get('diastolica', 80),
                'sexo_m': 1 if datos_paciente.get('sexo') == 'M' else 0,
                'num_sintomas': len(datos_paciente.get('sintomas_ids', [])),
                'num_factores': len(datos_paciente.get('factores_nombres', [])),
            }])
            
            # Escalar características
            features_scaled = self.scaler.transform(features)
            
            # Predecir
            prediccion = self.model.predict(features_scaled)[0]
            probabilidades = self.model.predict_proba(features_scaled)[0]
            
            # Mapear predicción a texto
            riesgo_map = {0: 'BAJO', 1: 'MODERADO', 2: 'ALTO', 3: 'MUY_ALTO'}
            
            # Crear diccionario de probabilidades
            prob_dict = {}
            for i, prob in enumerate(probabilidades):
                if i < 4:  # Solo las primeras 4 clases
                    prob_dict[riesgo_map.get(i, f'CLASE_{i}')] = round(float(prob) * 100, 1)
            
            resultado = {
                'riesgo': riesgo_map.get(prediccion, 'DESCONOCIDO'),
                'confianza': round(float(max(probabilidades) * 100), 1),
                'probabilidades': prob_dict,
                'error': None
            }
            
            return resultado
            
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return {
                'error': str(e),
                'riesgo': 'ERROR',
                'confianza': 0,
                'probabilidades': {}
            }
    
    def get_importancia_caracteristicas(self):
        """Retorna la importancia de cada característica en el modelo"""
        if not self.entrenado:
            try:
                self.model = joblib.load(self.modelo_path)
                self.entrenado = True
            except:
                return []
        
        if self.model:
            importancias = self.model.feature_importances_
            return [
                {'nombre': nombre, 'importancia': round(float(imp * 100), 1)}
                for nombre, imp in zip(self.feature_names, importancias)
            ]
        return []
    
    def get_estadisticas_modelo(self):
        """Retorna estadísticas del modelo entrenado"""
        stats = {
            'entrenado': self.entrenado,
            'precision': round(self.precision * 100, 1) if self.precision else 0,
            'total_casos': CasoClinico.objects.count(),
            'fecha_ultimo_entrenamiento': self._get_fecha_ultimo_entrenamiento(),
            'caracteristicas': self.feature_names
        }
        return stats
    
    def _get_fecha_ultimo_entrenamiento(self):
        """Obtiene la fecha del último entrenamiento"""
        try:
            if os.path.exists(self.reporte_path):
                return datetime.fromtimestamp(os.path.getmtime(self.reporte_path))
        except:
            pass
        return None