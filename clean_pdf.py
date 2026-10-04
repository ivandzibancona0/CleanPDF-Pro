#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpiador Profesional de PDFs: Eliminación de Enlaces Web y Marcas de Agua
Desarrollado para procesar documentos PDF localmente con máxima precisión y seguridad.
"""

import sys
import os
import re
import argparse
from typing import List, Dict, Tuple, Optional, Set

# Asegurar codificación UTF-8 en consolas Windows para evitar errores de Unicode
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import pymupdf  # PyMuPDF
except ImportError:
    print("\n[ERROR] La librería 'pymupdf' no está instalada.")
    print("Instálala ejecutando: pip install pymupdf\n")
    sys.exit(1)

# Palabras clave y patrones de marcas de agua comunes (Español e Inglés)
DEDICATED_WATERMARK_PATTERNS = [
    r'camscanner',
    r'scanned with camscanner',
    r'escaneado con camscanner',
    r'ilovepdf',
    r'smallpdf',
    r'pdfgear',
    r'wondershare',
    r'foxit',
    r'watermark',
    r'marca de agua',
    r'copia no controlada',
    r'do not copy',
    r'no copiar',
    r'evaluation copy',
    r'unregistered',
    r'para evaluaci[oó]n',
    r'versi[oó]n de prueba',
    r'internal use only',
    r'solo uso interno',
]

STANDALONE_WATERMARK_KEYWORDS = [
    'borrador', 'draft', 'confidencial', 'confidential',
    'sample', 'muestra', 'copia', 'copy', 'anulado', 'void',
    'demo', 'preview', 'ejemplo', 'preliminar'
]

URL_REGEX = re.compile(
    r'(?:https?:\/\/|www\.)[^\s<>"\')]+',
    re.IGNORECASE
)

# Colores para la consola (ANSI)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        cls.HEADER = ''
        cls.BLUE = ''
        cls.CYAN = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.BOLD = ''
        cls.DIM = ''
        cls.RESET = ''

# En Windows, activar soporte de secuencias ANSI
if sys.platform == "win32":
    os.system("")


def print_banner():
    """Muestra el encabezado visual de la aplicación."""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 68)
    print("       📄 LIMPIADOR PROFESIONAL DE ARCHIVOS PDF")
    print("   Eliminación de Enlaces Web y Detección de Marcas de Agua")
    print("=" * 68)
    print(f"{Colors.RESET}")


def clean_path_input(path_str: str) -> str:
    """Limpia la ruta ingresada eliminando comillas y espacios en blanco."""
    if not path_str:
        return ""
    p = path_str.strip()
    if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
        p = p[1:-1].strip()
    return os.path.normpath(p)


def is_web_link(link: dict) -> bool:
    """Determina si un enlace de PDF apunta a un sitio o página web."""
    kind = link.get("kind")
    uri = link.get("uri", "") or ""
    
    # pymupdf.LINK_URI representa un hipervínculo web
    if kind == pymupdf.LINK_URI:
        return True
    
    # Comprobar si la URI comienza con protocolo web común
    if re.match(r'^(https?:\/\/|www\.|ftp:\/\/|mailto:)', uri, re.IGNORECASE):
        return True
        
    return False


def is_watermark_text(text: str, is_rotated: bool, font_size: float, is_faint: bool,
                       custom_keywords: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Evalúa si un texto específico corresponde a una marca de agua
    aplicando heurísticas avanzadas de orientación, palabras clave, color y tamaño.
    """
    text_clean = text.strip()
    if not text_clean:
        return False, ""
        
    text_lower = text_clean.lower()
    words = text_clean.split()
    word_count = len(words)

    # 1. Palabras clave personalizadas dadas por el usuario (máxima prioridad)
    if custom_keywords:
        for ckw in custom_keywords:
            ckw_clean = ckw.strip().lower()
            if ckw_clean and ckw_clean in text_lower:
                return True, f"Texto personalizado del usuario: '{ckw.strip()}'"

    # 2. Banners y frases típicas de marcas de agua (CamScanner, iLovePDF, etc.)
    for pattern in DEDICATED_WATERMARK_PATTERNS:
        if re.search(r'\b' + pattern + r'\b', text_lower):
            return True, f"Frase de marca de agua: '{pattern}'"

    # 3. Texto rotado (inclinado/diagonal o vertical en 45°, -45°, etc.)
    if is_rotated:
        return True, "Texto rotado (orientación diagonal/no horizontal)"

    # 4. Palabras clave independientes de marca de agua (ej: BORRADOR, DRAFT, CONFIDENCIAL)
    # Solo califica si es un texto corto/destacado o fuente grande o color tenue,
    # evitando borrar oraciones normales que contengan la palabra de paso.
    for kw in STANDALONE_WATERMARK_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            if word_count <= 3 or font_size >= 24 or is_faint:
                return True, f"Palabra clave de marca: '{kw}' ({word_count} palabras, {font_size:.1f}pt)"

    # 5. Texto de fondo muy grande y con color tenue
    if is_faint and font_size >= 36 and word_count <= 4:
        return True, f"Texto grande tenue de fondo ({font_size:.1f}pt)"

    return False, ""


def inspect_pdf(doc: pymupdf.Document, custom_keywords: Optional[List[str]] = None) -> Dict:
    """
    Escanea el documento PDF para recopilar estadísticas de enlaces y marcas de agua.
    """
    total_web_links = 0
    total_internal_links = 0
    detected_urls: Set[str] = set()
    total_watermark_annots = 0
    text_watermarks: List[Dict] = []
    watermark_images_count = 0

    # Contar frecuencia de imágenes por xref para detectar imágenes de fondo repetitivas
    image_counts: Dict[int, int] = {}
    for page in doc:
        for img in page.get_images():
            xref = img[0]
            image_counts[xref] = image_counts.get(xref, 0) + 1

    for pno, page in enumerate(doc):
        # 1. Enlaces
        for link in page.get_links():
            uri = link.get("uri")
            if is_web_link(link):
                total_web_links += 1
                if uri:
                    detected_urls.add(uri)
            else:
                total_internal_links += 1

        # 2. Anotaciones
        for annot in page.annots():
            subtype = annot.type[1] if isinstance(annot.type, tuple) else ""
            info = annot.info or {}
            annot_text = (info.get("content", "") + " " + info.get("name", "") + " " + info.get("subject", "")).lower()
            if subtype in ["Watermark", "Stamp"] or any(w in annot_text for w in ["watermark", "marca", "draft", "borrador", "approved"]):
                total_watermark_annots += 1

        # 3. Textos
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    dir_ = line.get("dir", (1.0, 0.0))
                    is_rotated = abs(dir_[1]) > 0.05 or abs(dir_[0] - 1.0) > 0.05
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        font_size = span.get("size", 12.0)
                        color = span.get("color", 0)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b_col = color & 255
                        is_faint = (r > 170 and g > 170 and b_col > 170)

                        is_wm, reason = is_watermark_text(text, is_rotated, font_size, is_faint, custom_keywords)
                        if is_wm:
                            text_watermarks.append({
                                "page": pno + 1,
                                "text": text,
                                "reason": reason
                            })

        # 4. Imágenes repetitivas
        for img in page.get_images():
            xref = img[0]
            if image_counts.get(xref, 0) > 1 and len(doc) > 1:
                watermark_images_count += 1

    return {
        "pages": len(doc),
        "total_web_links": total_web_links,
        "total_internal_links": total_internal_links,
        "unique_urls": sorted(list(detected_urls)),
        "watermark_annots": total_watermark_annots,
        "text_watermarks": text_watermarks,
        "watermark_images": watermark_images_count,
        "repeated_image_xrefs": [xref for xref, count in image_counts.items() if count > 1 and len(doc) > 1]
    }


def clean_pdf(
    input_path: str,
    output_path: str,
    remove_all_links: bool = False,
    redact_url_text: bool = False,
    remove_watermark_images: bool = False,
    custom_keywords: Optional[List[str]] = None,
    verbose: bool = False
) -> Dict:
    """
    Ejecuta el proceso completo de limpieza del PDF eliminando enlaces y marcas de agua.
    """
    doc = pymupdf.open(input_path)

    stats = {
        "links_removed": 0,
        "url_texts_redacted": 0,
        "annots_removed": 0,
        "text_watermarks_removed": 0,
        "images_removed": 0,
        "ocg_layers_cleaned": 0,
        "pages_processed": len(doc),
        "urls_list": []
    }

    # Desactivar / limpiar capas OCG con nombres de marcas de agua si existen
    try:
        ocgs = doc.get_ocgs()
        if ocgs:
            for xref, ocg_info in ocgs.items():
                name = ocg_info.get("name", "").lower()
                if any(w in name for w in ["watermark", "marca", "draft", "borrador"]):
                    # Desactivar la capa
                    doc.set_layer(xref, on=False)
                    stats["ocg_layers_cleaned"] += 1
                    if verbose:
                        print(f"  {Colors.DIM}Capa OCG desactivada: {ocg_info.get('name')}{Colors.RESET}")
    except Exception:
        pass

    # Identificar imágenes que se repiten en múltiples páginas
    image_counts: Dict[int, int] = {}
    if remove_watermark_images and len(doc) > 1:
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                image_counts[xref] = image_counts.get(xref, 0) + 1

    for pno, page in enumerate(doc):
        page_num = pno + 1
        page_modified = False

        # -------------------------------------------------------------
        # 1. ELIMINAR ENLACES CLICABLES (Hipervínculos)
        # -------------------------------------------------------------
        links = list(page.get_links())
        for link in links:
            should_remove = False
            uri = link.get("uri", "")

            if remove_all_links:
                should_remove = True
            elif is_web_link(link):
                should_remove = True

            if should_remove:
                page.delete_link(link)
                stats["links_removed"] += 1
                page_modified = True
                if uri:
                    stats["urls_list"].append(uri)
                if verbose:
                    dest = uri if uri else f"Destino tipo {link.get('kind')}"
                    print(f"  {Colors.YELLOW}🔗 [Pág {page_num}] Enlace eliminado: {dest}{Colors.RESET}")

        # -------------------------------------------------------------
        # 2. ELIMINAR ANOTACIONES DE MARCA DE AGUA O SELLOS (STAMPS)
        # -------------------------------------------------------------
        annots = list(page.annots())
        for annot in annots:
            subtype = annot.type[1] if isinstance(annot.type, tuple) else ""
            info = annot.info or {}
            annot_text = (info.get("content", "") + " " + info.get("name", "") + " " + info.get("subject", "")).lower()

            is_wm_annot = (
                subtype in ["Watermark", "Stamp"] or
                any(w in annot_text for w in ["watermark", "marca", "draft", "borrador", "approved", "confidential"])
            )

            if is_wm_annot:
                page.delete_annot(annot)
                stats["annots_removed"] += 1
                page_modified = True
                if verbose:
                    print(f"  {Colors.CYAN}🏷️  [Pág {page_num}] Anotación eliminada: {subtype} ({info.get('name')}){Colors.RESET}")

        # -------------------------------------------------------------
        # 3. ELIMINAR IMÁGENES DE MARCA DE AGUA (SI SE SOLICITÓ)
        # -------------------------------------------------------------
        if remove_watermark_images and len(doc) > 1:
            for img in page.get_images():
                xref = img[0]
                if image_counts.get(xref, 0) > 1:
                    page.delete_image(xref)
                    stats["images_removed"] += 1
                    page_modified = True
                    if verbose:
                        print(f"  {Colors.CYAN}🖼️  [Pág {page_num}] Imagen de fondo/marca eliminada (xref: {xref}){Colors.RESET}")

        # -------------------------------------------------------------
        # 4. DETECTAR Y REDACTAR TEXTO DE MARCAS DE AGUA
        # -------------------------------------------------------------
        text_dict = page.get_text("dict")
        watermarks_to_redact = []

        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    dir_ = line.get("dir", (1.0, 0.0))
                    is_rotated = abs(dir_[1]) > 0.05 or abs(dir_[0] - 1.0) > 0.05
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        font_size = span.get("size", 12.0)
                        color = span.get("color", 0)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b_col = color & 255
                        is_faint = (r > 170 and g > 170 and b_col > 170)

                        is_wm, reason = is_watermark_text(text, is_rotated, font_size, is_faint, custom_keywords)
                        if is_wm:
                            watermarks_to_redact.append((span, is_rotated, text, reason))

        for span, is_rotated, text, reason in watermarks_to_redact:
            # Para texto rotado, aplicar búsqueda palabra por palabra
            # para delimitar áreas exactas y no afectar texto circundante
            words = text.split()
            if is_rotated and len(words) > 1:
                for w in words:
                    quads = page.search_for(w, quads=True)
                    for q in quads:
                        page.add_redact_annot(q, fill=False)
            else:
                page.add_redact_annot(pymupdf.Rect(span["bbox"]), fill=False)

            stats["text_watermarks_removed"] += 1
            page_modified = True
            if verbose:
                print(f"  {Colors.RED}❌ [Pág {page_num}] Marca de agua de texto eliminada: '{text}' ({reason}){Colors.RESET}")

        # -------------------------------------------------------------
        # 5. REDACTAR TEXTO VISIBLE DE LAS URLs (OPCIONAL)
        # -------------------------------------------------------------
        if redact_url_text:
            words = page.get_text("words")
            for w in words:
                word_text = w[4]
                if URL_REGEX.search(word_text):
                    page.add_redact_annot(pymupdf.Rect(w[:4]), fill=False)
                    stats["url_texts_redacted"] += 1
                    page_modified = True
                    if verbose:
                        print(f"  {Colors.YELLOW}✂️  [Pág {page_num}] Texto de URL redactado: '{word_text}'{Colors.RESET}")

        # Aplicar redacciones quirúrgicamente si hubo marcas o textos borrados
        # (images=0, graphics=0 asegura que no borre dibujos vectoriales ni fotos legítimas)
        if page_modified:
            page.apply_redactions(images=0, graphics=0, text=0)

    # Guardar optimizado con recolección de basura
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()

    return stats


def interactive_mode():
    """Ejecución interactiva guiada cuando no se pasan argumentos por consola."""
    print_banner()

    # 1. Solicitar ruta del archivo PDF
    while True:
        try:
            raw_input = input(f"{Colors.BOLD}📂 Ingrese la ruta del archivo PDF (o arrástrelo aquí): {Colors.RESET}")
        except (KeyboardInterrupt, EOFError):
            print("\nOperación cancelada por el usuario.")
            sys.exit(0)

        cleaned_path = clean_path_input(raw_input)
        if not cleaned_path:
            print(f"{Colors.YELLOW}⚠️  Por favor ingrese una ruta válida.{Colors.RESET}")
            continue

        if not os.path.exists(cleaned_path):
            print(f"{Colors.RED}❌ El archivo no existe: '{cleaned_path}'. Intente de nuevo.{Colors.RESET}")
            continue

        if not os.path.isfile(cleaned_path) or not cleaned_path.lower().endswith(".pdf"):
            print(f"{Colors.RED}❌ El archivo seleccionado no parece ser un documento PDF válido.{Colors.RESET}")
            continue

        # Validar apertura
        try:
            doc = pymupdf.open(cleaned_path)
            if doc.is_encrypted:
                password = input(f"{Colors.YELLOW}🔒 El PDF está protegido. Ingrese la contraseña: {Colors.RESET}")
                if not doc.authenticate(password):
                    print(f"{Colors.RED}❌ Contraseña incorrecta. No se pudo abrir el archivo.{Colors.RESET}")
                    doc.close()
                    continue
            doc.close()
            input_file = cleaned_path
            break
        except Exception as e:
            print(f"{Colors.RED}❌ Error al abrir el PDF: {e}. Intente con otro archivo.{Colors.RESET}")

    # 2. Preguntar por palabras clave de marca de agua personalizadas opcionales
    print(f"\n{Colors.CYAN}ℹ️  El limpiador detecta automáticamente marcas de agua comunes (Borrador, Draft,")
    print(f"Confidencial, Copia, CamScanner, iLovePDF, textos diagonales/rotados y sellos).{Colors.RESET}")
    custom_kw_input = input(f"{Colors.BOLD}¿Deseas agregar algún texto o frase específica como marca de agua? (Enter para omitir): {Colors.RESET}").strip()
    custom_keywords = [k.strip() for k in custom_kw_input.split(",") if k.strip()] if custom_kw_input else None

    # 3. Analizar preliminarmente el archivo
    print(f"\n{Colors.BLUE}🔍 Analizando el documento PDF...{Colors.RESET}")
    doc = pymupdf.open(input_file)
    inspection = inspect_pdf(doc, custom_keywords)
    doc.close()

    print(f"\n{Colors.BOLD}--- 📊 REPORTE DE DETECCIÓN PRELIMINAR ---{Colors.RESET}")
    print(f"  • Páginas totales: {Colors.BOLD}{inspection['pages']}{Colors.RESET}")
    print(f"  • Enlaces web detectados: {Colors.BOLD}{Colors.YELLOW}{inspection['total_web_links']}{Colors.RESET}")
    if inspection['unique_urls']:
        print(f"    {Colors.DIM}URLs encontradas:{Colors.RESET}")
        for u in inspection['unique_urls'][:8]:
            print(f"      - {u}")
        if len(inspection['unique_urls']) > 8:
            print(f"      ... y {len(inspection['unique_urls']) - 8} más.")

    print(f"  • Enlaces internos (entre páginas): {inspection['total_internal_links']} {Colors.DIM}(se mantendrán intactos){Colors.RESET}")
    print(f"  • Anotaciones de marca de agua / sellos: {Colors.BOLD}{inspection['watermark_annots']}{Colors.RESET}")
    print(f"  • Textos de marca de agua detectados: {Colors.BOLD}{len(inspection['text_watermarks'])}{Colors.RESET}")
    if inspection['text_watermarks']:
        for tw in inspection['text_watermarks'][:5]:
            print(f"      - [Pág {tw['page']}] \"{tw['text']}\" {Colors.DIM}({tw['reason']}){Colors.RESET}")
        if len(inspection['text_watermarks']) > 5:
            print(f"      ... y {len(inspection['text_watermarks']) - 5} marcas más.")

    if inspection['watermark_images'] > 0:
        print(f"  • Imágenes de fondo repetitivas: {Colors.BOLD}{inspection['watermark_images']}{Colors.RESET}")

    # 4. Opciones de personalización
    print(f"\n{Colors.BOLD}--- ⚙️  CONFIGURACIÓN DEL PROCESAMIENTO ---{Colors.RESET}")
    
    # Preguntar sobre el texto visible de las URLs
    redact_url_text = False
    if inspection['total_web_links'] > 0:
        ans = input(f"{Colors.BOLD}¿Deseas también borrar el texto visible de las URLs del documento? (s/N): {Colors.RESET}").strip().lower()
        redact_url_text = (ans == 's' or ans == 'si' or ans == 'sí' or ans == 'y')

    # Preguntar sobre imágenes de fondo si hay
    remove_images = False
    if inspection['watermark_images'] > 0:
        ans_img = input(f"{Colors.BOLD}Se detectaron imágenes de fondo repetitivas. ¿Deseas eliminarlas? (s/N): {Colors.RESET}").strip().lower()
        remove_images = (ans_img == 's' or ans_img == 'si' or ans_img == 'sí' or ans_img == 'y')

    # 5. Ruta de salida
    base_name, ext = os.path.splitext(input_file)
    default_output = f"{base_name}_limpio{ext}"
    output_input = input(f"{Colors.BOLD}Ruta de salida [{default_output}]: {Colors.RESET}").strip()
    output_file = clean_path_input(output_input) if output_input else default_output

    # 6. Procesar
    print(f"\n{Colors.GREEN}🚀 Procesando documento...{Colors.RESET}")
    stats = clean_pdf(
        input_path=input_file,
        output_path=output_file,
        remove_all_links=False,
        redact_url_text=redact_url_text,
        remove_watermark_images=remove_images,
        custom_keywords=custom_keywords,
        verbose=True
    )

    # 7. Resumen final
    size_before = os.path.getsize(input_file) / 1024
    size_after = os.path.getsize(output_file) / 1024

    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ¡PROCESAMIENTO COMPLETADO CON ÉXITO!{Colors.RESET}")
    print("=" * 68)
    print(f"  • Enlaces web eliminados:        {stats['links_removed']}")
    if redact_url_text:
        print(f"  • Textos de URL borrados:        {stats['url_texts_redacted']}")
    print(f"  • Anotaciones/Sellos eliminados: {stats['annots_removed']}")
    print(f"  • Textos de marca eliminados:    {stats['text_watermarks_removed']}")
    if remove_images:
        print(f"  • Imágenes de marca eliminadas:  {stats['images_removed']}")
    if stats['ocg_layers_cleaned'] > 0:
        print(f"  • Capas OCG desactivadas:        {stats['ocg_layers_cleaned']}")
    print(f"  • Tamaño anterior:               {size_before:.1f} KB")
    print(f"  • Tamaño optimizado:             {size_after:.1f} KB")
    print(f"  • Archivo guardado en:           {Colors.CYAN}{os.path.abspath(output_file)}{Colors.RESET}")
    print("=" * 68 + "\n")
    try:
        input(f"{Colors.DIM}Presione [Enter] para salir...{Colors.RESET}\n")
    except (EOFError, KeyboardInterrupt):
        pass


def cli_mode():
    """Modo línea de comandos para scripting y automatización."""
    parser = argparse.ArgumentParser(
        description="Limpia archivos PDF eliminando enlaces a páginas web y marcas de agua de manera precisa.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python clean_pdf.py documento.pdf
  python clean_pdf.py documento.pdf -o limpio.pdf --redact-url-text
  python clean_pdf.py documento.pdf -w "MI EMPRESA" "CONFIDENCIAL" --remove-images
        """
    )
    parser.add_argument("input_pdf", nargs="?", help="Ruta al archivo PDF a procesar")
    parser.add_argument("-o", "--output", dest="output_pdf", help="Ruta del archivo PDF resultante")
    parser.add_argument("-w", "--watermark-text", dest="custom_watermarks", nargs="+", help="Texto(s) o frase(s) de marca de agua personalizada a eliminar")
    parser.add_argument("--redact-url-text", action="store_true", help="Borra visualmente el texto de las URLs del documento")
    parser.add_argument("--remove-images", action="store_true", help="Elimina imágenes repetitivas de fondo/marca de agua")
    parser.add_argument("--all-links", action="store_true", help="Elimina todos los enlaces (incluyendo saltos de página internos)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra información detallada de cada elemento eliminado")
    parser.add_argument("-y", "--yes", action="store_true", help="Modo silencioso/automático, no solicita confirmación")

    args = parser.parse_args()

    # Si no se pasó argumento de archivo, iniciar modo interactivo
    if not args.input_pdf:
        interactive_mode()
        return

    input_file = clean_path_input(args.input_pdf)
    if not os.path.exists(input_file):
        print(f"{Colors.RED}[ERROR] El archivo no existe: '{input_file}'{Colors.RESET}")
        sys.exit(1)

    base_name, ext = os.path.splitext(input_file)
    output_file = clean_path_input(args.output_pdf) if args.output_pdf else f"{base_name}_limpio{ext}"

    print_banner()
    print(f"Procesando: {Colors.BOLD}{input_file}{Colors.RESET}")
    print(f"Salida:     {Colors.BOLD}{output_file}{Colors.RESET}\n")

    stats = clean_pdf(
        input_path=input_file,
        output_path=output_file,
        remove_all_links=args.all_links,
        redact_url_text=args.redact_url_text,
        remove_watermark_images=args.remove_images,
        custom_keywords=args.custom_watermarks,
        verbose=args.verbose or True
    )

    size_before = os.path.getsize(input_file) / 1024
    size_after = os.path.getsize(output_file) / 1024

    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ¡PDF LIMPIADO CON ÉXITO!{Colors.RESET}")
    print(f"  • Enlaces web eliminados:        {stats['links_removed']}")
    print(f"  • Anotaciones/Sellos eliminados: {stats['annots_removed']}")
    print(f"  • Textos de marca eliminados:    {stats['text_watermarks_removed']}")
    if args.remove_images:
        print(f"  • Imágenes de marca eliminadas:  {stats['images_removed']}")
    print(f"  • Tamaño anterior:               {size_before:.1f} KB")
    print(f"  • Tamaño resultante:             {size_after:.1f} KB")
    print(f"  • Guardado en:                   {Colors.CYAN}{os.path.abspath(output_file)}{Colors.RESET}\n")
    if not args.yes and sys.stdin.isatty():
        try:
            input(f"{Colors.DIM}Presione [Enter] para salir...{Colors.RESET}\n")
        except (EOFError, KeyboardInterrupt):
            pass


if __name__ == "__main__":
    cli_mode()
