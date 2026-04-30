from django.contrib import admin
from .models import Categoria, Comprobante, Curso, JornadaCurso, Estudiante, Matricula


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'color', 'activo', 'cantidad_cursos')
    list_editable = ('orden', 'activo')
    search_fields = ('nombre',)

    def cantidad_cursos(self, obj):
        return obj.cursos.count()
    cantidad_cursos.short_description = '# cursos'


class JornadaCursoInline(admin.TabularInline):
    model = JornadaCurso
    extra = 1
    fields = ('modalidad', 'descripcion', 'fecha_inicio', 'hora_inicio', 'hora_fin', 'ciudad', 'activo')


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'categoria',
        'ofrece_presencial', 'valor_presencial',
        'ofrece_online', 'valor_online',
        'duracion', 'activo',
    )
    list_filter = ('categoria', 'activo', 'ofrece_presencial', 'ofrece_online')
    search_fields = ('nombre',)
    autocomplete_fields = ('categoria',)
    inlines = [JornadaCursoInline]
    fieldsets = (
        (None, {
            'fields': ('categoria', 'nombre', 'descripcion', 'duracion', 'activo'),
        }),
        ('Modalidad presencial', {
            'fields': ('ofrece_presencial', 'valor_presencial'),
        }),
        ('Modalidad online', {
            'fields': ('ofrece_online', 'valor_online'),
        }),
        ('Legado (no usar)', {
            'classes': ('collapse',),
            'fields': ('valor',),
            'description': 'Campo antiguo conservado por compatibilidad. Usa los valores por modalidad.',
        }),
    )


@admin.register(JornadaCurso)
class JornadaCursoAdmin(admin.ModelAdmin):
    list_display = (
        'curso', 'modalidad', 'descripcion', 'fecha_inicio',
        'hora_inicio', 'hora_fin', 'ciudad', 'activo',
    )
    list_filter = ('modalidad', 'activo', 'ciudad', 'curso')
    search_fields = ('curso__nombre', 'descripcion', 'ciudad')


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = (
        'cedula', 'apellidos', 'nombres', 'edad',
        'correo', 'celular', 'ciudad', 'nivel_formacion',
    )
    search_fields = ('cedula', 'apellidos', 'nombres', 'correo')
    list_filter = ('nivel_formacion', 'ciudad')


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_matricula', 'estudiante', 'curso', 'jornada',
        'modalidad', 'valor_curso', 'valor_pagado', 'estado_pago',
        'registrado_por',
    )
    list_filter = ('modalidad', 'curso', 'fecha_matricula', 'talla_camiseta', 'registrado_por')
    search_fields = (
        'estudiante__cedula', 'estudiante__apellidos',
        'estudiante__nombres', 'curso__nombre',
    )
    autocomplete_fields = ('estudiante', 'curso', 'jornada')
    readonly_fields = ('registrado_por', 'creado', 'actualizado')


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_inscripcion', 'nombre_persona', 'curso',
        'modalidad', 'tipo_registro', 'pago_abono', 'diferencia',
        'vendedora_nombre', 'factura_realizada',
    )
    list_filter = ('modalidad', 'tipo_registro', 'factura_realizada', 'curso', 'vendedora')
    search_fields = (
        'nombre_persona', 'celular',
        'fact_nombres', 'fact_apellidos', 'fact_cedula', 'fact_correo',
        'curso__nombre',
    )
    autocomplete_fields = ('curso',)
    readonly_fields = ('vendedora_nombre', 'creado', 'actualizado')
    fieldsets = (
        ('Datos del curso', {
            'fields': ('curso', 'modalidad', 'jornada', 'inicio_curso',
                       'fecha_inscripcion'),
        }),
        ('Datos del cliente', {
            'fields': ('nombre_persona', 'celular'),
        }),
        ('Pago y Registro', {
            'fields': ('tipo_registro', 'pago_abono', 'diferencia'),
        }),
        ('Vendedora', {
            'fields': ('vendedora', 'vendedora_nombre'),
        }),
        ('Factura', {
            'fields': ('factura_realizada', 'fact_nombres', 'fact_apellidos',
                       'fact_cedula', 'fact_correo'),
        }),
        ('Auditoría', {
            'classes': ('collapse',),
            'fields': ('creado', 'actualizado'),
        }),
    )