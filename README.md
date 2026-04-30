# Formación Técnica y Profesional EC — Sistema Académico

## 🆕 Versión 4 — Sistema de Abonos profesional

### Cambios principales

**1. Sistema de Abonos** 💵
- Cada matrícula tiene un **historial de pagos parciales** (abonos)
- Cada abono guarda: fecha, monto, método (Efectivo / Transferencia / Tarjeta), número de recibo, observaciones, quién lo registró
- **Número de recibo automático** (REC-0001, REC-0002…) — editable manualmente si lo necesitas
- El saldo se **recalcula automáticamente** al crear/editar/eliminar abonos
- Cada abono tiene su **recibo imprimible** con el formato profesional (botón `📄`)
- **Validación**: no se puede abonar más que el saldo pendiente

**2. Pantalla central por matrícula** (`/matricula/<id>/abonos/`)
- Cabecera con datos del estudiante + barra de progreso visual
- Estadísticas por método de pago
- Tabla con todos los abonos
- Modal para registrar abono nuevo (fecha=hoy, monto sugerido=saldo)
- Acceso desde el botón **"💵 Gestionar pagos"** en `/pagos/`

**3. Excel de abonos** (`/abonos/exportar/`)
- Reporte completo con totales por método de pago al final
- Filtros por año, mes, método

**4. Matrícula Online — temporalmente deshabilitada**
- La sección de matrícula online está oculta mientras se vincula con **Google Forms**
- Los **cursos online** siguen viéndose normalmente en `/cursos/online/` ✓
- Las matrículas online existentes siguen accesibles para gestionar sus pagos
- Para reactivarla: en `academia/views.py` cambia `MATRICULA_ONLINE_HABILITADA = False` a `True`

---

## 📦 Instalación

### macOS / Linux

```bash
cd formacionProfesional

# Si tienes el venv del proyecto anterior, úsalo. Si no:
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias (la única nueva sigue siendo openpyxl)
pip install -r requirements.txt

# Aplicar la migración nueva (0005_abonos)
python manage.py migrate

# Si nunca corriste setup_roles, hazlo ahora
python manage.py setup_roles

# Arrancar
python manage.py runserver
```

### Windows

```powershell
cd formacionProfesional
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles
python manage.py runserver
```

> En Windows el comando se llama `python` (no `python3`). Y para activar venv usa `venv\Scripts\activate` con backslash.

---

## 🗺 Mapa de rutas (nuevas)

| Ruta | Quién accede | Qué hace |
|------|:-:|----------|
| `/matricula/<id>/abonos/` | Admin + Asesor | 🆕 Pantalla principal de pagos por matrícula |
| `/matricula/<id>/abonos/crear/` | Admin + Asesor | 🆕 (POST) Registra un abono |
| `/matricula/<id>/abonos/<aid>/editar/` | Admin + Asesor | 🆕 Edita un abono |
| `/matricula/<id>/abonos/<aid>/eliminar/` | Admin + Asesor | 🆕 (POST) Elimina y recalcula |
| `/abonos/exportar/` | Admin + Asesor | 🆕 Excel con totales por método |
| `/abonos/<id>/recibo/` | Admin + Asesor | 🆕 Recibo imprimible |

---

## 💵 Cómo se usa el sistema de abonos

### Flujo típico

1. Entras a `/pagos/` y ves el listado de matrículas con su estado
2. Click en **"💵 Gestionar pagos"** de una matrícula
3. Ves la pantalla con:
   - Datos del estudiante
   - Valor del curso, total pagado, saldo
   - Barra de progreso visual
   - Historial de abonos
4. Click en **"+ Registrar abono"**
5. Modal con fecha (hoy por defecto), monto (sugiere el saldo), método de pago, recibo (auto), observaciones
6. Guardar → el saldo se recalcula automáticamente
7. Cada abono tiene un botón 📄 para abrir su **recibo imprimible**

### Métodos de pago disponibles

- 💵 Efectivo
- 🏦 Transferencia bancaria
- 💳 Tarjeta de crédito/débito

Para añadir más métodos (cheque, depósito, etc.), edita `METODOS_PAGO` en `academia/models.py` y crea una nueva migración.

### Datos migrados automáticamente

Cuando aplicas la migración 0005 por primera vez, **cada matrícula con `valor_pagado > 0` se convierte en un abono inicial** con:
- Fecha = fecha de matrícula
- Método = "Efectivo"
- Recibo = REC-0001, REC-0002, …
- Observación: "Pago inicial migrado desde versión anterior"

Así no pierdes datos. Si después quieres editar esos abonos iniciales (por ejemplo cambiar el método a "Transferencia"), entras al recibo y los modificas.

---

## 🔄 Reactivar matrícula online

Cuando termines la integración con Google Forms y quieras reactivar la matrícula online:

1. Abre `academia/views.py`
2. Busca la línea `MATRICULA_ONLINE_HABILITADA = False`
3. Cámbiala a `MATRICULA_ONLINE_HABILITADA = True`
4. Reinicia el servidor

Sin reiniciar Django, las pestañas y tarjetas online vuelven a aparecer.

---

## 🛠 Solución de problemas

### "El saldo no coincide con la suma de abonos"

Esto solo puede pasar si modificas `valor_pagado` directamente desde el admin de Django. Solución:

```bash
python manage.py shell
>>> from academia.models import Matricula
>>> for m in Matricula.objects.all(): m.recalcular_valor_pagado()
```

### "Quiero cambiar el formato del número de recibo"

Edita `Abono.generar_numero_recibo()` en `academia/models.py`. Por ejemplo, para añadir el año:

```python
return f'REC-{date.today().year}-{siguiente:04d}'
```

### "Los recibos antiguos siguen con el formato viejo"

Sí, el cambio aplica solo a recibos nuevos. Los anteriores conservan su número original.

---

## 📂 Archivos nuevos y modificados (v4)

```
academia/
├── models.py                # ✏ +Abono, +recalcular_valor_pagado()
├── forms.py                 # ✏ +AbonoForm con validación de saldo
├── views.py                 # ✏ +MATRICULA_ONLINE_HABILITADA flag
├── views_pagos.py           # ✏ +5 vistas de abonos (crear, editar, eliminar, exportar, recibo)
├── urls.py                  # ✏ +6 rutas de abonos
├── context_processors.py    # ✏ +feature_flags para templates
└── migrations/
    └── 0005_abonos.py       # 🆕 Crea tabla + migra valor_pagado existente

templates/pagos/
├── matricula_abonos.html    # 🆕 Pantalla principal con modal
├── abono_editar.html        # 🆕 Editar abono individual
├── recibo.html              # 🆕 Comprobante imprimible
└── lista.html               # ✏ Botón "Gestionar pagos"

templates/
├── bienvenida.html          # ✏ Tarjeta online deshabilitada (con flag)
└── matricula/
    ├── menu.html            # ✏ Pestaña online oculta cuando flag=False
    └── lista.html           # ✏ Pestaña online oculta cuando flag=False
```

---

**Mantenido por Yandri Guevara — Formación Técnica y Profesional EC**
# Formaci-n_T-cnica_Profesional
