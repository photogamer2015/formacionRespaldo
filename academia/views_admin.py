"""
Registro Administrativo: dashboard financiero.

Solo accesible por administradores. Muestra:
- KPIs del mes (ingresos, egresos, balance)
- Gráfico de barras: ingresos vs egresos por mes (últimos 6 meses)
- Top egresos del mes por categoría
- Movimientos recientes (egresos + ingresos mezclados)
- CRUD de egresos
"""
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EgresoForm
from .models import Abono, CategoriaEgreso, Comprobante, Egreso
from .permisos import admin_requerido


MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


def _rango_mes(anio, mes):
    """Devuelve (primer_dia, ultimo_dia) del mes dado."""
    primer = date(anio, mes, 1)
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    ultimo = date(anio, mes, ultimo_dia)
    return primer, ultimo


def _ingresos_periodo(desde, hasta):
    """
    Suma todos los ingresos en el rango de fechas.
    Combina:
      - Abonos (matrículas presenciales): por fecha de abono
      - Comprobantes (ventas asesoras): por fecha de inscripción, solo el pago_abono
    """
    abonos = Abono.objects.filter(
        fecha__gte=desde, fecha__lte=hasta
    ).aggregate(s=Sum('monto'))['s'] or Decimal('0.00')

    ventas = Comprobante.objects.filter(
        fecha_inscripcion__gte=desde, fecha_inscripcion__lte=hasta
    ).aggregate(s=Sum('pago_abono'))['s'] or Decimal('0.00')

    return {
        'abonos': abonos,
        'ventas': ventas,
        'total': abonos + ventas,
    }


def _egresos_periodo(desde, hasta):
    """Suma egresos en el rango."""
    return Egreso.objects.filter(
        fecha__gte=desde, fecha__lte=hasta
    ).aggregate(s=Sum('monto'))['s'] or Decimal('0.00')


def _egresos_por_categoria_periodo(desde, hasta):
    """Devuelve lista [{categoria, total, color, icono}, …]."""
    qs = (Egreso.objects
          .filter(fecha__gte=desde, fecha__lte=hasta)
          .values('categoria__id', 'categoria__nombre',
                  'categoria__color', 'categoria__icono')
          .annotate(total=Sum('monto'))
          .order_by('-total'))
    return [
        {
            'id': r['categoria__id'],
            'nombre': r['categoria__nombre'],
            'color': r['categoria__color'],
            'icono': r['categoria__icono'],
            'total': r['total'] or Decimal('0.00'),
        }
        for r in qs
    ]




@admin_requerido
def admin_dashboard(request):
    """Panel principal del Registro Administrativo."""
    hoy = timezone.localdate()

    # Permite filtrar por mes/año via querystring (?anio=2026&mes=4)
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
        if not (1 <= mes <= 12):
            mes = hoy.month
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    desde, hasta = _rango_mes(anio, mes)

    # ── Datos del mes seleccionado ──
    ingresos = _ingresos_periodo(desde, hasta)
    egresos_total = _egresos_periodo(desde, hasta)
    balance = ingresos['total'] - egresos_total
    top_categorias = _egresos_por_categoria_periodo(desde, hasta)

    # ── Comparación con mes anterior ──
    if mes == 1:
        anio_prev, mes_prev = anio - 1, 12
    else:
        anio_prev, mes_prev = anio, mes - 1
    desde_prev, hasta_prev = _rango_mes(anio_prev, mes_prev)
    ing_prev = _ingresos_periodo(desde_prev, hasta_prev)['total']
    egr_prev = _egresos_periodo(desde_prev, hasta_prev)
    bal_prev = ing_prev - egr_prev

    def variacion(actual, anterior):
        if anterior == 0:
            return None
        return float(((actual - anterior) / abs(anterior)) * 100)

    # ── Datos para gráfico (últimos 6 meses) ──
    serie_meses = []
    for i in range(5, -1, -1):
        # contar i meses hacia atrás desde el mes seleccionado
        m = mes - i
        a = anio
        while m <= 0:
            m += 12
            a -= 1
        d, h = _rango_mes(a, m)
        ing = _ingresos_periodo(d, h)['total']
        egr = _egresos_periodo(d, h)
        serie_meses.append({
            'label': f'{MESES_ES[m][:3]} {a}',
            'ingresos': float(ing),
            'egresos': float(egr),
            'balance': float(ing - egr),
        })

    # ── Total acumulado histórico (todo el sistema) ──
    total_abonos_hist = Abono.objects.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
    total_ventas_hist = Comprobante.objects.aggregate(s=Sum('pago_abono'))['s'] or Decimal('0.00')
    total_egresos_hist = Egreso.objects.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
    total_ingresos_hist = total_abonos_hist + total_ventas_hist
    balance_hist = total_ingresos_hist - total_egresos_hist

    # Por cobrar: saldos pendientes (informativo, no se cuenta como ingreso)
    por_cobrar_comprobantes = Comprobante.objects.aggregate(
        s=Sum('diferencia')
    )['s'] or Decimal('0.00')

    # ── Movimientos recientes del mes (últimos 10 egresos) ──
    egresos_recientes = (Egreso.objects
                         .filter(fecha__gte=desde, fecha__lte=hasta)
                         .select_related('categoria', 'registrado_por')
                         .order_by('-fecha', '-creado')[:10])

    # Lista de meses para el selector (últimos 24 meses)
    meses_selector = []
    for i in range(0, 24):
        m = hoy.month - i
        a = hoy.year
        while m <= 0:
            m += 12
            a -= 1
        meses_selector.append({
            'anio': a, 'mes': m,
            'label': f'{MESES_ES[m]} {a}',
            'seleccionado': (a == anio and m == mes),
        })

    return render(request, 'admin_panel/dashboard.html', {
        'anio': anio,
        'mes': mes,
        'mes_nombre': MESES_ES[mes],
        'desde': desde,
        'hasta': hasta,
        'ingresos': ingresos,
        'egresos_total': egresos_total,
        'balance': balance,
        'top_categorias': top_categorias,
        'egresos_recientes': egresos_recientes,
        'meses_selector': meses_selector,
        # Comparativa
        'ing_prev': ing_prev,
        'egr_prev': egr_prev,
        'bal_prev': bal_prev,
        'var_ingresos': variacion(ingresos['total'], ing_prev),
        'var_egresos': variacion(egresos_total, egr_prev),
        'var_balance': variacion(balance, bal_prev),
        # Histórico
        'total_ingresos_hist': total_ingresos_hist,
        'total_egresos_hist': total_egresos_hist,
        'balance_hist': balance_hist,
        'total_abonos_hist': total_abonos_hist,
        'total_ventas_hist': total_ventas_hist,
        'por_cobrar': por_cobrar_comprobantes,
        # Gráfico (JSON serializable)
        'serie_meses_json': json.dumps(serie_meses),
    })


@admin_requerido
def egresos_lista(request):
    """Lista de todos los egresos con filtros."""
    qs = Egreso.objects.select_related('categoria', 'registrado_por')

    # Filtros
    categoria_id = request.GET.get('categoria', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()
    q = request.GET.get('q', '').strip()

    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if q:
        qs = qs.filter(concepto__icontains=q)

    total_filtrado = qs.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')

    return render(request, 'admin_panel/egresos_lista.html', {
        'egresos': qs[:200],  # limitar a 200 para no quemar render
        'total_filtrado': total_filtrado,
        'categorias': CategoriaEgreso.objects.filter(activo=True),
        'filtros': {
            'categoria': categoria_id,
            'desde': desde,
            'hasta': hasta,
            'q': q,
        },
    })


@admin_requerido
def egreso_crear(request):
    if request.method == 'POST':
        form = EgresoForm(request.POST)
        if form.is_valid():
            egreso = form.save(commit=False)
            egreso.registrado_por = request.user
            egreso.save()
            messages.success(
                request,
                f'Egreso registrado: {egreso.concepto} (${egreso.monto}).'
            )
            return redirect('academia:admin_egresos_lista')
    else:
        form = EgresoForm(initial={'fecha': timezone.localdate()})
    return render(request, 'admin_panel/egreso_form.html', {
        'form': form,
        'modo': 'crear',
        'titulo': 'Registrar nuevo egreso',
    })


@admin_requerido
def egreso_editar(request, pk):
    egreso = get_object_or_404(Egreso, pk=pk)
    if request.method == 'POST':
        form = EgresoForm(request.POST, instance=egreso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Egreso actualizado.')
            return redirect('academia:admin_egresos_lista')
    else:
        form = EgresoForm(instance=egreso)
    return render(request, 'admin_panel/egreso_form.html', {
        'form': form,
        'egreso': egreso,
        'modo': 'editar',
        'titulo': f'Editar egreso #{egreso.pk}',
    })


@admin_requerido
@require_POST
def egreso_eliminar(request, pk):
    egreso = get_object_or_404(Egreso, pk=pk)
    concepto = egreso.concepto
    monto = egreso.monto
    egreso.delete()
    messages.success(
        request,
        f'Egreso eliminado: {concepto} (${monto}).'
    )
    return redirect('academia:admin_egresos_lista')


# ─────────────────────────────────────────────────────────
# Exportación a CSV
# ─────────────────────────────────────────────────────────

import csv
from django.http import HttpResponse


def _csv_response(filename):
    """
    Crea una respuesta HTTP CSV. Usa BOM UTF-8 para que Excel
    abra bien las tildes y la ñ en Windows.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM para Excel
    return response


@admin_requerido
def export_reporte_mes(request):
    """
    Exporta el reporte financiero completo del mes:
    - Resumen (ingresos, egresos, balance)
    - Detalle de egresos
    - Detalle de ingresos por abonos
    - Detalle de ingresos por ventas/comprobantes
    Todo en un solo CSV.
    """
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
        if not (1 <= mes <= 12):
            mes = hoy.month
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    desde, hasta = _rango_mes(anio, mes)
    nombre_mes = MESES_ES[mes]

    ingresos = _ingresos_periodo(desde, hasta)
    egresos_total = _egresos_periodo(desde, hasta)
    balance = ingresos['total'] - egresos_total

    response = _csv_response(
        f'reporte_{anio}_{mes:02d}_{nombre_mes.lower()}.csv'
    )
    w = csv.writer(response)

    # ── Encabezado ─────────────────────────────────────
    w.writerow([f'REPORTE FINANCIERO — {nombre_mes.upper()} {anio}'])
    w.writerow([f'Período: {desde.strftime("%d/%m/%Y")} a {hasta.strftime("%d/%m/%Y")}'])
    w.writerow([f'Generado: {timezone.now().strftime("%d/%m/%Y %H:%M")}'])
    w.writerow([])

    # ── Resumen ────────────────────────────────────────
    w.writerow(['RESUMEN'])
    w.writerow(['Concepto', 'Monto (USD)'])
    w.writerow(['Ingresos por abonos (matrículas)', f'{ingresos["abonos"]:.2f}'])
    w.writerow(['Ingresos por ventas (comprobantes)', f'{ingresos["ventas"]:.2f}'])
    w.writerow(['TOTAL INGRESOS', f'{ingresos["total"]:.2f}'])
    w.writerow(['TOTAL EGRESOS', f'{egresos_total:.2f}'])
    w.writerow([
        'BALANCE NETO',
        f'{balance:.2f}',
        '(GANANCIA)' if balance > 0 else ('(PÉRDIDA)' if balance < 0 else '(EQUILIBRIO)')
    ])
    w.writerow([])

    # ── Egresos detallados ─────────────────────────────
    w.writerow(['EGRESOS DETALLADOS'])
    w.writerow(['Fecha', 'Categoría', 'Concepto', 'Monto (USD)', 'Notas', 'Registrado por'])
    egresos = (Egreso.objects
               .filter(fecha__gte=desde, fecha__lte=hasta)
               .select_related('categoria', 'registrado_por')
               .order_by('fecha'))
    for e in egresos:
        registrador = ''
        if e.registrado_por:
            registrador = e.registrado_por.get_full_name() or e.registrado_por.username
        w.writerow([
            e.fecha.strftime('%d/%m/%Y'),
            e.categoria.nombre,
            e.concepto,
            f'{e.monto:.2f}',
            e.notas or '',
            registrador,
        ])
    if not egresos:
        w.writerow(['(Sin egresos en este período)'])
    w.writerow([])

    # ── Ingresos por abonos ────────────────────────────
    w.writerow(['INGRESOS — ABONOS DE MATRÍCULAS'])
    w.writerow(['Fecha', 'Recibo', 'Estudiante', 'Cédula', 'Curso', 'Método', 'Banco', 'Monto (USD)'])
    abonos = (Abono.objects
              .filter(fecha__gte=desde, fecha__lte=hasta)
              .select_related('matricula__estudiante', 'matricula__curso')
              .order_by('fecha'))
    for a in abonos:
        est = a.matricula.estudiante
        w.writerow([
            a.fecha.strftime('%d/%m/%Y'),
            a.numero_recibo or '',
            est.nombre_completo,
            est.cedula,
            a.matricula.curso.nombre,
            a.get_metodo_display(),
            a.get_banco_display() if a.banco else '',
            f'{a.monto:.2f}',
        ])
    if not abonos:
        w.writerow(['(Sin abonos en este período)'])
    w.writerow([])

    # ── Ingresos por comprobantes ──────────────────────
    w.writerow(['INGRESOS — VENTAS POR COMPROBANTE'])
    w.writerow(['Fecha insc.', 'Cliente', 'Celular', 'Curso', 'Modalidad',
                'Pago/Abono (USD)', 'Diferencia (USD)', 'Vendedora'])
    comprobantes = (Comprobante.objects
                    .filter(fecha_inscripcion__gte=desde, fecha_inscripcion__lte=hasta)
                    .select_related('curso', 'vendedora')
                    .order_by('fecha_inscripcion'))
    for c in comprobantes:
        vendedora = c.vendedora_nombre or (c.vendedora.username if c.vendedora else '')
        w.writerow([
            c.fecha_inscripcion.strftime('%d/%m/%Y'),
            c.nombre_persona,
            c.celular,
            c.curso.nombre,
            c.get_modalidad_display(),
            f'{c.pago_abono:.2f}',
            f'{c.diferencia:.2f}',
            vendedora,
        ])
    if not comprobantes:
        w.writerow(['(Sin comprobantes en este período)'])

    return response


@admin_requerido
def export_egresos(request):
    """
    Exporta los egresos respetando los filtros activos
    (mismos parámetros GET que la lista).
    """
    qs = Egreso.objects.select_related('categoria', 'registrado_por')

    categoria_id = request.GET.get('categoria', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()
    q = request.GET.get('q', '').strip()

    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if q:
        qs = qs.filter(concepto__icontains=q)

    qs = qs.order_by('-fecha', '-creado')

    response = _csv_response(
        f'egresos_{timezone.now().strftime("%Y%m%d_%H%M")}.csv'
    )
    w = csv.writer(response)
    w.writerow(['EGRESOS — Exportación filtrada'])
    if desde or hasta or categoria_id or q:
        filtros = []
        if desde: filtros.append(f'desde {desde}')
        if hasta: filtros.append(f'hasta {hasta}')
        if categoria_id:
            cat = CategoriaEgreso.objects.filter(pk=categoria_id).first()
            if cat: filtros.append(f'categoría: {cat.nombre}')
        if q: filtros.append(f'búsqueda: "{q}"')
        w.writerow(['Filtros: ' + ', '.join(filtros)])
    w.writerow([f'Generado: {timezone.now().strftime("%d/%m/%Y %H:%M")}'])
    w.writerow([])

    w.writerow(['Fecha', 'Categoría', 'Concepto', 'Monto (USD)', 'Notas', 'Registrado por'])

    total = Decimal('0.00')
    for e in qs:
        registrador = ''
        if e.registrado_por:
            registrador = e.registrado_por.get_full_name() or e.registrado_por.username
        w.writerow([
            e.fecha.strftime('%d/%m/%Y'),
            e.categoria.nombre,
            e.concepto,
            f'{e.monto:.2f}',
            e.notas or '',
            registrador,
        ])
        total += e.monto

    w.writerow([])
    w.writerow(['', '', 'TOTAL', f'{total:.2f}'])

    return response
