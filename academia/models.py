from django.db import models
from decimal import Decimal


# ─────────────────────────────────────────────────────────
# Constantes compartidas
# ─────────────────────────────────────────────────────────

MODALIDADES = [
    ('presencial', 'Presencial'),
    ('online', 'Online'),
]


class Categoria(models.Model):
    """
    Categoría de cursos. Por defecto: Empresariales, Técnico, Vacacionales.
    Pero el usuario puede agregar las que quiera.
    """
    COLORES = [
        ('#1a237e', 'Azul'),
        ('#2e7d32', 'Verde'),
        ('#c62828', 'Rojo'),
        ('#f0ad4e', 'Naranja'),
        ('#6a1b9a', 'Morado'),
        ('#00838f', 'Cian'),
        ('#5d4037', 'Marrón'),
        ('#455a64', 'Gris'),
    ]

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, choices=COLORES, default='#1a237e',
        help_text='Color con el que se identifica la categoría.'
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text='Orden de aparición (menor = primero).'
    )
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Curso(models.Model):
    """
    Cursos que se ofertan. Cada uno puede ofrecerse en modalidad presencial,
    online, o en ambas. Cada modalidad tiene su propio valor.
    """

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT,
        related_name='cursos', null=True, blank=True,
    )
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True)

    # Modalidades que ofrece el curso
    ofrece_presencial = models.BooleanField(
        default=True,
        help_text='Marcar si el curso se ofrece en modalidad presencial.'
    )
    ofrece_online = models.BooleanField(
        default=False,
        help_text='Marcar si el curso se ofrece en modalidad online.'
    )

    # Valores diferenciados por modalidad
    valor_presencial = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Costo del curso presencial (USD).'
    )
    valor_online = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Costo del curso online (USD).'
    )

    # Campo legado (se conserva para no romper datos antiguos).
    # NO se usa para nuevas matrículas; el código siempre debe leer
    # valor_presencial / valor_online según la modalidad.
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='[Legado] Valor único anterior. Reemplazado por valor_presencial / valor_online.'
    )

    duracion = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['categoria__orden', 'nombre']

    def valor_para(self, modalidad):
        """Devuelve el valor del curso según la modalidad."""
        if modalidad == 'online':
            return self.valor_online
        return self.valor_presencial

    def ofrece(self, modalidad):
        """¿El curso se ofrece en esa modalidad?"""
        if modalidad == 'online':
            return self.ofrece_online
        return self.ofrece_presencial

    @property
    def modalidades_etiqueta(self):
        """Texto corto que indica las modalidades disponibles."""
        partes = []
        if self.ofrece_presencial:
            partes.append('Presencial')
        if self.ofrece_online:
            partes.append('Online')
        return ' + '.join(partes) if partes else '— Sin modalidad —'

    def __str__(self):
        # Mostrar el valor más relevante (prioriza presencial si lo ofrece)
        v = self.valor_presencial if self.ofrece_presencial else self.valor_online
        return f'{self.nombre} (${v})'


class JornadaCurso(models.Model):
    """
    Cada curso puede tener varias jornadas (fecha + horario + ciudad/zona).
    Estas son las opciones que el estudiante elige al matricularse.
    Cada jornada pertenece a una modalidad (presencial u online).
    """
    curso = models.ForeignKey(
        Curso, on_delete=models.CASCADE, related_name='jornadas'
    )
    modalidad = models.CharField(
        max_length=20, choices=MODALIDADES, default='presencial',
        help_text='Modalidad de esta jornada.'
    )
    descripcion = models.CharField(
        max_length=200,
        help_text='Ej.: Sábados intensivos, Domingos intensivos…'
    )
    fecha_inicio = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    ciudad = models.CharField(
        max_length=100, blank=True,
        help_text='Ciudad (presencial) o plataforma (online). Opcional.'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Jornada'
        verbose_name_plural = 'Jornadas'
        ordering = ['curso', 'modalidad', 'fecha_inicio']

    @property
    def etiqueta(self):
        prefijo = '🟢 Online' if self.modalidad == 'online' else '🏫 Presencial'
        partes = [prefijo, self.descripcion.upper()]
        if self.fecha_inicio:
            partes.append(self.fecha_inicio.strftime('%d/%m/%Y'))
        if self.hora_inicio and self.hora_fin:
            partes.append(
                f'{self.hora_inicio.strftime("%H:%M")} a {self.hora_fin.strftime("%H:%M")}'
            )
        if self.ciudad:
            partes.append(f'({self.ciudad})')
        return ' – '.join(partes)

    def __str__(self):
        return self.etiqueta


class Estudiante(models.Model):
    """Datos personales del estudiante."""

    NIVELES_FORMACION = [
        ('primaria', 'Primaria'),
        ('secundaria', 'Bachillerato / Secundaria'),
        ('tecnico', 'Técnico'),
        ('tecnologo', 'Tecnólogo'),
        ('tercer_nivel', 'Tercer Nivel (Pregrado)'),
        ('cuarto_nivel', 'Cuarto Nivel (Posgrado)'),
        ('otro', 'Otro'),
    ]

    cedula = models.CharField(max_length=20, unique=True)
    apellidos = models.CharField(max_length=100)
    nombres = models.CharField(max_length=100)
    edad = models.PositiveIntegerField(null=True, blank=True)
    correo = models.EmailField(blank=True)
    celular = models.CharField(max_length=20, blank=True)
    nivel_formacion = models.CharField(
        max_length=20, choices=NIVELES_FORMACION, blank=True
    )
    titulo_profesional = models.CharField(max_length=200, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['apellidos', 'nombres']

    @property
    def nombre_completo(self):
        return f'{self.apellidos} {self.nombres}'.strip()

    def __str__(self):
        return f'{self.cedula} – {self.nombre_completo}'


class Matricula(models.Model):
    """Matrícula que une estudiante + curso + jornada + pago."""

    TALLAS_CAMISETA = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('NA', 'Ninguna de las anteriores (la academia solo cubre hasta XL)'),
    ]

    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.PROTECT, related_name='matriculas'
    )
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT, related_name='matriculas'
    )
    jornada = models.ForeignKey(
        JornadaCurso, on_delete=models.PROTECT,
        related_name='matriculas', null=True, blank=True,
        help_text='Fecha y horario seleccionados (depende del curso y modalidad).'
    )
    modalidad = models.CharField(
        max_length=20, choices=MODALIDADES, default='presencial'
    )
    fecha_matricula = models.DateField()
    talla_camiseta = models.CharField(
        max_length=2, choices=TALLAS_CAMISETA, blank=True
    )
    valor_curso = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text='Se autocompleta con el valor del curso según modalidad, pero puedes ajustarlo.'
    )
    valor_pagado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    observaciones = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    # Auditoría: qué usuario registró la matrícula (útil para asesores)
    registrado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matriculas_registradas',
        help_text='Usuario que registró la matrícula (admin o asesor).'
    )

    class Meta:
        verbose_name = 'Matrícula'
        verbose_name_plural = 'Matrículas'
        ordering = ['-fecha_matricula', '-creado']

    @property
    def saldo(self):
        return (self.valor_curso or Decimal('0.00')) - (self.valor_pagado or Decimal('0.00'))

    @property
    def estado_pago(self):
        if self.saldo <= 0:
            return 'Pagado'
        if self.valor_pagado and self.valor_pagado > 0:
            return 'Parcial'
        return 'Pendiente'

    @property
    def horario(self):
        if self.jornada and self.jornada.hora_inicio and self.jornada.hora_fin:
            return f'{self.jornada.hora_inicio.strftime("%H:%M")} – {self.jornada.hora_fin.strftime("%H:%M")}'
        return '—'

    @property
    def sede(self):
        if self.jornada and self.jornada.ciudad:
            return self.jornada.ciudad
        return '—'

    def recalcular_valor_pagado(self, save=True):
        """
        Recalcula valor_pagado como la suma de todos los abonos.
        Se llama automáticamente al guardar/eliminar un Abono.
        """
        total = self.abonos.aggregate(s=models.Sum('monto'))['s'] or Decimal('0.00')
        self.valor_pagado = total
        if save:
            super().save(update_fields=['valor_pagado', 'actualizado'])
        return total

    def save(self, *args, **kwargs):
        # Si no se asignó valor_curso, tomar el valor de la modalidad
        if not self.valor_curso and self.curso_id:
            self.valor_curso = self.curso.valor_para(self.modalidad)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.estudiante} – {self.curso} ({self.get_modalidad_display()})'


class Abono(models.Model):
    """
    Cada pago parcial o completo que hace un estudiante para una matrícula.
    La suma de todos los abonos = valor_pagado de la matrícula.
    """

    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia bancaria'),
        ('tarjeta', 'Tarjeta de crédito/débito'),
    ]

    BANCOS = [
        ('pichincha', 'Banco Pichincha'),
        ('guayaquil', 'Banco Guayaquil'),
        ('produbanco', 'Produbanco'),
        ('pacifico', 'Banco Pacífico'),
        ('payphone', 'Payphone'),
        ('interbancaria', 'Interbancaria'),
    ]

    matricula = models.ForeignKey(
        Matricula, on_delete=models.CASCADE, related_name='abonos'
    )
    fecha = models.DateField(
        help_text='Fecha en que se recibió el abono.'
    )
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text='Cantidad recibida en este abono (USD).'
    )
    metodo = models.CharField(
        max_length=20, choices=METODOS_PAGO, default='efectivo',
        help_text='Forma en que se realizó el pago.'
    )
    banco = models.CharField(
        max_length=20, choices=BANCOS, blank=True,
        help_text='Banco usado (solo si el método es Transferencia bancaria).'
    )
    numero_recibo = models.CharField(
        max_length=30, unique=True, blank=True,
        help_text='Número de comprobante. Si se deja vacío, se genera automáticamente.'
    )
    observaciones = models.TextField(blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='abonos_registrados',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Abono'
        verbose_name_plural = 'Abonos'
        ordering = ['-fecha', '-creado']

    @staticmethod
    def generar_numero_recibo():
        """Genera el siguiente número de recibo correlativo: REC-0001, REC-0002…"""
        ultimo = Abono.objects.filter(
            numero_recibo__startswith='REC-'
        ).order_by('-numero_recibo').first()

        if ultimo and ultimo.numero_recibo[4:].isdigit():
            siguiente = int(ultimo.numero_recibo[4:]) + 1
        else:
            siguiente = 1
        return f'REC-{siguiente:04d}'

    def save(self, *args, **kwargs):
        # Auto-generar número de recibo si está vacío
        if not self.numero_recibo:
            self.numero_recibo = Abono.generar_numero_recibo()
        super().save(*args, **kwargs)
        # Recalcular el total pagado de la matrícula
        if self.matricula_id:
            self.matricula.recalcular_valor_pagado()

    def delete(self, *args, **kwargs):
        matricula = self.matricula
        super().delete(*args, **kwargs)
        # Recalcular después de eliminar
        matricula.recalcular_valor_pagado()

    def __str__(self):
        return f'{self.numero_recibo} — ${self.monto} ({self.fecha})'


# ─────────────────────────────────────────────────────────
# Comprobante de Venta
# ─────────────────────────────────────────────────────────

class Comprobante(models.Model):
    """
    Comprobante de venta registrado por una vendedora/asesora.

    Captura datos completos del cliente, curso vendido, pago/abono y datos
    para la facturación. Sirve para llevar el ranking de ventas por asesora.
    """

    MODALIDAD_OPCIONES = [
        ('virtual', 'Virtual'),
        ('presencial', 'Presencial'),
    ]

    SI_NO = [
        ('si', 'Sí'),
        ('no', 'No'),
    ]

    TIPOS_REGISTRO = [
        ('central_1', 'Central 1'),
        ('central_2', 'Central 2'),
        ('central_ia', 'Central IA'),
        ('seguimiento', 'Seguimiento'),
    ]

    # ── Datos del curso vendido ──────────────────────────
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT,
        related_name='comprobantes',
        verbose_name='Curso',
    )
    modalidad = models.CharField(
        max_length=20, choices=MODALIDAD_OPCIONES,
        verbose_name='Modalidad',
    )
    fecha_inscripcion = models.DateField(
        verbose_name='Fecha de inscripción',
    )
    jornada = models.CharField(
        max_length=200,
        verbose_name='Jornada',
        help_text='Ej.: Sábados 08:00–12:00, Domingos intensivos…',
    )
    inicio_curso = models.DateField(
        verbose_name='Inicio del curso',
    )

    # ── Datos del cliente ────────────────────────────────
    nombre_persona = models.CharField(
        max_length=200,
        verbose_name='Nombre de la persona',
    )
    celular = models.CharField(
        max_length=20,
        verbose_name='Celular',
    )

    # ── Tipo de Registro ─────────────────────────────────
    tipo_registro = models.CharField(
        max_length=20, choices=TIPOS_REGISTRO, blank=True, null=True,
        verbose_name='Tipo de registro',
        help_text='Origen del registro: Central 1, Central 2, Central IA o Seguimiento.'
    )

    # ── Pagos ────────────────────────────────────────────
    pago_abono = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Pago o abono (USD)',
        help_text='Monto recibido al momento de la venta.',
    )
    diferencia = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Diferencia (USD)',
        help_text='Saldo pendiente.',
    )
    link_comprobante = models.URLField(
        max_length=500, blank=True,
        verbose_name='Link del comprobante',
        help_text='Link a la foto del comprobante (Drive, Imgur, WhatsApp Web, etc.). Opcional.',
    )

    # ── Vendedora / Asesora ──────────────────────────────
    # Se llena automáticamente con el usuario logueado al momento de registrar.
    vendedora = models.ForeignKey(
        'auth.User', on_delete=models.PROTECT,
        related_name='comprobantes_registrados',
        verbose_name='Vendedora',
        help_text='Asesor/admin que registró la venta. Se asigna automáticamente.',
    )
    # Texto plano por si en el futuro se quiere mostrar el nombre tal cual estaba
    # cuando se registró (aunque la cuenta del usuario se modifique después).
    vendedora_nombre = models.CharField(
        max_length=150, blank=True,
        verbose_name='Nombre de la vendedora (registro)',
    )

    # ── Factura ──────────────────────────────────────────
    factura_realizada = models.CharField(
        max_length=2, choices=SI_NO, default='no',
        verbose_name='Factura realizada',
    )

    # Datos para factura (todos obligatorios)
    fact_nombres = models.CharField(
        max_length=120,
        verbose_name='Nombres (factura)',
    )
    fact_apellidos = models.CharField(
        max_length=120,
        verbose_name='Apellidos (factura)',
    )
    fact_cedula = models.CharField(
        max_length=20,
        verbose_name='Número de cédula (factura)',
    )
    fact_correo = models.EmailField(
        verbose_name='Correo electrónico (factura)',
    )

    # ── Auditoría ────────────────────────────────────────
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comprobante'
        verbose_name_plural = 'Comprobantes'
        ordering = ['-fecha_inscripcion', '-creado']

    @property
    def total_venta(self):
        """Total de la venta = pago/abono + diferencia."""
        from decimal import Decimal
        pago = self.pago_abono or Decimal('0.00')
        dif = self.diferencia or Decimal('0.00')
        return pago + dif

    @property
    def estado_pago(self):
        from decimal import Decimal
        if (self.diferencia or Decimal('0.00')) <= 0:
            return 'Pagado'
        if (self.pago_abono or Decimal('0.00')) > 0:
            return 'Parcial'
        return 'Pendiente'

    def save(self, *args, **kwargs):
        # Si no se guardó el nombre, intentar tomarlo del usuario asociado
        if not self.vendedora_nombre and self.vendedora_id:
            full = f'{self.vendedora.first_name} {self.vendedora.last_name}'.strip()
            self.vendedora_nombre = full or self.vendedora.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Comprobante #{self.pk} — {self.nombre_persona} ({self.curso.nombre})'


# ─────────────────────────────────────────────────────────
# Registro Administrativo: Egresos / Pérdidas
# ─────────────────────────────────────────────────────────

class CategoriaEgreso(models.Model):
    """
    Categoría de gasto/egreso. Se usa para clasificar los egresos
    en el módulo de Registro Administrativo.
    """
    COLORES = [
        ('#c62828', 'Rojo'),
        ('#f0ad4e', 'Naranja'),
        ('#1a237e', 'Azul'),
        ('#2e7d32', 'Verde'),
        ('#6a1b9a', 'Morado'),
        ('#00838f', 'Cian'),
        ('#5d4037', 'Marrón'),
        ('#455a64', 'Gris'),
    ]

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, choices=COLORES, default='#c62828',
    )
    icono = models.CharField(
        max_length=4, blank=True,
        help_text='Emoji corto para mostrar (ej.: 💼, 🏠, 💡, 📦).'
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoría de egreso'
        verbose_name_plural = 'Categorías de egresos'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Egreso(models.Model):
    """
    Cada gasto registrado por el administrador en el módulo
    de Registro Administrativo. Pueden ser sueldos, alquiler,
    comisiones pagadas a asesoras, materiales, etc.
    """

    fecha = models.DateField(
        help_text='Fecha en que se efectuó el gasto.'
    )
    categoria = models.ForeignKey(
        CategoriaEgreso, on_delete=models.PROTECT,
        related_name='egresos',
    )
    concepto = models.CharField(
        max_length=200,
        help_text='Descripción corta del gasto (ej.: "Sueldo Mayo - Ana").'
    )
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Monto del gasto en USD.'
    )
    notas = models.TextField(
        blank=True,
        help_text='Detalles adicionales: nº de factura, beneficiario, referencia, etc.'
    )

    # Auditoría
    registrado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='egresos_registrados',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Egreso'
        verbose_name_plural = 'Egresos'
        ordering = ['-fecha', '-creado']

    def __str__(self):
        return f'{self.fecha} — {self.concepto} (${self.monto})'