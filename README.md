# 📄 Limpiador Profesional de PDFs: Enlaces Web y Marcas de Agua

Herramienta de alto rendimiento para limpiar documentos PDF de forma local, rápida y totalmente segura:
1. **Eliminación inteligente de enlaces web**: Deshabilita hipervínculos clicables a sitios web (`http`, `https`, `www`, `mailto`) o borra visualmente su texto, conservando los enlaces de navegación interna entre páginas.
2. **Eliminación precisa de marcas de agua**: Suprime sellos, anotaciones, marcas de agua diagonales/rotadas, textos de aplicaciones conocidas (*CamScanner, iLovePDF, Smallpdf, Borrador, Confidencial, etc.*) e imágenes de fondo repetitivas.
3. **100% Local y Privado**: Tus documentos no se suben a ningún servidor ni servicio en la nube.

---

## 📁 Estructura del Proyecto

| Archivo / Carpeta | Descripción |
|---|---|
| **`LimpiadorPDF.exe`** | **Ejecutable autónomo para Windows**. Funciona en cualquier PC sin necesidad de tener Python instalado. |
| **`crear_ejecutable.bat`** | Script de un solo clic para compilar o regenerar el ejecutable con PyInstaller. |
| **`clean_pdf.py`** | Código fuente en Python con la lógica de inspección, filtrado y redacción vectorial. |
| **`requirements.txt`** | Lista de librerías requeridas (`pymupdf`, `pillow`). |
| **`.gitignore`** | Reglas para ignorar temporales, binarios pesados (`.exe`) y documentos PDF. |
| **`LICENSE`** | Licencia de código abierto MIT. |
| **`README.md`** | Manual de usuario y documentación técnica completa. |

---

## ⚡ Formas de Uso

### 1. Con el Ejecutable (`LimpiadorPDF.exe`) — *Recomendado (Sin Python)*

No necesitas instalar nada. Tienes dos formas muy sencillas de utilizarlo:

* **Método Arrastrar y Soltar:**
  Arrastra cualquier archivo `.pdf` desde tu explorador de archivos y suéltalo sobre **`LimpiadorPDF.exe`**. Se procesará de inmediato, generará el archivo con el sufijo `_limpio.pdf` y mantendrá la ventana visible con el reporte estadístico.
* **Método Interactivo (Doble Clic):**
  Haz doble clic en **`LimpiadorPDF.exe`**. Se abrirá el asistente en consola que te solicitará la ruta del PDF, analizará el documento y te preguntará las opciones deseadas.
* **Desde la Terminal:**
  ```powershell
  .\LimpiadorPDF.exe documento.pdf
  .\LimpiadorPDF.exe documento.pdf --redact-url-text -o resultado.pdf
  ```

---

### 2. Con el Script de Python (`clean_pdf.py`)

Si prefieres ejecutar directamente el código fuente de Python:

#### Requisitos
Tener instalado Python 3.8 o superior y las dependencias:
```bash
pip install -r requirements.txt
```

#### Modos de Ejecución
* **Modo Interactivo:**
  ```bash
  python clean_pdf.py
  ```

* **Modo Línea de Comandos (CLI / Automatización):**
  ```bash
  # Limpieza básica (enlaces web y marcas de agua estándar)
  python clean_pdf.py mi_documento.pdf

  # Especificar archivo de salida
  python clean_pdf.py mi_documento.pdf -o documento_limpio.pdf

  # Borrar también el texto visible de las URLs (redacción visual completa)
  python clean_pdf.py mi_documento.pdf --redact-url-text

  # Indicar marcas de agua personalizadas
  python clean_pdf.py mi_documento.pdf -w "MI EMPRESA" "CONFIDENCIAL 2026"

  # Eliminar también imágenes de fondo o logotipos repetitivos
  python clean_pdf.py mi_documento.pdf --remove-images

  # Modo silencioso/automático (sin confirmaciones)
  python clean_pdf.py mi_documento.pdf -y
  ```

---

## 🛠️ Parámetros de Línea de Comandos

Tanto `LimpiadorPDF.exe` como `clean_pdf.py` aceptan los siguientes argumentos:

| Parámetro | Tipo | Descripción |
|---|---|---|
| `input_pdf` | Posicional | Ruta del archivo PDF que deseas procesar. |
| `-o`, `--output` | Opción | Ruta donde se guardará el PDF resultante (por defecto: `<nombre>_limpio.pdf`). |
| `-w`, `--watermark-text` | Texto(s) | Una o más palabras clave o frases personalizadas de marcas de agua a eliminar. |
| `--redact-url-text` | Flag | Aplica redacción visual sobre el texto de las URLs (las borra físicamente de la página). |
| `--remove-images` | Flag | Elimina imágenes de fondo o logotipos de marcas de agua repetidos en múltiples páginas. |
| `--all-links` | Flag | Elimina todos los enlaces (incluyendo índices y navegación interna entre páginas). |
| `-v`, `--verbose` | Flag | Muestra el reporte detallado elemento por elemento en cada página. |
| `-y`, `--yes` | Flag | Ejecución desatendida / silenciosa sin confirmaciones interactivas. |

---

## 🔨 Cómo Regenerar el Ejecutable (`.exe`)

Si realizas cambios en `clean_pdf.py` y deseas generar un nuevo ejecutable:

1. Haz doble clic sobre **`crear_ejecutable.bat`**.
2. El script se encargará automáticamente de:
   - Verificar la instalación de Python y PyInstaller.
   - Instalar las dependencias necesarias.
   - Limpiar temporales previos.
   - Compilar el archivo empaquetando todo el motor C/C++ de MuPDF (`--collect-all pymupdf`).
   - Copiar el nuevo `LimpiadorPDF.exe` a la carpeta principal del proyecto.

---

## 🛡️ Detalles Técnicos de Detección y Limpieza

1. **Hipervínculos Web:**
   - Detecta anotaciones de tipo `/Link` (`LINK_URI`) con esquemas `http`, `https`, `www`, `ftp` y `mailto`.
   - Mantiene intactos los enlaces de índices, tablas de contenidos y saltos entre páginas (`LINK_GOTO`).
2. **Anotaciones y Sellos:**
   - Rastrea y purga anotaciones nativas de marcas (`/Watermark`), sellos gráficos (`/Stamp`) y elementos flotantes.
3. **Marcas de Texto:**
   - Analiza matrices de transformación vectorial para identificar textos rotados o diagonales (típicos de marcas de agua en 45°).
   - Emplea coincidencia inteligente de patrones para términos comunes (*Draft, Borrador, CamScanner, Copia, iLovePDF, etc.*) asegurando no remover texto legítimo del contenido.
   - Aplica redacción con limpieza de vectores subyacentes.
4. **Optimización de Archivo:**
   - Al finalizar, compacta el documento mediante recolección de basura de objetos huérfanos (`garbage=4`) y compresión de flujos internos (`deflate=True`), reduciendo frecuentemente el tamaño final del archivo.

---

## 📜 Licencia

Este proyecto se distribuye bajo los términos de la Licencia de Código Abierto **MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.
