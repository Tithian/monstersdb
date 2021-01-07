from django.db import models

class Dote(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.CharField(max_length=200)
    requisito = models.CharField(max_length=200, null=True)
    normal = models.CharField(max_length=200, null=True)
    especial = models.CharField(max_length=200, null=True)