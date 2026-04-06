from django.contrib import admin

# Register your models here.

# diagnosticos/admin.py

from .models import *

@admin.register(Enfermedad)
class EnfermedadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo_cie10']
    search_fields = ['nombre']

@admin.register(Sintoma)
class SintomaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria']
    list_filter = ['categoria']

@admin.register(FactorRiesgo)
class FactorRiesgoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria']
    list_filter = ['categoria']

@admin.register(ProtocoloClinico)
class ProtocoloClinicoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fuente', 'nivel_evidencia']
    list_filter = ['nivel_evidencia']

class DetalleSintomaCasoInline(admin.TabularInline):
    model = DetalleSintomaCaso
    extra = 1

@admin.register(CasoClinico)
class CasoClinicoAdmin(admin.ModelAdmin):
    list_display = ['edad', 'sexo', 'presion_sistolica', 'presion_diastolica', 'clasificacion_hta']
    list_filter = ['clasificacion_hta', 'riesgo_cv']
    filter_horizontal = ['factores_riesgo']
    inlines = [DetalleSintomaCasoInline]

@admin.register(ReglaConocimiento)
class ReglaConocimientoAdmin(admin.ModelAdmin):
    list_display = ['condicion', 'prioridad', 'activa']
    list_filter = ['activa', 'prioridad']