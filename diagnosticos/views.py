from django.shortcuts import render

# Create your views here.
# diagnosticos/views.py

import json
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Count
from django.core.exceptions import ImproperlyConfigured

# Importar modelos
from .models import (
    CasoClinico, Enfermedad, Sintoma, FactorRiesgo,
    ProtocoloClinico, ReglaConocimiento
)

# Importar utilidades
from .utils.motor_inferencia import MotorInferencia
from .utils.nlp_processor import NLPProcessor
from .utils.ml_predictor import MLPredictor

from django.db.models import Count, Q, Avg, Min, Max
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Inicializar componentes de forma segura
motor = MotorInferencia()
nlp = NLPProcessor()  # Ahora no intenta acceder a la BD inmediatamente
ml_predictor = MLPredictor()

def chatbot_view(request):
    """Vista principal del chatbot con resultados unificados"""
    
    try:
        sintomas = Sintoma.objects.all().order_by('categoria', 'nombre')
        factores = FactorRiesgo.objects.all()
        protocolos = ProtocoloClinico.objects.all()[:5]
    except Exception as e:
        print(f"⚠️ Error cargando datos iniciales: {e}")
        sintomas = []
        factores = []
        protocolos = []
    
    resultados = None
    
    if request.method == 'POST':
        print("\n" + "="*60)
        print("📊 NUEVA EVALUACIÓN RECIBIDA")
        print("="*60)
        
        # Obtener datos del formulario
        edad = int(request.POST.get('edad', 0))
        sexo = request.POST.get('sexo')
        sistolica = int(request.POST.get('sistolica', 0))
        diastolica = int(request.POST.get('diastolica', 0))
        sintomas_ids = [int(id) for id in request.POST.getlist('sintomas') if id]
        factores_nombres = request.POST.getlist('factores')
        
        print(f"📝 Datos recibidos:")
        print(f"   Edad: {edad}")
        print(f"   Sexo: {sexo}")
        print(f"   PA: {sistolica}/{diastolica}")
        print(f"   Síntomas IDs: {sintomas_ids}")
        print(f"   Factores: {factores_nombres}")
        
        if sistolica > 0 and diastolica > 0:
            # ============================================
            # 1. RESULTADO DEL MOTOR DE REGLAS (Basado en guías)
            # ============================================
            clasificacion = motor.clasificar_hta(sistolica, diastolica)
            riesgo_reglas = motor.calcular_riesgo_score(
                edad, sexo, sistolica, 'Tabaquismo' in factores_nombres
            )
            
            # Traducir clasificación a texto amigable
            clasificacion_texto = dict(CasoClinico.CLASIFICACION_HTA).get(clasificacion, clasificacion)
            
            print(f"\n🤖 Motor de Reglas:")
            print(f"   Clasificación: {clasificacion_texto}")
            print(f"   Riesgo: {riesgo_reglas}")
            
            # ============================================
            # 2. PREDICCIÓN DEL MODELO ML
            # ============================================
            datos_ml = {
                'edad': edad,
                'sexo': sexo,
                'sistolica': sistolica,
                'diastolica': diastolica,
                'sintomas_ids': sintomas_ids,
                'factores_nombres': factores_nombres,
            }
            prediccion_ml = ml_predictor.predecir(datos_ml)
            
            print(f"\n🧠 Modelo ML:")
            print(f"   Riesgo predicho: {prediccion_ml.get('riesgo', 'N/A')}")
            print(f"   Confianza: {prediccion_ml.get('confianza', 0)}%")
            
            # ============================================
            # 3. SISTEMA HÍBRIDO: COMBINAR RESULTADOS
            # ============================================
            
            # Determinar el riesgo final (con mayor peso al ML si tiene suficiente confianza)
            riesgo_final = riesgo_reglas  # Por defecto, usar reglas
            confianza_final = 85  # Confianza base de las reglas
            
            if prediccion_ml.get('confianza', 0) > 70:
                # Si ML tiene alta confianza (>70%), usar ML
                riesgo_final = prediccion_ml['riesgo']
                confianza_final = prediccion_ml['confianza']
                metodo = "Machine Learning"
            elif prediccion_ml.get('confianza', 0) > 50:
                # Si ML tiene confianza media, promediar
                pesos = {'BAJO': 1, 'MODERADO': 2, 'ALTO': 3, 'MUY_ALTO': 4}
                peso_reglas = pesos.get(riesgo_reglas, 2)
                peso_ml = pesos.get(prediccion_ml['riesgo'], 2)
                
                # Promedio ponderado por confianza
                peso_promedio = (peso_reglas * 0.6 + peso_ml * 0.4)
                
                # Convertir de vuelta a texto
                if peso_promedio < 1.5:
                    riesgo_final = 'BAJO'
                elif peso_promedio < 2.5:
                    riesgo_final = 'MODERADO'
                elif peso_promedio < 3.5:
                    riesgo_final = 'ALTO'
                else:
                    riesgo_final = 'MUY_ALTO'
                
                confianza_final = (85 * 0.6 + prediccion_ml['confianza'] * 0.4)
                metodo = "Sistema Híbrido"
            else:
                # ML con baja confianza, usar solo reglas
                riesgo_final = riesgo_reglas
                confianza_final = 85
                metodo = "Guías Clínicas"
            
            print(f"\n🎯 Resultado Final:")
            print(f"   Método: {metodo}")
            print(f"   Riesgo: {riesgo_final}")
            print(f"   Confianza: {confianza_final:.1f}%")
            
            # ============================================
            # 4. BUSCAR PROTOCOLO RECOMENDADO
            # ============================================
            protocolo_recomendado = None
            recomendaciones = []
            
            # Buscar protocolo según clasificación y riesgo
            if clasificacion in ['GRADO_3'] or riesgo_final in ['MUY_ALTO']:
                # Casos severos
                protocolo_recomendado = ProtocoloClinico.objects.filter(
                    titulo__icontains='crisis'
                ).first()
                if not protocolo_recomendado:
                    protocolo_recomendado = ProtocoloClinico.objects.filter(
                        titulo__icontains='Grado 2'
                    ).first()
            elif clasificacion in ['GRADO_2'] or riesgo_final in ['ALTO']:
                # Casos moderados-altos
                protocolo_recomendado = ProtocoloClinico.objects.filter(
                    titulo__icontains='Grado 2'
                ).first()
            elif clasificacion in ['GRADO_1'] or riesgo_final in ['MODERADO']:
                # Casos leves-moderados
                protocolo_recomendado = ProtocoloClinico.objects.filter(
                    titulo__icontains='Grado 1'
                ).first()
            else:
                # Casos de bajo riesgo
                protocolo_recomendado = ProtocoloClinico.objects.filter(
                    titulo__icontains='prevención'
                ).first()
            
            # Si no se encontró protocolo específico, usar el primero
            if not protocolo_recomendado:
                protocolo_recomendado = ProtocoloClinico.objects.first()
            
            # Obtener reglas activadas para recomendaciones adicionales
            hechos = {'edad': edad, 'sistolica': sistolica, 'diastolica': diastolica}
            reglas_activadas = motor.inferir(hechos)
            
            # Crear recomendaciones personalizadas
            if reglas_activadas:
                for regla in reglas_activadas[:2]:  # Máximo 2 recomendaciones
                    recomendaciones.append(regla['recomendacion'])
            
            # ============================================
            # 5. PREPARAR RESULTADO UNIFICADO
            # ============================================
            resultados = {
                # Datos del paciente
                'edad': edad,
                'sexo': 'Masculino' if sexo == 'M' else 'Femenino' if sexo == 'F' else 'No especificado',
                'sistolica': sistolica,
                'diastolica': diastolica,
                
                # Clasificación
                'clasificacion': clasificacion_texto,
                
                # Riesgo (resultado final unificado)
                'riesgo_final': riesgo_final,
                'confianza_final': round(confianza_final, 1),
                'metodo': metodo,
                
                # Resultados individuales (para transparencia)
                'riesgo_reglas': riesgo_reglas,
                'prediccion_ml': prediccion_ml,
                
                # Protocolo recomendado
                'protocolo_recomendado': protocolo_recomendado,
                
                # Recomendaciones adicionales
                'recomendaciones': recomendaciones,
            }
            
            print("\n" + "="*60)
            print("✅ Evaluación completada")
            print("="*60)
    
    context = {
        'sintomas': sintomas,
        'factores': factores,
        'protocolos': protocolos,
        'resultados': resultados,
    }
    return render(request, 'diagnosticos/chatbot.html', context)

@csrf_exempt
def procesar_texto_api(request):
    """API para procesar texto con NLP - VERSIÓN MEJORADA"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            texto = data.get('texto', '')
            
            print(f"🔍 API recibió texto: '{texto}'")
            
            # Extraer síntomas
            sintomas_detectados = nlp.extraer_sintomas(texto)
            
            # Extraer otros datos
            presion = nlp.extraer_presion_arterial(texto)
            edad = nlp.extraer_edad(texto)
            sexo = nlp.extraer_sexo(texto)
            
            print(f"📊 Datos extraídos: edad={edad}, sexo={sexo}, presión={presion}")
            
            response_data = {
                'sintomas_detectados': [
                    {
                        'id': s['sintoma'].id,
                        'nombre': s['sintoma'].nombre,
                        'confianza': s['confianza'],
                        'severidad': s['severidad'],
                        'duracion': s['duracion'],
                        'metodo': s.get('metodo', 'exacto')
                    }
                    for s in sintomas_detectados
                ],
                'datos_paciente': {
                    'edad': edad,
                    'sexo': sexo,
                    'presion_sistolica': presion.get('sistolica') if presion else None,
                    'presion_diastolica': presion.get('diastolica') if presion else None,
                },
                'texto_original': texto[:100] + '...' if len(texto) > 100 else texto
            }
            return JsonResponse(response_data)
        except Exception as e:
            print(f"❌ Error en API: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def protocolos_view(request):
    """Vista de protocolos clínicos"""
    try:
        protocolos = ProtocoloClinico.objects.all().order_by('-nivel_evidencia')
    except:
        protocolos = []
    
    context = {'protocolos': protocolos}
    return render(request, 'diagnosticos/protocolos.html', context)

def estadisticas_view(request):
    """
    Dashboard completo de estadísticas y análisis de datos
    """
    print("\n" + "="*60)
    print("📊 ACCEDIENDO AL DASHBOARD DE ESTADÍSTICAS")
    print("="*60)
    
    # ============================================
    # 1. ESTADÍSTICAS GENERALES
    # ============================================
    total_casos = CasoClinico.objects.count()
    total_enfermedades = Enfermedad.objects.count()
    total_sintomas = Sintoma.objects.count()
    total_factores = FactorRiesgo.objects.count()
    total_protocolos = ProtocoloClinico.objects.count()
    
    # Casos por resultado
    casos_exitosos = CasoClinico.objects.filter(resultado='CONTROLADO').count()
    casos_no_controlados = CasoClinico.objects.filter(resultado='NO_CONTROLADO').count()
    casos_mejoria = CasoClinico.objects.filter(resultado='MEJORIA').count()
    
    tasa_exito = round((casos_exitosos / total_casos * 100) if total_casos > 0 else 0, 1)
    
    # ============================================
    # 2. ESTADÍSTICAS POR RIESGO CARDIOVASCULAR
    # ============================================
    casos_por_riesgo = []
    riesgo_labels = []
    riesgo_counts = []
    riesgo_colors = []
    
    for riesgo, label in CasoClinico.RIESGO_CV:
        count = CasoClinico.objects.filter(riesgo_cv=riesgo).count()
        if count > 0:
            casos_por_riesgo.append({
                'riesgo': riesgo,
                'label': label,
                'count': count,
                'porcentaje': round(count / total_casos * 100, 1) if total_casos > 0 else 0
            })
            riesgo_labels.append(label)
            riesgo_counts.append(count)
            
            # Colores para gráficos
            if riesgo == 'BAJO':
                riesgo_colors.append('#10b981')
            elif riesgo == 'MODERADO':
                riesgo_colors.append('#f59e0b')
            elif riesgo == 'ALTO':
                riesgo_colors.append('#ef4444')
            elif riesgo == 'MUY_ALTO':
                riesgo_colors.append('#7f1d1d')
    
    # ============================================
    # 3. ESTADÍSTICAS POR CLASIFICACIÓN HTA
    # ============================================
    casos_por_clasificacion = []
    for clasif, label in CasoClinico.CLASIFICACION_HTA:
        count = CasoClinico.objects.filter(clasificacion_hta=clasif).count()
        if count > 0:
            casos_por_clasificacion.append({
                'clasificacion': clasif,
                'label': label,
                'count': count,
                'porcentaje': round(count / total_casos * 100, 1) if total_casos > 0 else 0
            })
    
    # ============================================
    # 4. ESTADÍSTICAS DE EDAD
    # ============================================
    edad_stats = CasoClinico.objects.aggregate(
        edad_min=Min('edad'),
        edad_max=Max('edad'),
        edad_promedio=Avg('edad')
    )
    
    # Distribución por rangos etarios
    rangos_edad = [
        {'rango': '18-30 años', 'min': 18, 'max': 30},
        {'rango': '31-45 años', 'min': 31, 'max': 45},
        {'rango': '46-60 años', 'min': 46, 'max': 60},
        {'rango': '61-75 años', 'min': 61, 'max': 75},
        {'rango': '76-90 años', 'min': 76, 'max': 90},
        {'rango': '90+ años', 'min': 91, 'max': 120},
    ]
    
    distribucion_edad = []
    for rango in rangos_edad:
        count = CasoClinico.objects.filter(
            edad__gte=rango['min'],
            edad__lte=rango['max']
        ).count()
        if count > 0:
            distribucion_edad.append({
                'rango': rango['rango'],
                'count': count,
                'porcentaje': round(count / total_casos * 100, 1) if total_casos > 0 else 0
            })
    
    # ============================================
    # 5. ESTADÍSTICAS DE PRESIÓN ARTERIAL
    # ============================================
    presion_stats = CasoClinico.objects.aggregate(
        sistolica_min=Min('presion_sistolica'),
        sistolica_max=Max('presion_sistolica'),
        sistolica_promedio=Avg('presion_sistolica'),
        diastolica_min=Min('presion_diastolica'),
        diastolica_max=Max('presion_diastolica'),
        diastolica_promedio=Avg('presion_diastolica'),
    )
    
    # ============================================
    # 6. TOP ENFERMEDADES
    # ============================================
    top_enfermedades = Enfermedad.objects.annotate(
        num_casos=Count('casoclinico'),
        num_exitosos=Count('casoclinico', filter=Q(casoclinico__resultado='CONTROLADO'))
    ).order_by('-num_casos')[:10]
    
    # ============================================
    # 7. TOP SÍNTOMAS
    # ============================================
    top_sintomas = Sintoma.objects.annotate(
        frecuencia=Count('detallesintomacaso')
    ).filter(frecuencia__gt=0).order_by('-frecuencia')[:15]
    
    # ============================================
    # 8. TOP FACTORES DE RIESGO
    # ============================================
    top_factores = FactorRiesgo.objects.annotate(
        frecuencia=Count('casoclinico')
    ).filter(frecuencia__gt=0).order_by('-frecuencia')[:10]
    
    # ============================================
    # 9. EVOLUCIÓN TEMPORAL
    # ============================================
    ultimos_12_meses = datetime.now() - timedelta(days=365)
    casos_por_mes = CasoClinico.objects.filter(
        fecha_registro__gte=ultimos_12_meses
    ).annotate(
        mes=TruncMonth('fecha_registro')
    ).values('mes').annotate(
        total=Count('id'),
        exitosos=Count('id', filter=Q(resultado='CONTROLADO'))
    ).order_by('mes')
    
    meses_labels = []
    casos_mes_data = []
    exitosos_mes_data = []
    
    for item in casos_por_mes:
        if item['mes']:
            meses_labels.append(item['mes'].strftime('%b %Y'))
            casos_mes_data.append(item['total'])
            exitosos_mes_data.append(item['exitosos'])
    
    # ============================================
    # 10. DISTRIBUCIÓN POR SEXO
    # ============================================
    sexo_counts = CasoClinico.objects.values('sexo').annotate(
        count=Count('id')
    ).order_by('sexo')
    
    sexo_labels = []
    sexo_data = []
    for item in sexo_counts:
        if item['sexo'] == 'M':
            sexo_labels.append('Masculino')
        elif item['sexo'] == 'F':
            sexo_labels.append('Femenino')
        else:
            sexo_labels.append('Otro')
        sexo_data.append(item['count'])
    
    # ============================================
    # 11. CORRELACIÓN EDAD vs PRESIÓN
    # ============================================
    datos_correlacion = []
    for caso in CasoClinico.objects.all()[:100]:  # Limitar a 100 para rendimiento
        datos_correlacion.append({
            'edad': caso.edad,
            'sistolica': caso.presion_sistolica,
            'diastolica': caso.presion_diastolica,
            'riesgo': caso.riesgo_cv
        })
    
    # ============================================
    # 12. GENERAR GRÁFICOS CON PLOTLY
    # ============================================
    
    # Gráfico 1: Distribución de Riesgo (Pastel)
    fig_riesgo = go.Figure(data=[go.Pie(
        labels=riesgo_labels,
        values=riesgo_counts,
        marker=dict(colors=riesgo_colors),
        textinfo='label+percent',
        insidetextorientation='radial',
        hole=0.3
    )])
    fig_riesgo.update_layout(
        title='Distribución de Riesgo Cardiovascular',
        showlegend=False,
        height=400
    )
    graph_riesgo = fig_riesgo.to_html()
    
    # Gráfico 2: Distribución por Edad (Barras)
    fig_edad = px.bar(
        x=[d['rango'] for d in distribucion_edad],
        y=[d['count'] for d in distribucion_edad],
        title='Distribución por Rangos de Edad',
        labels={'x': 'Rango Etario', 'y': 'Número de Pacientes'},
        color=[d['count'] for d in distribucion_edad],
        color_continuous_scale='Blues'
    )
    fig_edad.update_layout(height=400)
    graph_edad = fig_edad.to_html()
    
    # Gráfico 3: Top Enfermedades (Barras Horizontales)
    fig_enfermedades = px.bar(
        x=[e.num_casos for e in top_enfermedades],
        y=[e.nombre for e in top_enfermedades],
        title='Top 10 Enfermedades más Diagnosticadas',
        labels={'x': 'Número de Casos', 'y': ''},
        orientation='h',
        color=[e.num_casos for e in top_enfermedades],
        color_continuous_scale='Viridis'
    )
    fig_enfermedades.update_layout(height=500)
    graph_enfermedades = fig_enfermedades.to_html()
    
    # Gráfico 4: Top Síntomas (Barras)
    fig_sintomas = px.bar(
        x=[s.frecuencia for s in top_sintomas],
        y=[s.nombre for s in top_sintomas],
        title='Top 15 Síntomas más Frecuentes',
        labels={'x': 'Frecuencia', 'y': ''},
        orientation='h',
        color=[s.frecuencia for s in top_sintomas],
        color_continuous_scale='Plasma'
    )
    fig_sintomas.update_layout(height=600)
    graph_sintomas = fig_sintomas.to_html()
    
    # Gráfico 5: Evolución Temporal (Líneas)
    fig_temporal = go.Figure()
    fig_temporal.add_trace(go.Scatter(
        x=meses_labels,
        y=casos_mes_data,
        mode='lines+markers',
        name='Total Casos',
        line=dict(color='#2563eb', width=3)
    ))
    fig_temporal.add_trace(go.Scatter(
        x=meses_labels,
        y=exitosos_mes_data,
        mode='lines+markers',
        name='Casos Exitosos',
        line=dict(color='#10b981', width=3)
    ))
    fig_temporal.update_layout(
        title='Evolución de Casos en los Últimos 12 Meses',
        xaxis_title='Mes',
        yaxis_title='Número de Casos',
        height=400,
        hovermode='x unified'
    )
    graph_temporal = fig_temporal.to_html()
    
    # Gráfico 6: Distribución por Sexo (Pastel)
    fig_sexo = go.Figure(data=[go.Pie(
        labels=sexo_labels,
        values=sexo_data,
        marker=dict(colors=['#2563eb', '#f59e0b', '#94a3b8']),
        textinfo='label+percent',
        hole=0.3
    )])
    fig_sexo.update_layout(
        title='Distribución por Sexo',
        showlegend=False,
        height=350
    )
    graph_sexo = fig_sexo.to_html()
    
    # Gráfico 7: Correlación Edad vs Presión Sistólica (Scatter)
    if datos_correlacion:
        df_corr = pd.DataFrame(datos_correlacion)
        fig_corr = px.scatter(
            df_corr,
            x='edad',
            y='sistolica',
            color='riesgo',
            title='Correlación: Edad vs Presión Sistólica',
            labels={'edad': 'Edad (años)', 'sistolica': 'Presión Sistólica (mmHg)', 'riesgo': 'Riesgo'},
            color_discrete_map={
                'BAJO': '#10b981',
                'MODERADO': '#f59e0b',
                'ALTO': '#ef4444',
                'MUY_ALTO': '#7f1d1d'
            },
            trendline='ols'
        )
        fig_corr.update_layout(height=500)
        graph_correlacion = fig_corr.to_html()
    else:
        graph_correlacion = None
    
    # Gráfico 8: Clasificación HTA (Barras)
    fig_clasif = px.bar(
        x=[c['label'] for c in casos_por_clasificacion],
        y=[c['count'] for c in casos_por_clasificacion],
        title='Distribución por Clasificación de HTA',
        labels={'x': 'Clasificación', 'y': 'Número de Casos'},
        color=[c['count'] for c in casos_por_clasificacion],
        color_continuous_scale='Reds'
    )
    fig_clasif.update_layout(height=400, xaxis_tickangle=-45)
    graph_clasificacion = fig_clasif.to_html()
    
    # ============================================
    # 13. PREPARAR CONTEXTO PARA LA PLANTILLA
    # ============================================
    context = {
        # Métricas generales
        'total_casos': total_casos,
        'total_enfermedades': total_enfermedades,
        'total_sintomas': total_sintomas,
        'total_factores': total_factores,
        'total_protocolos': total_protocolos,
        
        # Métricas de resultados
        'casos_exitosos': casos_exitosos,
        'casos_no_controlados': casos_no_controlados,
        'casos_mejoria': casos_mejoria,
        'tasa_exito': tasa_exito,
        
        # Riesgo cardiovascular
        'casos_por_riesgo': casos_por_riesgo,
        
        # Clasificación HTA
        'casos_por_clasificacion': casos_por_clasificacion,
        
        # Estadísticas de edad
        'edad_min': edad_stats['edad_min'],
        'edad_max': edad_stats['edad_max'],
        'edad_promedio': round(edad_stats['edad_promedio'], 1) if edad_stats['edad_promedio'] else 0,
        'distribucion_edad': distribucion_edad,
        
        # Estadísticas de presión
        'presion_stats': presion_stats,
        
        # Top lists
        'top_enfermedades': top_enfermedades,
        'top_sintomas': top_sintomas,
        'top_factores': top_factores,
        
        # Datos para gráficos
        'graph_riesgo': graph_riesgo,
        'graph_edad': graph_edad,
        'graph_enfermedades': graph_enfermedades,
        'graph_sintomas': graph_sintomas,
        'graph_temporal': graph_temporal,
        'graph_sexo': graph_sexo,
        'graph_correlacion': graph_correlacion,
        'graph_clasificacion': graph_clasificacion,
        
        # JSON para JavaScript
        'riesgo_labels_json': json.dumps(riesgo_labels),
        'riesgo_data_json': json.dumps(riesgo_counts),
        'edad_labels_json': json.dumps([d['rango'] for d in distribucion_edad]),
        'edad_data_json': json.dumps([d['count'] for d in distribucion_edad]),
    }
    
    return render(request, 'diagnosticos/estadisticas.html', context)


def caso_detail_view(request, caso_id):
    """Vista detallada de un caso"""
    caso = get_object_or_404(CasoClinico, id=caso_id)
    sintomas_detalle = caso.detallesintomacaso_set.all().select_related('sintoma')
    resumen_ia = nlp.generar_resumen(caso)
    
    context = {
        'caso': caso,
        'sintomas_detalle': sintomas_detalle,
        'resumen_ia': resumen_ia,
    }
    return render(request, 'diagnosticos/caso_detail.html', context)

def dashboard_predictivo_view(request):
    """
    Vista del dashboard de IA predictiva
    Muestra predicciones y estadísticas del modelo ML
    """
    print("\n" + "="*60)
    print("📊 ACCEDIENDO AL DASHBOARD PREDICTIVO")
    print("="*60)
    
    # Inicializar predictor
    predictor = MLPredictor()
    
    # Entrenar modelo (o cargar existente)
    precision = predictor.entrenar()
    
    # Obtener importancia de características
    importancia = predictor.get_importancia_caracteristicas()
    
    # Obtener estadísticas del modelo
    stats = predictor.get_estadisticas_modelo()
    
    # Definir perfiles de prueba para predicciones
    perfiles_prueba = [
        {
            'nombre': 'Paciente Tipo A (Bajo Riesgo)',
            'edad': 35,
            'sexo': 'F',
            'sistolica': 115,
            'diastolica': 75,
            'sintomas': 1,
            'factores': 0,
            'descripcion': 'Mujer joven, sin factores de riesgo, PA normal'
        },
        {
            'nombre': 'Paciente Tipo B (Riesgo Moderado)',
            'edad': 50,
            'sexo': 'M',
            'sistolica': 135,
            'diastolica': 85,
            'sintomas': 2,
            'factores': 1,
            'descripcion': 'Hombre de mediana edad, fumador, PA normal-alta'
        },
        {
            'nombre': 'Paciente Tipo C (Riesgo Alto)',
            'edad': 65,
            'sexo': 'M',
            'sistolica': 155,
            'diastolica': 95,
            'sintomas': 3,
            'factores': 2,
            'descripcion': 'Adulto mayor, hipertenso, múltiples factores de riesgo'
        },
        {
            'nombre': 'Paciente Tipo D (Riesgo Muy Alto)',
            'edad': 72,
            'sexo': 'F',
            'sistolica': 175,
            'diastolica': 105,
            'sintomas': 4,
            'factores': 3,
            'descripcion': 'Adulto mayor, HTA severa, múltiples comorbilidades'
        },
    ]
    
    # Generar predicciones para cada perfil
    predicciones = []
    for perfil in perfiles_prueba:
        datos = {
            'edad': perfil['edad'],
            'sexo': 'M' if perfil['sexo'] == 'M' else 'F',
            'sistolica': perfil['sistolica'],
            'diastolica': perfil['diastolica'],
            'sintomas_ids': list(range(perfil['sintomas'])),
            'factores_nombres': ['factor'] * perfil['factores']
        }
        
        resultado = predictor.predecir(datos)
        
        # Determinar color según riesgo
        color = 'success'
        if resultado['riesgo'] == 'MODERADO':
            color = 'warning'
        elif resultado['riesgo'] == 'ALTO':
            color = 'danger'
        elif resultado['riesgo'] == 'MUY_ALTO':
            color = 'dark'
        
        predicciones.append({
            'perfil': perfil,
            'resultado': resultado,
            'color': color,
            'probabilidades_json': json.dumps(resultado.get('probabilidades', {}))
        })
    
    # Estadísticas generales
    total_casos = CasoClinico.objects.count()
    casos_por_riesgo = {
        'BAJO': CasoClinico.objects.filter(riesgo_cv='BAJO').count(),
        'MODERADO': CasoClinico.objects.filter(riesgo_cv='MODERADO').count(),
        'ALTO': CasoClinico.objects.filter(riesgo_cv='ALTO').count(),
        'MUY_ALTO': CasoClinico.objects.filter(riesgo_cv='MUY_ALTO').count(),
    }
    
    # Últimos casos para la tabla
    ultimos_casos = CasoClinico.objects.all().order_by('-fecha_registro')[:5]
    
    context = {
        'titulo': 'IA Predictiva - Diagnos.IA',
        'precision_modelo': round(precision * 100, 1) if precision else 0,
        'importancia': importancia,
        'predicciones': predicciones,
        'total_casos': total_casos,
        'casos_por_riesgo': casos_por_riesgo,
        'ultimos_casos': ultimos_casos,
        'stats': stats,
        'modelo_entrenado': stats['entrenado'],
        'fecha_entrenamiento': stats['fecha_ultimo_entrenamiento'],
    }
    
    return render(request, 'diagnosticos/dashboard_predictivo.html', context)