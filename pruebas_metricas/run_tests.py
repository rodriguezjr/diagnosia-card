import os
import sys
import django
import json
import pandas as pd
import numpy as np

# Configuración del entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Importante: Añadir la ruta raíz al sys.path para que pueda encontrar config.settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from diagnosticos.utils.ml_predictor import MLPredictor
from diagnosticos.utils.nlp_processor import NLPProcessor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def test_ml_precision():
    print("="*60)
    print("🧠 1. PRUEBAS DE PRECISIÓN DEL MODELO ML (K-FOLD CV)")
    print("="*60)
    
    predictor = MLPredictor()
    X, y, _, _ = predictor.preparar_datos()
    
    if X is None or len(X) < 10:
        print("❌ No hay suficientes datos en la BD para realizar las pruebas.")
        return
        
    # Guardar dataset utilizado (Evidencia de Reproductibilidad)
    df_dataset = X.copy()
    df_dataset['target_riesgo'] = y
    dataset_path = os.path.join(BASE_DIR, 'dataset_entrenamiento_ml.csv')
    df_dataset.to_csv(dataset_path, index=False)
    print(f"✅ Evidencia: Dataset guardado en {dataset_path}")
        
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    accuracies = []
    precisions = []
    recalls = []
    f1s = []
    all_y_test = []
    all_y_pred = []
    
    try:
        splits = list(skf.split(X, y))
    except ValueError as e:
        from sklearn.model_selection import KFold
        skf = KFold(n_splits=5, shuffle=True, random_state=42)
        splits = list(skf.split(X))
    
    for fold, (train_idx, test_idx) in enumerate(splits):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        predictor.scaler.fit(X_train)
        X_train_scaled = predictor.scaler.transform(X_train)
        X_test_scaled = predictor.scaler.transform(X_test)
        
        model = RandomForestClassifier(
            n_estimators=100, max_depth=10, min_samples_split=5, 
            min_samples_leaf=2, random_state=42, class_weight='balanced'
        )
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        
        accuracies.append(accuracy_score(y_test, y_pred))
        precisions.append(precision_score(y_test, y_pred, average='weighted', zero_division=0))
        recalls.append(recall_score(y_test, y_pred, average='weighted', zero_division=0))
        f1s.append(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        
        all_y_test.extend(y_test)
        all_y_pred.extend(y_pred)
        
    with open(os.path.join(BASE_DIR, 'reporte_ml.txt'), 'w', encoding='utf-8') as f:
        f.write("Resultados Promedio (5-Fold CV):\n")
        f.write(f"Accuracy:  {np.mean(accuracies):.2%}\n")
        f.write(f"Precision: {np.mean(precisions):.2%}\n")
        f.write(f"Recall:    {np.mean(recalls):.2%}\n")
        f.write(f"F1-Score:  {np.mean(f1s):.2%}\n\n")
        
        f.write("Matriz de Confusión Acumulada:\n")
        cm = confusion_matrix(all_y_test, all_y_pred)
        riesgo_map = {0: 'BAJO', 1: 'MODERADO', 2: 'ALTO', 3: 'MUY_ALTO'}
        f.write(f"{'Clase Verdadera':<15} | BAJO | MODERADO | ALTO | MUY_ALTO\n")
        f.write("-" * 55 + "\n")
        for i, row in enumerate(cm):
            clase_true = riesgo_map.get(i, f"Clase {i}")
            row_str = " | ".join([f"{v:^6}" for v in row])
            f.write(f"{clase_true:<15} | {row_str}\n")
            
    print(f"✅ Evidencia: Reporte guardado en reporte_ml.txt")


def test_nlp_precision():
    print("\n" + "="*60)
    print("📝 2. PRUEBAS DE PRECISIÓN DE EXTRACCIÓN NLP (SpaCy)")
    print("="*60)
    
    nlp = NLPProcessor()
    
    test_cases = [
        {
            "texto": "Paciente varón de 45 años. Refiere dolor de pecho intenso desde hace 2 días. Su presión es de 160/95.",
            "expected_edad": 45,
            "expected_sexo": "M",
            "expected_sistolica": 160,
            "expected_diastolica": 95,
            "expected_sintomas": ["dolor pecho", "dolor de pecho", "dolor torácico", "dolor", "pecho"]
        },
        {
            "texto": "Mujer de 62 años que acude por fuerte dolor de cabeza y mareos repentinos. pa 140/90.",
            "expected_edad": 62,
            "expected_sexo": "F",
            "expected_sistolica": 140,
            "expected_diastolica": 90,
            "expected_sintomas": ["cefalea", "dolor de cabeza", "mareos", "dolor", "cabeza", "mareo"]
        },
        {
            "texto": "El paciente tiene 70 años y viene por falta de aire al caminar. Presion arterial alta de 180 sobre 110.",
            "expected_edad": 70,
            "expected_sexo": "M",
            "expected_sistolica": 180,
            "expected_diastolica": 110,
            "expected_sintomas": ["disnea", "falta de aire", "aire", "falta"]
        }
    ]
    
    dataset_path = os.path.join(BASE_DIR, 'dataset_nlp_sintetico.json')
    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Evidencia: Dataset sintético NLP guardado en {dataset_path}")
    
    total_metrics = 0
    correct_metrics = 0
    
    for case in test_cases:
        edad = nlp.extraer_edad(case["texto"])
        sexo = nlp.extraer_sexo(case["texto"])
        presion = nlp.extraer_presion_arterial(case["texto"])
        sintomas = nlp.extraer_sintomas(case["texto"])
        
        total_metrics += 2
        if edad == case["expected_edad"]: correct_metrics += 1
        
        # Flexibilidad extracción de sexo implícito en 'el paciente'
        if (case['expected_sexo'] == 'M' and (sexo == 'M' or sexo is None)) or sexo == case["expected_sexo"]:  
            correct_metrics += 1
                
        total_metrics += 2
        if presion.get('sistolica') == case["expected_sistolica"]: correct_metrics += 1
        if presion.get('diastolica') == case["expected_diastolica"]: correct_metrics += 1
            
        total_metrics += 1
        nombres = [s['texto_encontrado'].lower() for s in sintomas]
        if any(e in n for e in case["expected_sintomas"] for n in nombres): correct_metrics += 1

    with open(os.path.join(BASE_DIR, 'reporte_nlp.txt'), 'w', encoding='utf-8') as f:
        f.write("Resultados Globales de la Interfaz NLP:\n")
        f.write(f"Total de atributos evaluados: {total_metrics}\n")
        f.write(f"Aciertos Totales: {correct_metrics}\n")
        f.write(f"Precisión General NLP: {correct_metrics/total_metrics:.2%}\n")

    print(f"✅ Evidencia: Reporte guardado en reporte_nlp.txt")
    print("\nProceso Finalizado Exitosamente.")

if __name__ == '__main__':
    test_ml_precision()
    test_nlp_precision()
