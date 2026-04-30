from django.urls import path, re_path
from . import views, views_pagos, views_comprobantes, views_admin

app_name = 'academia'

# Las URLs de cursos y matrícula reciben la modalidad como parte del path:
#   /matricula/presencial/...
#   /matricula/online/...
#   /cursos/presencial/
#   /cursos/online/

urlpatterns = [
    path('bienvenida/', views.bienvenida, name='bienvenida'),

    # ── Ayuda ──────────────────────────────────────────────────
    path('ayuda/', views.ayuda, name='ayuda'),

    # ── Matrícula (presencial u online) ────────────────────────
    path('matricula/<str:modalidad>/',
         views.matricula_menu, name='matricula_menu'),
    path('matricula/<str:modalidad>/registrar/',
         views.matricula_registrar, name='matricula_registrar'),
    path('matricula/<str:modalidad>/lista/',
         views.matricula_lista, name='matricula_lista'),
    path('matricula/<str:modalidad>/editar/<int:pk>/',
         views.matricula_editar, name='matricula_editar'),
    path('matricula/<str:modalidad>/eliminar/<int:pk>/',
         views.matricula_eliminar, name='matricula_eliminar'),

    # ── Cursos: rutas específicas ANTES del catch-all de modalidad ──
    # (Si no, /cursos/crear/ haría match con modalidad='crear')
    path('cursos/crear/', views.curso_crear, name='curso_crear'),
    path('cursos/<int:pk>/editar/', views.curso_editar, name='curso_editar'),
    path('cursos/<int:pk>/eliminar/', views.curso_eliminar, name='curso_eliminar'),
    path('cursos/<int:pk>/jornadas/', views.curso_jornadas, name='curso_jornadas'),
    path('cursos/<int:pk>/jornadas/eliminar/<int:jornada_pk>/',
         views.jornada_eliminar, name='jornada_eliminar'),

    # ── Cursos: lista por modalidad (catch-all, va al final) ────────
    path('cursos/<str:modalidad>/',
         views.cursos_lista, name='cursos_lista'),

    # ── Pagos ──────────────────────────────────────────────────
    path('pagos/', views_pagos.pagos_lista, name='pagos_lista'),
    path('pagos/exportar/', views_pagos.pagos_export, name='pagos_export'),

    # ── Abonos (sistema de pagos por matrícula) ───────────────
    path('matricula/<int:pk>/abonos/',
         views_pagos.matricula_abonos, name='matricula_abonos'),
    path('matricula/<int:matricula_pk>/abonos/crear/',
         views_pagos.abono_crear, name='abono_crear'),
    path('matricula/<int:matricula_pk>/abonos/<int:abono_pk>/editar/',
         views_pagos.abono_editar, name='abono_editar'),
    path('matricula/<int:matricula_pk>/abonos/<int:abono_pk>/eliminar/',
         views_pagos.abono_eliminar, name='abono_eliminar'),
    path('abonos/exportar/', views_pagos.abonos_export, name='abonos_export'),
    path('abonos/<int:abono_pk>/recibo/',
         views_pagos.abono_recibo, name='abono_recibo'),

    # ── Historial de matriculados ──────────────────────────────
    path('historial/', views_pagos.historial_lista, name='historial_lista'),
    path('historial/exportar/', views_pagos.historial_export, name='historial_export'),

    # ── Estudiantes ───────────────────────────────────────────
    path('estudiantes/', views_pagos.estudiantes_lista, name='estudiantes_lista'),
    path('estudiantes/por-curso/', views_pagos.estudiantes_por_curso, name='estudiantes_por_curso'),
    path('estudiantes/exportar/', views_pagos.estudiantes_export, name='estudiantes_export'),
    path('estudiantes/<int:pk>/', views_pagos.estudiante_detalle, name='estudiante_detalle'),
    path('estudiantes/<int:pk>/exportar/', views_pagos.estudiante_export, name='estudiante_export'),

    # ── Comprobantes de Venta ─────────────────────────────────
    path('comprobantes/', views_comprobantes.comprobante_menu, name='comprobante_menu'),
    path('comprobantes/registrar/', views_comprobantes.comprobante_registrar, name='comprobante_registrar'),
    path('comprobantes/lista/', views_comprobantes.comprobante_lista, name='comprobante_lista'),
    path('comprobantes/totales/', views_comprobantes.comprobante_totales, name='comprobante_totales'),
    path('comprobantes/<int:pk>/editar/', views_comprobantes.comprobante_editar, name='comprobante_editar'),
    path('comprobantes/<int:pk>/eliminar/', views_comprobantes.comprobante_eliminar, name='comprobante_eliminar'),

    # ── Endpoints AJAX ─────────────────────────────────────────
    path('api/curso/<int:pk>/', views.api_curso_detalle, name='api_curso_detalle'),
    path('api/curso/<int:pk>/jornadas/',
         views.api_curso_jornadas, name='api_curso_jornadas'),
    path('api/categoria/crear/',
         views.api_categoria_crear, name='api_categoria_crear'),

    # ── Registro Administrativo ────────────────────────────────
    path('admin-panel/',
         views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/egresos/',
         views_admin.egresos_lista, name='admin_egresos_lista'),
    path('admin-panel/egresos/nuevo/',
         views_admin.egreso_crear, name='admin_egreso_crear'),
    path('admin-panel/egresos/<int:pk>/editar/',
         views_admin.egreso_editar, name='admin_egreso_editar'),
    path('admin-panel/egresos/<int:pk>/eliminar/',
         views_admin.egreso_eliminar, name='admin_egreso_eliminar'),

    # ── Exportación CSV ───────────────────────────────────────
    path('admin-panel/export/reporte/',
         views_admin.export_reporte_mes, name='admin_export_reporte'),
    path('admin-panel/export/egresos/',
         views_admin.export_egresos, name='admin_export_egresos'),
]