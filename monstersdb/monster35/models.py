from django.db import models

class Monstruo(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    tipo = models.CharField(max_length=200)
    subtipo = models.CharField(max_length=200, null=True)
    tamaño = models.CharField(max_length=200)

    dg_pv = models.CharField(max_length=200)

    iniciativa = models.CharField(max_length=200, default=0)

    velocidad = models.CharField(max_length=200)

    ca = models.CharField(max_length=200)

    ataquebase_presa = models.CharField(max_length=200)

    ataque = models.CharField(max_length=200)

    ataque_completo = models.CharField(max_length=200)

    espacio_alcance = models.CharField(max_length=200)

    ataques_especiales = models.CharField(max_length=200)

    cualidades_especiales = models.CharField(max_length=200)

    salvaciones = models.CharField(max_length=200), \
                  models.CharField(max_length=200), \
                  models.CharField(max_length=200)

    caracteristicas =   models.CharField(max_length=200),\
                        models.CharField(max_length=200),\
                        models.CharField(max_length=200),\
                        models.CharField(max_length=200),\
                        models.CharField(max_length=200),\
                        models.CharField(max_length=200)

    habilidades = models.CharField(max_length=1200)

    dotes = models.CharField(max_length=200)

    entorno = models.CharField(max_length=200)

    organizacion = models.CharField(max_length=200)

    vd = models.CharField(max_length=200)

    tesoro = models.CharField(max_length=200)

    alineamiento = models.CharField(max_length=200)

    avance = models.CharField(max_length=200)

    ajuste_de_nivel = models.CharField(max_length=200)

    descripcion = models.CharField(max_length=20000)

    combate = models.CharField(max_length=20000)

