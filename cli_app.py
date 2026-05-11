"""
Keysearch Diarrea de Perro
  - Sugerencias de autocompletado
  - People Also Ask
  - Preguntas generadas por autocompletado
  - Busquedas relacionadas
  - Metricas reales de Google Trends cuando estan disponibles
  - Score interno de prioridad para ordenar temas
"""
import os
import re
import sys
import time
import argparse
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pyrefly: ignore [missing-import]
from rich import box
# pyrefly: ignore [missing-import]
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from config import APP_NAME, APP_VERSION, GROQ_API_KEY, SCRAPE_PROFILE, normalize_country
from scraper.categorizer import auto_categorizar

PROFILE_DISPLAY_LABELS = {
    "normal": "Normal Precoz Eyaculation",
    "extreme": "Sex Extreme Toro",
}

console = Console()
_SCRAPERS = None
_EXPORTADORES = None


def _importar_exportadores():
    """Carga exportadores solo cuando realmente se necesitan."""
    global _EXPORTADORES
    if _EXPORTADORES is not None:
        return _EXPORTADORES

    from exporters.excel_export import exportar_excel
    from exporters.json_export import exportar_json

    _EXPORTADORES = (exportar_excel, exportar_json)
    return _EXPORTADORES


def _importar_scrapers():
    """Carga scrapers y metricas despues de mostrar la interfaz."""
    global _SCRAPERS
    if _SCRAPERS is not None:
        return _SCRAPERS

    from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
    from scraper.google_ads_metrics import enrich_with_google_ads_metrics
    from scraper.google_serp import scrape_google
    from scraper.volume_estimator import estimar_volumenes, ordenar_por_volumen

    _SCRAPERS = {
        "get_autocomplete_suggestions": get_autocomplete_suggestions,
        "get_question_suggestions": get_question_suggestions,
        "enrich_with_google_ads_metrics": enrich_with_google_ads_metrics,
        "scrape_google": scrape_google,
        "estimar_volumenes": estimar_volumenes,
        "ordenar_por_volumen": ordenar_por_volumen,
    }
    return _SCRAPERS


def mostrar_banner():
    """Muestra el banner de bienvenida."""
    banner = Text()
    banner.append(APP_NAME, style="bold cyan")
    banner.append("\n")
    banner.append("   Descubre senales reales de demanda sobre cualquier tema", style="dim")
    banner.append("\n")
    banner.append("   HTTP puro + Google Trends + prioridad editorial transparente", style="dim green")
    banner.append("\n")
    banner.append(
        f"   Build: {APP_VERSION} | Perfil: {PROFILE_DISPLAY_LABELS.get(SCRAPE_PROFILE, SCRAPE_PROFILE)}",
        style="bold white",
    )

    console.print(
        Panel(
            banner,
            border_style="bright_cyan",
            padding=(1, 2),
            title=f"[bold white]V {APP_VERSION}[/]",
            title_align="right",
        )
    )
    console.print()


def _parse_keywords(raw_value: str) -> list[str]:
    """Convierte una entrada libre en una lista de keywords sin duplicados."""
    candidates = []
    normalized_value = re.sub(r"[|;]+", ",", raw_value.replace("\r", "").replace("\n", ","))
    for bloque in normalized_value.split(","):
        texto = bloque.strip()
        if texto:
            candidates.append(texto)

    keywords = []
    vistas = set()
    for item in candidates:
        key = item.lower()
        if key not in vistas:
            vistas.add(key)
            keywords.append(item)
    return keywords


def _solicitar_keywords() -> list[str]:
    """Solicita multiples keywords al usuario de forma amigable para CMD."""
    console.print(
        Panel(
            "[bold]Ingresa una o varias keywords.[/]\n"
            "Puedes usar cualquiera de estas formas:\n"
            "  - Una keyword por linea\n"
            "  - Varias separadas por coma\n"
            "  - Varias separadas por |\n\n"
            "Ejemplos:\n"
            "  marketing digital\n"
            "  salud canina\n"
            "  perros con sangre | vomito perro | diarrea perro\n\n"
            "Deja una linea vacia para comenzar la busqueda.",
            border_style="bright_cyan",
            title="[bold]Keywords del lote[/]",
        )
    )

    lineas = []
    while True:
        linea = console.input("  Keyword: ").strip()
        if not linea:
            break
        lineas.append(linea)

    return _parse_keywords("\n".join(lineas))


def _solicitar_modo_busqueda() -> str:
    """Permite elegir entre busqueda individual o por lote."""
    console.print(
        Panel(
            "[bold]Selecciona el modo de trabajo:[/]\n"
            "  [cyan]1[/] -> Busqueda individual\n"
            "  [cyan]2[/] -> Busqueda por lote",
            border_style="bright_cyan",
            title="[bold]Modo de busqueda[/]",
        )
    )
    return Prompt.ask("  Seleccione una opcion", choices=["1", "2"], default="1")


def _solicitar_keyword_individual() -> list[str]:
    """Solicita una sola keyword."""
    keyword = Prompt.ask("[bold cyan]Ingrese una palabra clave[/]").strip()
    return [keyword] if keyword else []


def _solicitar_contexto_busqueda() -> dict:
    """Pide el contexto geografico de la corrida.

    Categoria y subcategoria se detectan automaticamente por keyword
    — no se le pregunta al usuario.
    """
    raw_country = Prompt.ask(
        "[bold cyan]Pais o codigo[/]",
        default="co",
    ).strip()
    country_data = normalize_country(raw_country)

    return {
        "country_code": country_data["country_code"],
        "country_name": country_data["country_name"],
        "language_code": country_data["language_code"],
        "google_ads_geo_targets": country_data["google_ads_geo_targets"],
    }


def _solicitar_perfil_scrape() -> str:
    """Permite elegir el perfil de extraccion."""
    console.print(
        Panel(
            "[bold]Perfil de extraccion:[/]\n"
            "  [cyan]1[/] -> Normal Precoz Eyaculation (equilibrado)\n"
            "  [cyan]2[/] -> Sex Extreme Toro (maxima cobertura, mas lento)",
            border_style="bright_cyan",
            title="[bold]Perfil de scraping[/]",
        )
    )
    opcion = Prompt.ask("  Seleccione una opcion (SOLO UNA, POR FAVOR, NO COLOQUE MÁS DE UNA, ANIMAL)", choices=["1", "2"], default="1")
    return "extreme" if opcion == "2" else "normal"


def _color_score(score: float) -> str:
    """Devuelve el color Rich apropiado para un score."""
    if score >= 80:
        return "bold red"
    if score >= 55:
        return "bold yellow"
    if score >= 30:
        return "cyan"
    if score >= 15:
        return "dim"
    return "dim italic"


def _resumen_dato_real(vol: dict) -> str:
    """Resume la trazabilidad real del item en una sola celda."""
    fuente = vol.get("fuente", "-")
    posicion = vol.get("posicion_fuente")
    promedio = vol.get("google_trends_promedio")
    avg_ads = vol.get("google_ads_avg_monthly_searches")

    partes = [f"{fuente} #{posicion}" if posicion else fuente]
    if avg_ads is not None:
        partes.append(f"Ads {avg_ads}/mes")
    if promedio is not None:
        partes.append(f"GT {promedio}/100")
    return " | ".join(partes)


def _modo_reporte(datos: dict) -> str:
    """Describe el modo metodologico del reporte actual."""
    google_ads = datos.get("google_ads", {}) or {}
    if google_ads.get("enabled") and google_ads.get("keywords_enriched", 0) > 0:
        return "Google Ads + Google Trends + senales observables"
    return "Senales observables + Google Trends"


def _mensaje_google_ads(datos: dict) -> str:
    """Resume el estado de Google Ads de forma legible."""
    google_ads = datos.get("google_ads", {}) or {}
    if google_ads.get("enabled") and google_ads.get("keywords_enriched", 0) > 0:
        return f"Activo: {google_ads.get('keywords_enriched', 0)} keywords enriquecidas"
    reason = google_ads.get("reason") or "No disponible"
    return f"No disponible: {reason}"


def mostrar_sugerencias(sugerencias: list, volumenes: dict):
    """Muestra las sugerencias de autocompletado con sus metricas."""
    if not sugerencias:
        console.print("  [dim]No se encontraron sugerencias.[/]")
        return

    table = Table(
        title="Sugerencias de Autocompletado",
        box=box.ROUNDED,
        border_style="blue",
        title_style="bold blue",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Sugerencia", style="white", min_width=35)
    table.add_column("Ads/mes", justify="center", width=12)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Prioridad", width=12)
    table.add_column("Datos reales", min_width=28)

    for i, sugerencia in enumerate(sugerencias, 1):
        vol = volumenes.get(sugerencia, {})
        score = vol.get("score", 0)
        prioridad = vol.get("categoria", "-")
        ads_avg = vol.get("google_ads_avg_monthly_searches")
        color = _color_score(score)

        table.add_row(
            str(i),
            sugerencia,
            str(ads_avg) if ads_avg is not None else "-",
            f"[{color}]{score}[/]",
            f"[{color}]{prioridad}[/]",
            _resumen_dato_real(vol),
        )

    console.print(table)
    console.print(f"  [dim]Total: {len(sugerencias)} sugerencias[/]\n")


def mostrar_preguntas(
    preguntas: list,
    volumenes: dict,
    titulo: str = "Preguntas Frecuentes",
    color: str = "red",
):
    """Muestra preguntas ordenadas por prioridad."""
    if not preguntas:
        console.print("  [dim]No se encontraron preguntas en esta fuente.[/]")
        return

    ordenadores = _importar_scrapers()
    preguntas_ordenadas = ordenadores["ordenar_por_volumen"](preguntas, volumenes)

    table = Table(
        title=titulo,
        box=box.ROUNDED,
        border_style=color,
        title_style=f"bold {color}",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Pregunta", style="white", min_width=40)
    table.add_column("Ads/mes", justify="center", width=12)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Prioridad", width=12)
    table.add_column("Datos reales", min_width=28)

    for i, pregunta in enumerate(preguntas_ordenadas, 1):
        vol = volumenes.get(pregunta, {})
        score = vol.get("score", 0)
        prioridad = vol.get("categoria", "-")
        ads_avg = vol.get("google_ads_avg_monthly_searches")
        score_color = _color_score(score)

        table.add_row(
            str(i),
            pregunta,
            str(ads_avg) if ads_avg is not None else "-",
            f"[{score_color}]{score}[/]",
            f"[{score_color}]{prioridad}[/]",
            _resumen_dato_real(vol),
        )

    console.print(table)
    console.print(f"  [dim]Total: {len(preguntas)} preguntas ordenadas por prioridad[/]\n")


def mostrar_relacionadas(relacionadas: list, volumenes: dict):
    """Muestra las busquedas relacionadas con sus metricas."""
    if not relacionadas:
        console.print("  [dim]No se encontraron busquedas relacionadas.[/]")
        return

    ordenadores = _importar_scrapers()
    relacionadas_ordenadas = ordenadores["ordenar_por_volumen"](relacionadas, volumenes)

    table = Table(
        title="Busquedas Relacionadas",
        box=box.ROUNDED,
        border_style="green",
        title_style="bold green",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Busqueda", style="white", min_width=35)
    table.add_column("Ads/mes", justify="center", width=12)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Prioridad", width=12)
    table.add_column("Datos reales", min_width=28)

    for i, busqueda in enumerate(relacionadas_ordenadas, 1):
        vol = volumenes.get(busqueda, {})
        score = vol.get("score", 0)
        prioridad = vol.get("categoria", "-")
        ads_avg = vol.get("google_ads_avg_monthly_searches")
        score_color = _color_score(score)

        table.add_row(
            str(i),
            busqueda,
            str(ads_avg) if ads_avg is not None else "-",
            f"[{score_color}]{score}[/]",
            f"[{score_color}]{prioridad}[/]",
            _resumen_dato_real(vol),
        )

    console.print(table)
    console.print(f"  [dim]Total: {len(relacionadas)} busquedas relacionadas[/]\n")


def mostrar_resumen(keyword: str, datos: dict):
    """Muestra un resumen estadistico."""
    n_sug = len(datos.get("sugerencias", []))
    n_paa = len(datos.get("preguntas_paa", []))
    n_preg = len(datos.get("preguntas_autocompletado", []))
    n_rel = len(datos.get("busquedas_relacionadas", []))
    total = n_sug + n_paa + n_preg + n_rel
    volumenes = datos.get("volumenes", {})
    con_trends = sum(1 for item in volumenes.values() if item.get("google_trends_promedio") is not None)
    con_ads = sum(1 for item in volumenes.values() if item.get("google_ads_avg_monthly_searches") is not None)

    resumen = Table(
        title=f"Resumen para: [bold]{keyword}[/]",
        box=box.DOUBLE_EDGE,
        border_style="yellow",
        title_style="bold yellow",
    )
    resumen.add_column("Categoria", style="bold", min_width=35)
    resumen.add_column("Cantidad", justify="center", style="cyan", min_width=10)

    resumen.add_row("Pais analizado", datos.get("country_name", "-"))
    resumen.add_row("Categoria editorial", datos.get("category_name", "-"))
    resumen.add_row("Subcategoria editorial", datos.get("subcategory_name", "-"))
    resumen.add_row("Sugerencias de autocompletado", str(n_sug))
    resumen.add_row("Preguntas frecuentes (PAA)", str(n_paa))
    resumen.add_row("Preguntas por autocompletado", str(n_preg))
    resumen.add_row("Busquedas relacionadas", str(n_rel))
    resumen.add_row("Modo del reporte", _modo_reporte(datos))
    resumen.add_row("Estado Google Ads", _mensaje_google_ads(datos))
    resumen.add_row("Keywords con Google Ads", str(con_ads))
    resumen.add_row("Keywords con Google Trends", str(con_trends))
    resumen.add_row("-" * 35, "-" * 10)
    resumen.add_row("[bold]TOTAL[/]", f"[bold]{total}[/]")

    console.print(resumen)
    console.print()
    console.print(
        Panel(
            "[dim]Este reporte muestra solo datos trazables:\n"
            "  - Posicion real dentro de la fuente donde se encontro cada termino\n"
            "  - Google Ads promedio mensual real cuando hay configuracion valida\n"
            "  - Fuente real de Google: Autocompletado, PAA o relacionadas\n"
            "  - Google Trends 0-100 cuando pytrends devuelve datos\n\n"
            "El score es una prioridad interna para ordenar ideas, no un volumen mensual exacto.[/]",
            border_style="dim",
            title="[dim]Metodologia honesta[/]",
            padding=(0, 1),
        )
    )
    console.print(
        Panel(
            "[dim]Lectura recomendada para cliente:\n"
            "  - Muy alta / Alta = temas que vale la pena validar primero\n"
            "  - Media = temas utiles para ampliar cobertura\n"
            "  - Baja / Muy baja = oportunidades secundarias o nichos concretos\n\n"
            "Usa este reporte para priorizar contenido e investigacion, no para proyectar ingresos o presupuestos de medios.[/]",
            border_style="dim",
            title="[dim]Como presentarlo[/]",
            padding=(0, 1),
        )
    )
    console.print()


def buscar_keyword(keyword: str, search_context: dict, editorial_context: dict) -> dict:
    """Ejecuta la busqueda completa para una palabra clave."""
    scrapers = _importar_scrapers()
    datos = {
        "country_code": search_context.get("country_code", ""),
        "country_name": search_context.get("country_name", ""),
        "language_code": search_context.get("language_code", "es"),
        "category_name": editorial_context.get("category_name", ""),
        "subcategory_name": editorial_context.get("subcategory_name", ""),
        "reference_keyword": keyword,
    }
    console.print()

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Obteniendo sugerencias de autocompletado...", total=None)
        sugerencias = scrapers["get_autocomplete_suggestions"](
            keyword,
            expandir=True,
            search_context=search_context,
        )
        datos["sugerencias"] = sugerencias
        progress.update(task, description=f"OK {len(sugerencias)} sugerencias encontradas")
        time.sleep(0.3)

    console.print(f"  [green]OK[/] [bold]{len(sugerencias)}[/] sugerencias de autocompletado\n")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold magenta]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Generando preguntas por autocompletado...", total=None)
        preguntas_ac = scrapers["get_question_suggestions"](keyword, search_context=search_context)
        datos["preguntas_autocompletado"] = preguntas_ac
        progress.update(task, description=f"OK {len(preguntas_ac)} preguntas generadas")
        time.sleep(0.3)

    console.print(f"  [green]OK[/] [bold]{len(preguntas_ac)}[/] preguntas por autocompletado\n")

    def progress_cb(msg):
        console.print(f"  [dim]-> {msg}[/]")

    console.print("  [bold yellow]Extrayendo datos de la SERP de Google...[/]")
    console.print("  [dim](Peticion HTTP directa, sin abrir navegador)[/]\n")

    serp_data = scrapers["scrape_google"](
        keyword,
        progress_callback=progress_cb,
        search_context=search_context,
    )
    datos["preguntas_paa"] = serp_data.get("preguntas_paa", [])
    datos["busquedas_relacionadas"] = serp_data.get("busquedas_relacionadas", [])

    n_paa = len(datos["preguntas_paa"])
    n_rel = len(datos["busquedas_relacionadas"])
    console.print(f"\n  [green]OK[/] [bold]{n_paa}[/] preguntas PAA de la SERP")
    console.print(f"  [green]OK[/] [bold]{n_rel}[/] busquedas relacionadas\n")

    if GROQ_API_KEY:
        console.print("  [bold yellow]Filtrando resultados con IA (Groq)...[/]")
        from scraper.ai_filter import filtrar_con_ia

        def _aplicar_filtro_ia(nombre, lista):
            if not lista:
                return lista
            console.print(f"  [dim]-> Filtrando {len(lista)} {nombre}...[/]")
            filtrados = filtrar_con_ia(lista, keyword, search_context.get("country_name", "Colombia"))
            console.print(f"  [dim]   Mantenidos:[/] [bold]{len(filtrados)}[/] / {len(lista)}")
            return filtrados

        datos["sugerencias"] = _aplicar_filtro_ia("sugerencias", datos["sugerencias"])
        datos["preguntas_autocompletado"] = _aplicar_filtro_ia("preguntas ac", datos["preguntas_autocompletado"])
        datos["preguntas_paa"] = _aplicar_filtro_ia("preguntas PAA", datos["preguntas_paa"])
        datos["busquedas_relacionadas"] = _aplicar_filtro_ia("relacionadas", datos["busquedas_relacionadas"])
    else:
        console.print("  [yellow]INFO[/] Filtro IA omitido: falta GROQ_API_KEY\n")

    console.print("\n  [bold yellow]Analizando senales reales de Google...[/]\n")

    def vol_cb(msg):
        console.print(f"  [dim]-> {msg}[/]")

    volumenes = scrapers["estimar_volumenes"](
        keyword_principal=keyword,
        sugerencias=datos["sugerencias"],
        preguntas_paa=datos["preguntas_paa"],
        preguntas_autocompletado=datos["preguntas_autocompletado"],
        busquedas_relacionadas=datos["busquedas_relacionadas"],
        usar_trends=True,
        progress_callback=vol_cb,
        metadata={
            "categoria_padre": editorial_context.get("category_name", ""),
            "subcategoria": editorial_context.get("subcategory_name", ""),
            "referencia": keyword,
            "pais": search_context.get("country_name", ""),
            "pais_codigo": search_context.get("country_code", ""),
            "google_ads_geo_targets": search_context.get("google_ads_geo_targets", []),
        },
        search_context=search_context,
    )

    console.print("\n  [bold yellow]Intentando enriquecer con Google Ads API...[/]\n")
    google_ads_result = scrapers["enrich_with_google_ads_metrics"](volumenes, progress_callback=vol_cb)
    datos["volumenes"] = volumenes
    datos["google_ads"] = google_ads_result

    categorias = {}
    for metrica in volumenes.values():
        categoria = metrica.get("categoria", "-")
        categorias[categoria] = categorias.get(categoria, 0) + 1

    console.print(f"\n  [green]OK[/] Metricas reales analizadas para [bold]{len(volumenes)}[/] keywords")
    if google_ads_result.get("enabled"):
        console.print(
            f"  [green]OK[/] Google Ads enriquecio [bold]{google_ads_result.get('keywords_enriched', 0)}[/] keywords"
        )
    else:
        console.print(f"  [yellow]INFO[/] Reporte en modo sin Google Ads: {google_ads_result.get('reason')}")
    for categoria, count in sorted(categorias.items(), key=lambda item: item[1], reverse=True):
        console.print(f"     {categoria}: {count}")
    console.print()

    return datos


def menu_exportar(keyword: str, datos: dict):
    """Muestra el menu de exportacion."""
    exportar_excel, exportar_json = _importar_exportadores()
    console.print(
        Panel(
            "[bold]Opciones de exportacion:[/]\n"
            "  [cyan]1[/] -> Exportar a Excel (.xlsx)\n"
            "  [cyan]2[/] -> Exportar a JSON (.json)\n"
            "  [cyan]3[/] -> Exportar ambos\n"
            "  [cyan]0[/] -> No exportar",
            border_style="bright_cyan",
            title="[bold]Guardar resultados[/]",
        )
    )

    opcion = Prompt.ask("  Seleccione una opcion", choices=["0", "1", "2", "3"], default="1")

    if opcion in ("1", "3"):
        try:
            ruta = exportar_excel(keyword, datos)
            console.print(f"\n  [green]OK Excel guardado:[/] [bold]{ruta}[/]")
        except Exception as exc:
            console.print(f"\n  [red]Error exportando Excel:[/] {exc}")

    if opcion in ("2", "3"):
        try:
            ruta = exportar_json(keyword, datos)
            console.print(f"\n  [green]OK JSON guardado:[/] [bold]{ruta}[/]")
        except Exception as exc:
            console.print(f"\n  [red]Error exportando JSON:[/] {exc}")

    if opcion == "0":
        console.print("  [dim]Exportacion omitida.[/]")

    console.print()


def main():
    """Punto de entrada principal."""
    console.clear()
    mostrar_banner()

    while True:
        modo = _solicitar_modo_busqueda()
        keywords = _solicitar_keyword_individual() if modo == "1" else _solicitar_keywords()
        if not keywords:
            console.print("  [red]Debe ingresar al menos una palabra clave.[/]\n")
            continue

        contexto = _solicitar_contexto_busqueda()
        perfil = _solicitar_perfil_scrape()
        contexto["scrape_profile"] = perfil
        perfil_etiqueta = PROFILE_DISPLAY_LABELS.get(perfil, perfil)

        console.print(
            f"\n  Lote: [bold]{len(keywords)}[/] keyword(s) | "
            f"Pais: [bold yellow]{contexto['country_name']} ({contexto['country_code'].upper()})[/] | "
            f"Perfil: [bold magenta]{perfil_etiqueta}[/]\n"
        )

        for indice, keyword in enumerate(keywords, 1):
            console.print(f"  Analizando [bold yellow]{keyword}[/] ({indice}/{len(keywords)})\n")
            console.rule(style="dim")

            categoria, subcategoria = auto_categorizar(keyword)
            console.print(
                f"  [dim]Categoria detectada automaticamente:[/] "
                f"[bold cyan]{categoria}[/] / [cyan]{subcategoria}[/]\n"
            )

            editorial_context = {
                "category_name": categoria,
                "subcategory_name": subcategoria,
            }

            datos = buscar_keyword(keyword, contexto, editorial_context)
            volumenes = datos.get("volumenes", {})

            console.rule("[bold]Resultados[/]", style="bright_cyan")
            console.print()

            mostrar_sugerencias(datos.get("sugerencias", []), volumenes)
            mostrar_preguntas(
                datos.get("preguntas_paa", []),
                volumenes,
                "Preguntas Frecuentes (People Also Ask - SERP)",
                "red",
            )
            mostrar_preguntas(
                datos.get("preguntas_autocompletado", []),
                volumenes,
                "Preguntas Frecuentes (Autocompletado)",
                "magenta",
            )
            mostrar_relacionadas(datos.get("busquedas_relacionadas", []), volumenes)
            mostrar_resumen(keyword, datos)

            menu_exportar(keyword, datos)

            console.rule(style="dim")

        if not Confirm.ask("[bold]Desea buscar otra palabra clave?[/]", default=True):
            console.print("\n  [bold cyan]Hasta luego![/]\n")
            break

        console.clear()
        mostrar_banner()


def _cargar_keywords_archivo(path: str) -> list[str]:
    if not path:
        return []

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    _, ext = os.path.splitext(path.lower())
    if ext == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as file_handle:
            reader = csv.reader(file_handle)
            rows = [row for row in reader if row]
        values = [row[0] for row in rows if row and row[0] and not row[0].strip().startswith("#")]
        return _parse_keywords(",".join(values))

    with open(path, "r", encoding="utf-8") as file_handle:
        lines = [line.strip() for line in file_handle.readlines()]
    lines = [line for line in lines if line and not line.startswith("#")]
    return _parse_keywords("\n".join(lines))


def _parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--keyword", action="append", default=[], help="Keyword individual (repetible).")
    parser.add_argument("--keywords", default="", help="Lista separada por coma.")
    parser.add_argument("--file", default="", help="Archivo .txt o .csv con keywords.")
    parser.add_argument("--country", default="co", help="Pais o codigo (ej. co, mx, Colombia).")
    parser.add_argument("--profile", choices=["normal", "extreme"], default=SCRAPE_PROFILE)
    parser.add_argument("--export", choices=["excel", "json", "both", "none"], default="excel")
    parser.add_argument("--no-display", action="store_true", help="No imprime tablas, solo ejecuta y exporta.")
    return parser.parse_args(argv)


def _ejecutar_cli(args) -> int:
    keywords = []
    if args.keywords:
        keywords.extend(_parse_keywords(args.keywords))
    if args.keyword:
        keywords.extend([kw.strip() for kw in args.keyword if kw and kw.strip()])
    if args.file:
        keywords.extend(_cargar_keywords_archivo(args.file))

    keywords = _parse_keywords(",".join(keywords))
    if not keywords:
        raise ValueError("No se encontraron keywords. Usa --keyword, --keywords o --file.")

    country_data = normalize_country(args.country)
    contexto = {
        "country_code": country_data["country_code"],
        "country_name": country_data["country_name"],
        "language_code": country_data["language_code"],
        "google_ads_geo_targets": country_data["google_ads_geo_targets"],
        "scrape_profile": (args.profile or SCRAPE_PROFILE).strip().lower(),
    }

    exportar_excel, exportar_json = _importar_exportadores()
    profile_label = PROFILE_DISPLAY_LABELS.get(contexto["scrape_profile"], contexto["scrape_profile"])

    console.print(
        f"\n  Lote: [bold]{len(keywords)}[/] keyword(s) | "
        f"Pais: [bold yellow]{contexto['country_name']} ({contexto['country_code'].upper()})[/] | "
        f"Perfil: [bold magenta]{profile_label}[/]\n"
    )

    for indice, keyword in enumerate(keywords, 1):
        if not args.no_display:
            console.print(f"  Analizando [bold yellow]{keyword}[/] ({indice}/{len(keywords)})\n")
            console.rule(style="dim")

        categoria, subcategoria = auto_categorizar(keyword)
        editorial_context = {"category_name": categoria, "subcategory_name": subcategoria}
        datos = buscar_keyword(keyword, contexto, editorial_context)
        volumenes = datos.get("volumenes", {})

        if not args.no_display:
            console.rule("[bold]Resultados[/]", style="bright_cyan")
            console.print()
            mostrar_sugerencias(datos.get("sugerencias", []), volumenes)
            mostrar_preguntas(
                datos.get("preguntas_paa", []),
                volumenes,
                "Preguntas Frecuentes (People Also Ask - SERP)",
                "red",
            )
            mostrar_preguntas(
                datos.get("preguntas_autocompletado", []),
                volumenes,
                "Preguntas Frecuentes (Autocompletado)",
                "magenta",
            )
            mostrar_relacionadas(datos.get("busquedas_relacionadas", []), volumenes)
            mostrar_resumen(keyword, datos)

        if args.export in ("excel", "both"):
            ruta = exportar_excel(keyword, datos)
            console.print(f"\n  [green]OK Excel guardado:[/] [bold]{ruta}[/]")

        if args.export in ("json", "both"):
            ruta = exportar_json(keyword, datos)
            console.print(f"\n  [green]OK JSON guardado:[/] [bold]{ruta}[/]")

        if not args.no_display:
            console.rule(style="dim")

    return 0


if __name__ == "__main__":
    try:
        args = _parse_args()
        if args.keyword or args.keywords or args.file:
            _ejecutar_cli(args)
        else:
            main()
    except KeyboardInterrupt:
        console.print("\n\n  [bold cyan]Hasta luego![/]\n")
        sys.exit(0)
