from django.db import models

# Create your models here.

from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class Enfermedad(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True)
    codigo_cie10 = models.CharField(max_length=10, blank=True)
    
    class Meta:
        verbose_name = "Enfermedad"
        verbose_name_plural = "Enfermedades"
    
    def __str__(self):
        return self.nombre

class Sintoma(models.Model):
    CATEGORIAS = [
        ('DOLOR', 'Dolor'),
        ('RESPIRATORIO', 'Respiratorio'),
        ('NEUROLOGICO', 'Neurológico'),
        ('GENERAL', 'General'),
    ]
    
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='GENERAL')
    
    class Meta:
        verbose_name = "Síntoma"
        verbose_name_plural = "Síntomas"
    
    def __str__(self):
        return self.nombre

class FactorRiesgo(models.Model):
    CATEGORIAS = [
        ('MODIFICABLE', 'Modificable'),
        ('NO_MODIFICABLE', 'No Modificable'),
    ]
    
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    
    def __str__(self):
        return self.nombre

class ProtocoloClinico(models.Model):
    NIVEL_EVIDENCIA = [
        ('A', 'Alta'),
        ('B', 'Moderada'),
        ('C', 'Baja'),
    ]
    
    titulo = models.CharField(max_length=300)
    fuente = models.CharField(max_length=200)
    nivel_evidencia = models.CharField(max_length=1, choices=NIVEL_EVIDENCIA)
    indicaciones = models.TextField()
    contraindicaciones = models.TextField(blank=True)
    fecha_publicacion = models.DateField()
    
    def __str__(self):
        return f"{self.titulo}"

class CasoClinico(models.Model):
    CLASIFICACION_HTA = [
        ('OPTIMA', 'Óptima (<120/80)'),
        ('NORMAL', 'Normal (120-129/80-84)'),
        ('NORMAL_ALTA', 'Normal-alta (130-139/85-89)'),
        ('GRADO_1', 'Grado 1 (140-159/90-99)'),
        ('GRADO_2', 'Grado 2 (160-179/100-109)'),
        ('GRADO_3', 'Grado 3 (≥180/110)'),
    ]
    
    RIESGO_CV = [
        ('BAJO', 'Bajo'),
        ('MODERADO', 'Moderado'),
        ('ALTO', 'Alto'),
        ('MUY_ALTO', 'Muy alto'),
    ]
    
    RESULTADOS = [
        ('CONTROLADO', 'Controlado'),
        ('NO_CONTROLADO', 'No controlado'),
        ('MEJORIA', 'Mejoría'),
    ]
    
    edad = models.IntegerField(validators=[MinValueValidator(18), MaxValueValidator(120)])
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    presion_sistolica = models.IntegerField()
    presion_diastolica = models.IntegerField()
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True)
    
    factores_riesgo = models.ManyToManyField(FactorRiesgo, blank=True)
    sintomas = models.ManyToManyField(Sintoma, through='DetalleSintomaCaso')
    
    clasificacion_hta = models.CharField(max_length=20, choices=CLASIFICACION_HTA)
    riesgo_cv = models.CharField(max_length=20, choices=RIESGO_CV)
    diagnostico = models.ForeignKey(Enfermedad, on_delete=models.PROTECT)
    protocolo_aplicado = models.ForeignKey(ProtocoloClinico, on_delete=models.PROTECT)
    resultado = models.CharField(max_length=20, choices=RESULTADOS)
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Paciente {self.edad}a - PA:{self.presion_sistolica}/{self.presion_diastolica}"

class DetalleSintomaCaso(models.Model):
    INTENSIDAD = [(1, 'Leve'), (2, 'Moderado'), (3, 'Severo')]
    
    caso = models.ForeignKey(CasoClinico, on_delete=models.CASCADE)
    sintoma = models.ForeignKey(Sintoma, on_delete=models.CASCADE)
    intensidad = models.IntegerField(choices=INTENSIDAD, default=2)
    observaciones = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = ['caso', 'sintoma']

class ReglaConocimiento(models.Model):
    condicion = models.TextField()
    recomendacion = models.TextField()
    protocolo = models.ForeignKey(ProtocoloClinico, on_delete=models.CASCADE)
    prioridad = models.IntegerField(default=1)
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Regla: {self.condicion[:50]}..."