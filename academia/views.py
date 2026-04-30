import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    CategoriaForm, CursoForm, EstudianteForm,
    JornadaCursoForm, MatriculaForm,
)
from .models import Categoria, Curso, Estudiante, JornadaCurso, Matricula
from .permisos import admin_requerido, matricula_requerida


# ─────────────────────────────────────────────────────────
# Helpers de modalidad
# ─────────────────────────────────────────────────────────

MODALIDADES_VALIDAS = ('presencial', 'online')

# Mientras se vincula con Google Forms, la matrícula online está deshabilitada.
# Los CURSOS online siguen visibles. Solo se bloquea el flujo de matrícula online.
MATRICULA_ONLINE_HABILITADA = False


def _modalidad_o_404(modalidad):
    """Valida que la modalidad de la URL sea válida; si no, lanza 404."""
    if modalidad not in MODALIDADES_VALIDAS:
        from django.http import Http404
        raise Http404(f'Modalidad desconocida: {modalidad}')
    return modalidad


def _bloquear_si_online(request, modalidad):
    """
    Si la matrícula online está deshabilitada y se intenta acceder a esa modalidad,
    muestra mensaje y redirige al dashboard. Devuelve None si todo OK.
    """
    if modalidad == 'online' and not MATRICULA_ONLINE_HABILITADA:
        messages.info(
            request,
            'La matrícula online está temporalmente deshabilitada en el sistema. '
            'Disponible próximamente vía Google Forms.'
        )
        return redirect('academia:bienvenida')
    return None


def _label_modalidad(modalidad):
    return 'Presencial' if modalidad == 'presencial' else 'Online'


# ─────────────────────────────────────────────────────────
# Páginas base
# ─────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('academia:bienvenida')
    return redirect('login')


@login_required
def bienvenida(request):
    # Estadísticas rápidas para mostrar en el dashboard
    stats = {
        'total_presencial': Matricula.objects.filter(modalidad='presencial').count(),
        'total_online': Matricula.objects.filter(modalidad='online').count(),
        'total_cursos_presencial': Curso.objects.filter(activo=True, ofrece_presencial=True).count(),
        'total_cursos_online': Curso.objects.filter(activo=True, ofrece_online=True).count(),
    }
    return render(request, 'bienvenida.html', {
        'usuario': request.user,
        'stats': stats,
    })


# ─────────────────────────────────────────────────────────
# Matrícula (presencial u online — parametrizado por URL)
# ─────────────────────────────────────────────────────────

@matricula_requerida
def matricula_menu(request, modalidad):
    modalidad = _modalidad_o_404(modalidad)
    bloqueo = _bloquear_si_online(request, modalidad)
    if bloqueo:
        return bloqueo
    total = Matricula.objects.filter(modalidad=modalidad).count()
    return render(request, 'matricula/menu.html', {
        'total': total,
        'modalidad': modalidad,
        'modalidad_label': _label_modalidad(modalidad),
    })


@matricula_requerida
@transaction.atomic
def matricula_registrar(request, modalidad):
    modalidad = _modalidad_o_404(modalidad)
    bloqueo = _bloquear_si_online(request, modalidad)
    if bloqueo:
        return bloqueo

    if request.method == 'POST':
        est_form = EstudianteForm(request.POST, prefix='est')
        mat_form = MatriculaForm(request.POST, prefix='mat', modalidad=modalidad)

        cedula = request.POST.get('est-cedula', '').strip()
        estudiante_existente = None
        if cedula:
            estudiante_existente = Estudiante.objects.filter(cedula=cedula).first()

        if estudiante_existente:
            if mat_form.is_valid():
                matricula = mat_form.save(commit=False)
                matricula.estudiante = estudiante_existente
                matricula.modalidad = modalidad
                matricula.registrado_por = request.user
                matricula.save()
                messages.success(
                    request,
                    f'Matrícula {_label_modalidad(modalidad).lower()} registrada para '
                    f'{estudiante_existente.nombre_completo}.'
                )
                return redirect('academia:matricula_lista', modalidad=modalidad)
        else:
            if est_form.is_valid() and mat_form.is_valid():
                estudiante = est_form.save()
                matricula = mat_form.save(commit=False)
                matricula.estudiante = estudiante
                matricula.modalidad = modalidad
                matricula.registrado_por = request.user
                matricula.save()
                messages.success(
                    request,
                    f'Matrícula {_label_modalidad(modalidad).lower()} registrada para '
                    f'{estudiante.nombre_completo}.'
                )
                return redirect('academia:matricula_lista', modalidad=modalidad)

    else:
        est_form = EstudianteForm(prefix='est')
        mat_form = MatriculaForm(prefix='mat', modalidad=modalidad)

    return render(request, 'matricula/form.html', {
        'est_form': est_form,
        'mat_form': mat_form,
        'modalidad': modalidad,
        'modalidad_label': _label_modalidad(modalidad),
        'modo': 'registrar',
        'titulo': f'Registrar Matrícula {_label_modalidad(modalidad)}',
    })


@matricula_requerida
@transaction.atomic
def matricula_editar(request, modalidad, pk):
    modalidad = _modalidad_o_404(modalidad)
    matricula = get_object_or_404(Matricula, pk=pk, modalidad=modalidad)

    if request.method == 'POST':
        est_form = EstudianteForm(request.POST, prefix='est', instance=matricula.estudiante)
        mat_form = MatriculaForm(
            request.POST, prefix='mat', instance=matricula, modalidad=modalidad
        )
        if est_form.is_valid() and mat_form.is_valid():
            est_form.save()
            mat_form.save()
            messages.success(request, 'Matrícula actualizada correctamente.')
            return redirect('academia:matricula_lista', modalidad=modalidad)
    else:
        est_form = EstudianteForm(prefix='est', instance=matricula.estudiante)
        mat_form = MatriculaForm(
            prefix='mat', instance=matricula, modalidad=modalidad
        )

    return render(request, 'matricula/form.html', {
        'est_form': est_form,
        'mat_form': mat_form,
        'matricula': matricula,
        'modalidad': modalidad,
        'modalidad_label': _label_modalidad(modalidad),
        'modo': 'editar',
        'titulo': f'Editar Matrícula #{matricula.pk}',
    })


@matricula_requerida
def matricula_lista(request, modalidad):
    modalidad = _modalidad_o_404(modalidad)
    q = request.GET.get('q', '').strip()
    curso_id = request.GET.get('curso', '').strip()

    qs = (Matricula.objects
          .filter(modalidad=modalidad)
          .select_related('estudiante', 'curso', 'jornada', 'registrado_por'))

    if q:
        qs = qs.filter(
            Q(estudiante__cedula__icontains=q)
            | Q(estudiante__apellidos__icontains=q)
            | Q(estudiante__nombres__icontains=q)
            | Q(curso__nombre__icontains=q)
        )
    if curso_id:
        qs = qs.filter(curso_id=curso_id)

    # Cursos disponibles en esta modalidad para el filtro
    if modalidad == 'online':
        cursos_filtro = Curso.objects.filter(activo=True, ofrece_online=True)
    else:
        cursos_filtro = Curso.objects.filter(activo=True, ofrece_presencial=True)

    return render(request, 'matricula/lista.html', {
        'matriculas': qs,
        'cursos': cursos_filtro,
        'q': q,
        'curso_seleccionado': curso_id,
        'modalidad': modalidad,
        'modalidad_label': _label_modalidad(modalidad),
    })


@matricula_requerida
@require_POST
def matricula_eliminar(request, modalidad, pk):
    modalidad = _modalidad_o_404(modalidad)
    matricula = get_object_or_404(Matricula, pk=pk, modalidad=modalidad)
    matricula.delete()
    messages.success(request, 'Matrícula eliminada.')
    return redirect('academia:matricula_lista', modalidad=modalidad)


# ─────────────────────────────────────────────────────────
# Cursos y categorías (con tabs presencial/online)
# ─────────────────────────────────────────────────────────

@login_required
def cursos_lista(request, modalidad):
    """
    Lista cursos filtrados por modalidad. Solo muestra los que
    ofrecen la modalidad seleccionada.
    """
    modalidad = _modalidad_o_404(modalidad)

    # Filtro principal: cursos que ofrecen esta modalidad
    if modalidad == 'online':
        cursos_qs = Curso.objects.filter(ofrece_online=True)
    else:
        cursos_qs = Curso.objects.filter(ofrece_presencial=True)

    # Categorías: agrupa solo los cursos que ofrecen la modalidad
    categorias_lista = []
    for cat in Categoria.objects.filter(activo=True).order_by('orden', 'nombre'):
        cursos_cat = cursos_qs.filter(categoria=cat).order_by('nombre')
        categorias_lista.append({
            'obj': cat,
            'cursos': cursos_cat,
            'total': cursos_cat.count(),
        })

    sin_categoria = cursos_qs.filter(categoria__isnull=True)
    total_cursos = cursos_qs.count()

    # Conteo en cada modalidad para mostrar en los tabs
    counts = {
        'presencial': Curso.objects.filter(ofrece_presencial=True).count(),
        'online': Curso.objects.filter(ofrece_online=True).count(),
    }

    return render(request, 'cursos/lista.html', {
        'categorias': categorias_lista,
        'sin_categoria': sin_categoria,
        'total_cursos': total_cursos,
        'modalidad': modalidad,
        'modalidad_label': _label_modalidad(modalidad),
        'counts': counts,
    })


@admin_requerido
def curso_crear(request):
    """Crear un curso. Soporta ?modalidad=online para preseleccionar la modalidad."""
    modalidad_pref = request.GET.get('modalidad', 'presencial')
    if modalidad_pref not in MODALIDADES_VALIDAS:
        modalidad_pref = 'presencial'

    if request.method == 'POST':
        form = CursoForm(request.POST)
        if form.is_valid():
            curso = form.save()
            messages.success(request, f'Curso "{curso.nombre}" creado.')
            # Redirige a la lista de la modalidad activa
            modalidad_redirect = (
                'online' if curso.ofrece_online and not curso.ofrece_presencial
                else 'presencial'
            )
            return redirect('academia:cursos_lista', modalidad=modalidad_redirect)
    else:
        cat_id = request.GET.get('categoria')
        initial = {
            'ofrece_presencial': modalidad_pref == 'presencial',
            'ofrece_online': modalidad_pref == 'online',
        }
        if cat_id and cat_id.isdigit():
            initial['categoria'] = cat_id
        form = CursoForm(initial=initial)

    return render(request, 'cursos/form.html', {
        'form': form,
        'modo': 'crear',
        'titulo': 'Nuevo Curso',
        'modalidad_pref': modalidad_pref,
    })


@admin_requerido
def curso_editar(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            form.save()
            messages.success(request, f'Curso "{curso.nombre}" actualizado.')
            modalidad_redirect = 'online' if curso.ofrece_online and not curso.ofrece_presencial else 'presencial'
            return redirect('academia:cursos_lista', modalidad=modalidad_redirect)
    else:
        form = CursoForm(instance=curso)
    return render(request, 'cursos/form.html', {
        'form': form,
        'curso': curso,
        'modo': 'editar',
        'titulo': f'Editar: {curso.nombre}',
        'modalidad_pref': 'online' if (curso.ofrece_online and not curso.ofrece_presencial) else 'presencial',
    })


@admin_requerido
@require_POST
def curso_eliminar(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    modalidad_redirect = 'online' if (curso.ofrece_online and not curso.ofrece_presencial) else 'presencial'
    if curso.matriculas.exists():
        curso.activo = False
        curso.save()
        messages.warning(
            request,
            f'El curso "{curso.nombre}" tiene matrículas. Se marcó como inactivo.'
        )
    else:
        nombre = curso.nombre
        curso.delete()
        messages.success(request, f'Curso "{nombre}" eliminado.')
    return redirect('academia:cursos_lista', modalidad=modalidad_redirect)


@admin_requerido
def curso_jornadas(request, pk):
    """Lista jornadas del curso y permite agregar nuevas en la misma pantalla."""
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        form = JornadaCursoForm(request.POST)
        if form.is_valid():
            jornada = form.save(commit=False)
            jornada.curso = curso
            jornada.save()
            messages.success(request, f'Jornada {jornada.get_modalidad_display().lower()} agregada.')
            return redirect('academia:curso_jornadas', pk=curso.pk)
    else:
        # Por defecto, sugerir la modalidad que el curso ofrece
        modalidad_inicial = 'presencial' if curso.ofrece_presencial else 'online'
        form = JornadaCursoForm(initial={'modalidad': modalidad_inicial, 'activo': True})

    jornadas_pres = curso.jornadas.filter(modalidad='presencial').order_by('fecha_inicio')
    jornadas_onl = curso.jornadas.filter(modalidad='online').order_by('fecha_inicio')

    return render(request, 'cursos/jornadas.html', {
        'curso': curso,
        'jornadas_presencial': jornadas_pres,
        'jornadas_online': jornadas_onl,
        'form': form,
    })


@admin_requerido
@require_POST
def jornada_eliminar(request, pk, jornada_pk):
    curso = get_object_or_404(Curso, pk=pk)
    jornada = get_object_or_404(JornadaCurso, pk=jornada_pk, curso=curso)
    if jornada.matriculas.exists():
        jornada.activo = False
        jornada.save()
        messages.warning(request, 'La jornada tiene matrículas; se marcó como inactiva.')
    else:
        jornada.delete()
        messages.success(request, 'Jornada eliminada.')
    return redirect('academia:curso_jornadas', pk=curso.pk)


# ─────────────────────────────────────────────────────────
# Endpoints AJAX
# ─────────────────────────────────────────────────────────

@login_required
def api_curso_detalle(request, pk):
    """Devuelve datos del curso. Usa ?modalidad= para devolver el valor correcto."""
    curso = get_object_or_404(Curso, pk=pk)
    modalidad = request.GET.get('modalidad', 'presencial')
    if modalidad not in MODALIDADES_VALIDAS:
        modalidad = 'presencial'

    return JsonResponse({
        'ok': True,
        'curso': {
            'id': curso.id,
            'nombre': curso.nombre,
            'valor': str(curso.valor_para(modalidad)),
            'valor_presencial': str(curso.valor_presencial),
            'valor_online': str(curso.valor_online),
            'ofrece_presencial': curso.ofrece_presencial,
            'ofrece_online': curso.ofrece_online,
            'categoria_id': curso.categoria_id,
            'categoria_nombre': curso.categoria.nombre if curso.categoria else '',
            # True si la categoría es "Técnico" (case-insensitive, ignora acentos básicos)
            'requiere_talla': bool(
                curso.categoria
                and curso.categoria.nombre.strip().lower() in ('técnico', 'tecnico')
            ),
        }
    })


@login_required
def api_curso_jornadas(request, pk):
    """Devuelve jornadas del curso. Usa ?modalidad= para filtrar."""
    curso = get_object_or_404(Curso, pk=pk)
    modalidad = request.GET.get('modalidad', '').strip()

    jornadas = curso.jornadas.filter(activo=True)
    if modalidad in MODALIDADES_VALIDAS:
        jornadas = jornadas.filter(modalidad=modalidad)

    data = [
        {
            'id': j.id,
            'modalidad': j.modalidad,
            'descripcion': j.descripcion,
            'fecha': j.fecha_inicio.strftime('%d/%m/%Y'),
            'hora_inicio': j.hora_inicio.strftime('%H:%M'),
            'hora_fin': j.hora_fin.strftime('%H:%M'),
            'ciudad': j.ciudad,
            'etiqueta': j.etiqueta,
        }
        for j in jornadas
    ]
    return JsonResponse({'ok': True, 'jornadas': data})


@admin_requerido
@require_http_methods(['POST'])
def api_categoria_crear(request):
    """Crea una categoría desde el modal del form de curso. (Solo admin)"""
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        data = request.POST

    nombre = (data.get('nombre') or '').strip()
    color = (data.get('color') or '#1a237e').strip()
    descripcion = (data.get('descripcion') or '').strip()

    if not nombre:
        return JsonResponse(
            {'ok': False, 'error': 'El nombre de la categoría es obligatorio.'},
            status=400
        )

    if Categoria.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse(
            {'ok': False, 'error': f'Ya existe una categoría llamada "{nombre}".'},
            status=409
        )

    colores_validos = [c[0] for c in Categoria.COLORES]
    if color not in colores_validos:
        color = '#1a237e'

    siguiente_orden = (Categoria.objects.order_by('-orden').first().orden + 1) \
        if Categoria.objects.exists() else 1

    categoria = Categoria.objects.create(
        nombre=nombre,
        descripcion=descripcion,
        color=color,
        orden=siguiente_orden,
    )

    return JsonResponse({
        'ok': True,
        'categoria': {
            'id': categoria.id,
            'nombre': categoria.nombre,
            'color': categoria.color,
        },
    })
