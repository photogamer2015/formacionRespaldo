from django import forms
from .models import Abono, CategoriaEgreso, Categoria, Comprobante, Curso, Egreso, Estudiante, JornadaCurso, Matricula


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'color', 'orden', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej.: Vacacionales'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'color': forms.Select(attrs={'class': 'form-input'}),
            'orden': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = [
            'categoria', 'nombre', 'descripcion',
            'ofrece_presencial', 'valor_presencial',
            'ofrece_online', 'valor_online',
            'duracion', 'activo',
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-input', 'id': 'id_categoria'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'valor_presencial': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'valor_online': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'duracion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej.: 3 meses, 40 horas…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(activo=True)
        self.fields['categoria'].empty_label = '— Selecciona categoría —'

    def clean(self):
        cleaned = super().clean()
        ofrece_pres = cleaned.get('ofrece_presencial')
        ofrece_onl = cleaned.get('ofrece_online')
        if not ofrece_pres and not ofrece_onl:
            raise forms.ValidationError(
                'Debes seleccionar al menos una modalidad (presencial u online).'
            )
        return cleaned


class JornadaCursoForm(forms.ModelForm):
    class Meta:
        model = JornadaCurso
        fields = [
            'modalidad', 'descripcion', 'fecha_inicio', 'ciudad', 'activo',
        ]
        widgets = {
            'modalidad': forms.Select(attrs={'class': 'form-input'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej.: Sábados intensivos'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej.: Guayaquil — o "Zoom" si es online'
            }),
        }


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = [
            'cedula', 'apellidos', 'nombres', 'edad',
            'correo', 'celular', 'nivel_formacion',
            'titulo_profesional', 'ciudad',
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0102030405'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-input'}),
            'nombres': forms.TextInput(attrs={'class': 'form-input'}),
            'edad': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 120}),
            'correo': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'correo@ejemplo.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0991234567'}),
            'nivel_formacion': forms.Select(attrs={'class': 'form-input'}),
            'titulo_profesional': forms.TextInput(attrs={'class': 'form-input'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-input'}),
        }


class MatriculaForm(forms.ModelForm):
    """
    Formulario de matrícula. Recibe `modalidad` (presencial/online) en __init__
    para filtrar cursos y jornadas.
    """

    class Meta:
        model = Matricula
        fields = [
            'curso', 'jornada',
            'fecha_matricula', 'talla_camiseta',
            'valor_curso', 'valor_pagado', 'observaciones',
        ]
        widgets = {
            'curso': forms.Select(attrs={'class': 'form-input', 'id': 'id_curso'}),
            'jornada': forms.RadioSelect(attrs={'class': 'jornada-radio'}),
            'fecha_matricula': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'talla_camiseta': forms.RadioSelect(attrs={'class': 'talla-radio'}),
            'valor_curso': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'id': 'id_valor_curso'}),
            'valor_pagado': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'readonly': True}),
            'observaciones': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

    def __init__(self, *args, modalidad='presencial', **kwargs):
        super().__init__(*args, **kwargs)
        self.modalidad = modalidad
        
        self.fields['valor_pagado'].initial = 0.00
        self.fields['valor_pagado'].help_text = "Los pagos se registran posteriormente en la sección de Abonos."
        
        # Filtrar cursos: solo los que ofrecen esta modalidad y están activos
        if modalidad == 'online':
            curso_qs = Curso.objects.filter(activo=True, ofrece_online=True)
        else:
            curso_qs = Curso.objects.filter(activo=True, ofrece_presencial=True)
        self.fields['curso'].queryset = curso_qs
        self.fields['curso'].empty_label = '— Selecciona un curso —'

        # Filtrar jornadas según el curso e instancia
        if self.instance and self.instance.pk and self.instance.curso_id:
            self.fields['jornada'].queryset = JornadaCurso.objects.filter(
                curso_id=self.instance.curso_id,
                modalidad=modalidad,
                activo=True,
            )
        else:
            self.fields['jornada'].queryset = JornadaCurso.objects.filter(
                modalidad=modalidad, activo=True,
            )

        self.fields['jornada'].required = False
        self.fields['talla_camiseta'].required = False


class AbonoForm(forms.ModelForm):
    """Formulario para registrar/editar un abono."""

    class Meta:
        model = Abono
        fields = [
            'fecha', 'monto', 'metodo', 'banco',
            'numero_recibo', 'observaciones',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0.01',
                'placeholder': '0.00',
            }),
            'metodo': forms.Select(attrs={'class': 'form-input', 'id': 'id_metodo'}),
            'banco': forms.Select(attrs={'class': 'form-input', 'id': 'id_banco'}),
            'numero_recibo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Se genera automáticamente si lo dejas vacío',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 2,
                'placeholder': 'Detalles del pago, referencia bancaria, etc.',
            }),
        }
        labels = {
            'numero_recibo': 'Nº de recibo',
            'banco': 'Banco',
        }

    def __init__(self, *args, matricula=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.matricula = matricula
        self.fields['numero_recibo'].required = False
        self.fields['banco'].required = False
        self.fields['banco'].empty_label = '— Selecciona un banco —'

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto

    def clean(self):
        cleaned = super().clean()
        monto = cleaned.get('monto')
        metodo = cleaned.get('metodo')
        banco = cleaned.get('banco')

        # Si pagó con transferencia, exigir banco
        if metodo == 'transferencia' and not banco:
            self.add_error(
                'banco',
                'Selecciona el banco usado para la transferencia.'
            )

        # Si no es transferencia, no guardar banco aunque venga seleccionado
        if metodo != 'transferencia':
            cleaned['banco'] = ''

        if self.matricula and monto:
            from decimal import Decimal
            valor_curso = self.matricula.valor_curso or Decimal('0.00')
            otros = self.matricula.abonos.all()
            if self.instance and self.instance.pk:
                otros = otros.exclude(pk=self.instance.pk)
            total_otros = sum((a.monto for a in otros), Decimal('0.00'))
            if total_otros + monto > valor_curso:
                disponible = valor_curso - total_otros
                raise forms.ValidationError(
                    f'El monto excede el saldo. Máximo permitido: ${disponible:.2f} '
                    f'(valor curso ${valor_curso:.2f} − ya pagado ${total_otros:.2f}).'
                )
        return cleaned


# ─────────────────────────────────────────────────────────
# Comprobante de Venta
# ─────────────────────────────────────────────────────────

class ComprobanteForm(forms.ModelForm):
    """
    Formulario de Comprobante de Venta.
    TODOS los campos son obligatorios (según requerimiento).
    El campo `vendedora` NO se incluye: se asigna automáticamente
    desde request.user en la vista.
    """

    class Meta:
        model = Comprobante
        fields = [
            'curso', 'modalidad', 'fecha_inscripcion',
            'nombre_persona', 'celular',
            'tipo_registro',  # <-- CAMPO NUEVO INTEGRADO AQUÍ
            'pago_abono', 'diferencia',
            'link_comprobante',
            'jornada', 'inicio_curso',
            'factura_realizada',
            'fact_nombres', 'fact_apellidos',
            'fact_cedula', 'fact_correo',
        ]
        widgets = {
            'curso': forms.Select(attrs={
                'class': 'form-input', 'required': 'required',
            }),
            'modalidad': forms.Select(attrs={
                'class': 'form-input', 'required': 'required',
            }),
            'fecha_inscripcion': forms.DateInput(attrs={
                'class': 'form-input', 'type': 'date', 'required': 'required',
            }),
            'nombre_persona': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Nombre completo del cliente',
                'required': 'required',
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '0991234567',
                'required': 'required',
            }),
            'tipo_registro': forms.Select(attrs={
                'class': 'form-input', 'required': 'required',
            }),
            'pago_abono': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0',
                'placeholder': '0.00', 'required': 'required',
            }),
            'diferencia': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0',
                'placeholder': '0.00', 'required': 'required',
            }),
            'link_comprobante': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://… (opcional)',
            }),
            'jornada': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej.: Sábados 08:00–12:00',
                'required': 'required',
            }),
            'inicio_curso': forms.DateInput(attrs={
                'class': 'form-input', 'type': 'date', 'required': 'required',
            }),
            'factura_realizada': forms.Select(attrs={
                'class': 'form-input', 'required': 'required',
            }),
            'fact_nombres': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Nombres del titular de factura',
                'required': 'required',
            }),
            'fact_apellidos': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Apellidos del titular de factura',
                'required': 'required',
            }),
            'fact_cedula': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Cédula / RUC',
                'required': 'required',
            }),
            'fact_correo': forms.EmailInput(attrs={
                'class': 'form-input', 'placeholder': 'correo@ejemplo.com',
                'required': 'required',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo cursos activos
        self.fields['curso'].queryset = Curso.objects.filter(activo=True)
        self.fields['curso'].empty_label = '— Selecciona un curso —'
        self.fields['tipo_registro'].empty_label = '— Selecciona tipo —'

        # Forzar todos los campos como obligatorios EXCEPTO el link del comprobante
        OPCIONALES = {'link_comprobante'}
        for name, field in self.fields.items():
            field.required = name not in OPCIONALES

    def clean_celular(self):
        cel = (self.cleaned_data.get('celular') or '').strip()
        if not cel:
            raise forms.ValidationError('El celular es obligatorio.')
        return cel

    def clean_pago_abono(self):
        valor = self.cleaned_data.get('pago_abono')
        if valor is None or valor < 0:
            raise forms.ValidationError('El pago o abono debe ser un valor válido (≥ 0).')
        return valor

    def clean_diferencia(self):
        valor = self.cleaned_data.get('diferencia')
        if valor is None or valor < 0:
            raise forms.ValidationError('La diferencia debe ser un valor válido (≥ 0).')
        return valor


# ─────────────────────────────────────────────────────────
# Registro Administrativo: Egresos
# ─────────────────────────────────────────────────────────

class EgresoForm(forms.ModelForm):
    """Formulario para registrar/editar un egreso (gasto)."""

    class Meta:
        model = Egreso
        fields = ['fecha', 'categoria', 'concepto', 'monto', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'concepto': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej.: Sueldo Mayo - Ana López',
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0.01',
                'placeholder': '0.00',
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Nº de factura, beneficiario, referencia bancaria…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = CategoriaEgreso.objects.filter(activo=True)
        self.fields['categoria'].empty_label = '— Selecciona categoría —'

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto


class CategoriaEgresoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEgreso
        fields = ['nombre', 'descripcion', 'color', 'icono', 'orden', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'color': forms.Select(attrs={'class': 'form-input'}),
            'icono': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '💼',
                'maxlength': '4',
            }),
            'orden': forms.NumberInput(attrs={'class': 'form-input'}),
        }