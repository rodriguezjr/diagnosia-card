# diagnosticos/management/commands/poblar_datos.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from diagnosticos.models import (
    Enfermedad, Sintoma, FactorRiesgo, ProtocoloClinico,
    CasoClinico, DetalleSintomaCaso, ReglaConocimiento
)
from datetime import date

class Command(BaseCommand):
    help = 'Pobla la base de datos con datos iniciales'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🌱 Poblando base de datos...'))
        
        # 1. Crear o obtener usuario admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@diagnosia.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('  ✅ Usuario admin creado (admin/admin123)')
        else:
            self.stdout.write('  ℹ️ Usuario admin ya existe')
        
        # 2. Enfermedades (usando get_or_create para evitar duplicados)
        enfermedades_data = [
            {'nombre': 'Hipertensión Arterial Esencial', 'codigo_cie10': 'I10'},
            {'nombre': 'Hipertensión Arterial Secundaria', 'codigo_cie10': 'I15'},
            {'nombre': 'Cardiopatía Hipertensiva', 'codigo_cie10': 'I11'},
        ]
        
        enfermedades = {}
        for e_data in enfermedades_data:
            obj, created = Enfermedad.objects.get_or_create(
                nombre=e_data['nombre'],
                defaults={'codigo_cie10': e_data['codigo_cie10']}
            )
            enfermedades[e_data['nombre']] = obj
            if created:
                self.stdout.write(f'  ✅ Enfermedad creada: {e_data["nombre"]}')
            else:
                self.stdout.write(f'  ℹ️ Enfermedad ya existe: {e_data["nombre"]}')
        
        # 3. Síntomas
        sintomas_data = [
            {'nombre': 'Cefalea occipital', 'categoria': 'NEUROLOGICO'},
            {'nombre': 'Mareos', 'categoria': 'NEUROLOGICO'},
            {'nombre': 'Palpitaciones', 'categoria': 'GENERAL'},
            {'nombre': 'Dolor torácico', 'categoria': 'DOLOR'},
            {'nombre': 'Disnea de esfuerzo', 'categoria': 'RESPIRATORIO'},
            {'nombre': 'Visión borrosa', 'categoria': 'NEUROLOGICO'},
            {'nombre': 'Acúfenos', 'categoria': 'NEUROLOGICO'},
            {'nombre': 'Edema en miembros inferiores', 'categoria': 'GENERAL'},
            {'nombre': 'Fatiga', 'categoria': 'GENERAL'},
            {'nombre': 'Náuseas', 'categoria': 'GENERAL'},
        ]
        
        sintomas = {}
        for s_data in sintomas_data:
            obj, created = Sintoma.objects.get_or_create(
                nombre=s_data['nombre'],
                defaults={'categoria': s_data['categoria']}
            )
            sintomas[s_data['nombre']] = obj
            if created:
                self.stdout.write(f'  ✅ Síntoma creado: {s_data["nombre"]}')
        
        # 4. Factores de riesgo
        factores_data = [
            {'nombre': 'Edad > 65 años', 'categoria': 'NO_MODIFICABLE', 'descripcion': 'Edad avanzada'},
            {'nombre': 'Sexo masculino', 'categoria': 'NO_MODIFICABLE', 'descripcion': 'Sexo masculino'},
            {'nombre': 'Antecedentes familiares', 'categoria': 'NO_MODIFICABLE', 'descripcion': 'Historia familiar de HTA'},
            {'nombre': 'Tabaquismo', 'categoria': 'MODIFICABLE', 'descripcion': 'Consumo de tabaco'},
            {'nombre': 'Obesidad', 'categoria': 'MODIFICABLE', 'descripcion': 'IMC > 30'},
            {'nombre': 'Sedentarismo', 'categoria': 'MODIFICABLE', 'descripcion': 'Falta de actividad física'},
            {'nombre': 'Diabetes', 'categoria': 'MODIFICABLE', 'descripcion': 'Diabetes mellitus'},
            {'nombre': 'Dislipidemia', 'categoria': 'MODIFICABLE', 'descripcion': 'Colesterol alto'},
        ]
        
        factores = {}
        for f_data in factores_data:
            obj, created = FactorRiesgo.objects.get_or_create(
                nombre=f_data['nombre'],
                defaults={
                    'categoria': f_data['categoria'],
                    'descripcion': f_data['descripcion']
                }
            )
            factores[f_data['nombre']] = obj
            if created:
                self.stdout.write(f'  ✅ Factor de riesgo creado: {f_data["nombre"]}')
        
        # 5. Protocolos clínicos
        protocolos_data = [
            {
                'titulo': 'Manejo de HTA Grado 1 sin complicaciones',
                'fuente': 'Guía ESC/ESH 2018',
                'nivel_evidencia': 'A',
                'indicaciones': 'Iniciar cambios en estilo de vida (dieta baja en sodio, ejercicio regular, pérdida de peso). Evaluar en 3 meses. Si persiste >140/90, iniciar tratamiento farmacológico con IECA o ARA-II.',
                'contraindicaciones': 'Hipersensibilidad a IECA, embarazo',
                'fecha_publicacion': '2018-08-25'
            },
            {
                'titulo': 'Manejo de HTA Grado 2',
                'fuente': 'Guía AHA 2020',
                'nivel_evidencia': 'A',
                'indicaciones': 'Iniciar tratamiento farmacológico combinado (IECA + Calcioantagonista o diurético tiazídico). Evaluar cada 2-4 semanas hasta control.',
                'contraindicaciones': 'Insuficiencia renal severa, hiperkalemia',
                'fecha_publicacion': '2020-05-15'
            },
            {
                'titulo': 'Manejo de crisis hipertensiva',
                'fuente': 'Guía ESC 2018',
                'nivel_evidencia': 'B',
                'indicaciones': 'Hospitalización. Reducir PA gradualmente (máx 25% en primeras 2h). Evitar descensos bruscos. Monitoreo continuo.',
                'contraindicaciones': 'Hipotensión, shock',
                'fecha_publicacion': '2018-08-25'
            },
        ]
        
        protocolos = {}
        for p_data in protocolos_data:
            obj, created = ProtocoloClinico.objects.get_or_create(
                titulo=p_data['titulo'],
                defaults={
                    'fuente': p_data['fuente'],
                    'nivel_evidencia': p_data['nivel_evidencia'],
                    'indicaciones': p_data['indicaciones'],
                    'contraindicaciones': p_data['contraindicaciones'],
                    'fecha_publicacion': p_data['fecha_publicacion'],
                }
            )
            protocolos[p_data['titulo']] = obj
            if created:
                self.stdout.write(f'  ✅ Protocolo creado: {p_data["titulo"]}')
        
        # 6. Reglas de conocimiento
        protocolo_g1 = protocolos.get('Manejo de HTA Grado 1 sin complicaciones')
        protocolo_g2 = protocolos.get('Manejo de HTA Grado 2')
        protocolo_crisis = protocolos.get('Manejo de crisis hipertensiva')
        
        if protocolo_g1 and protocolo_g2 and protocolo_crisis:
            reglas_data = [
                {
                    'condicion': 'sistolica >= 140 and sistolica < 160 and diastolica >= 90 and diastolica < 100',
                    'recomendacion': 'Paciente con HTA Grado 1. Iniciar cambios en estilo de vida y reevaluar en 3 meses.',
                    'protocolo': protocolo_g1,
                    'prioridad': 2
                },
                {
                    'condicion': 'sistolica >= 160 and sistolica < 180 and diastolica >= 100 and diastolica < 110',
                    'recomendacion': 'Paciente con HTA Grado 2. Iniciar tratamiento farmacológico combinado.',
                    'protocolo': protocolo_g2,
                    'prioridad': 2
                },
                {
                    'condicion': 'sistolica >= 180 or diastolica >= 110',
                    'recomendacion': '¡ALERTA! Posible crisis hipertensiva. Requiere evaluación inmediata.',
                    'protocolo': protocolo_crisis,
                    'prioridad': 1
                },
            ]
            
            for r_data in reglas_data:
                obj, created = ReglaConocimiento.objects.get_or_create(
                    condicion=r_data['condicion'],
                    defaults={
                        'recomendacion': r_data['recomendacion'],
                        'protocolo': r_data['protocolo'],
                        'prioridad': r_data['prioridad']
                    }
                )
                if created:
                    self.stdout.write(f'  ✅ Regla creada: {r_data["condicion"][:30]}...')
        
        # 7. Casos clínicos de ejemplo
        if CasoClinico.objects.count() == 0:  # Solo crear si no hay casos
            sintoma_cefalea = sintomas.get('Cefalea occipital')
            sintoma_mareos = sintomas.get('Mareos')
            sintoma_palpitaciones = sintomas.get('Palpitaciones')
            sintoma_disnea = sintomas.get('Disnea de esfuerzo')
            
            factor_tabaquismo = factores.get('Tabaquismo')
            factor_edad = factores.get('Edad > 65 años')
            factor_obesidad = factores.get('Obesidad')
            factor_diabetes = factores.get('Diabetes')
            
            diagnostico = enfermedades.get('Hipertensión Arterial Esencial')
            
            casos_data = [
                {
                    'edad': 55, 'sexo': 'M',
                    'sistolica': 145, 'diastolica': 95,
                    'clasificacion': 'GRADO_1',
                    'riesgo': 'MODERADO',
                    'sintomas': [sintoma_cefalea, sintoma_mareos],
                    'factores': [factor_tabaquismo, factor_obesidad],
                    'protocolo': protocolo_g1,
                },
                {
                    'edad': 68, 'sexo': 'F',
                    'sistolica': 162, 'diastolica': 98,
                    'clasificacion': 'GRADO_2',
                    'riesgo': 'ALTO',
                    'sintomas': [sintoma_cefalea, sintoma_palpitaciones],
                    'factores': [factor_edad, factor_diabetes],
                    'protocolo': protocolo_g2,
                },
                {
                    'edad': 72, 'sexo': 'M',
                    'sistolica': 185, 'diastolica': 110,
                    'clasificacion': 'GRADO_3',
                    'riesgo': 'MUY_ALTO',
                    'sintomas': [sintoma_cefalea, sintoma_disnea],
                    'factores': [factor_edad, factor_tabaquismo],
                    'protocolo': protocolo_crisis,
                },
            ]
            
            for c_data in casos_data:
                caso = CasoClinico.objects.create(
                    edad=c_data['edad'],
                    sexo=c_data['sexo'],
                    presion_sistolica=c_data['sistolica'],
                    presion_diastolica=c_data['diastolica'],
                    clasificacion_hta=c_data['clasificacion'],
                    riesgo_cv=c_data['riesgo'],
                    diagnostico=diagnostico,
                    protocolo_aplicado=c_data['protocolo'],
                    resultado='CONTROLADO',
                    creado_por=admin
                )
                
                # Agregar síntomas
                for sintoma in c_data['sintomas']:
                    if sintoma:
                        DetalleSintomaCaso.objects.create(
                            caso=caso,
                            sintoma=sintoma,
                            intensidad=2
                        )
                
                # Agregar factores de riesgo
                for factor in c_data['factores']:
                    if factor:
                        caso.factores_riesgo.add(factor)
                
                self.stdout.write(f'  ✅ Caso clínico creado: PA {c_data["sistolica"]}/{c_data["diastolica"]}')
        else:
            self.stdout.write('  ℹ️ Ya existen casos clínicos, no se crean nuevos')
        
        self.stdout.write(self.style.SUCCESS('✨ ¡Base de datos poblada exitosamente!'))