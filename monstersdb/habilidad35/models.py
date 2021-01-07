from django.db import models

class Habilidad(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    caracteristica_asociada = models.CharField(max_length=200)
    entrenada = models.CharField(max_length=200, null=True)
    penalizador_de_armadura = models.CharField(max_length=200, null=True)

    descripcion = models.CharField(max_length=20000)

    chequeos_epicos = models.CharField(max_length=200, null=True)
    tipo_de_accion = models.CharField(max_length=200, null=True)
    reintentos = models.CharField(max_length=200, null=True)
    especial = models.CharField(max_length=200, null=True)
    sinergias = models.CharField(max_length=200, null=True)
    restricciones = models.CharField(max_length=200, null=True)
    desentrenada = models.CharField(max_length=200, null=True)