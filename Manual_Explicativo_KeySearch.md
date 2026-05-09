# 📖 Manual Explicativo Completo: KeySearch V6.0
**Una guía paso a paso para entender cómo funciona el proyecto (sin saber programar)**

¡Hola! Si estás leyendo esto, es porque quieres entender cómo funciona este proyecto por dentro, pero sin enredarte con código complejo. Este documento está diseñado para explicarte "con plastilina" qué hace cada archivo y cada función de la herramienta.

---

## 1. 🌟 ¿Qué es este proyecto y cómo funciona en resumen?

Este proyecto es como un **investigador privado súper rápido** que contrataste para que averigüe todo lo que la gente está buscando en Google sobre un tema en específico. 

Imagina que le dices: *"Investiga sobre 'comida para perros'"*. 
El programa, en lugar de abrir el navegador de Chrome (lo cual es lento y gasta mucha memoria), hace lo siguiente de forma invisible y a la velocidad de la luz:
1. Va a la barra de búsqueda de Google y empieza a escribir la palabra clave para ver **qué le sugiere Google** (Autocompletado).
2. Agrega palabras como "qué", "cómo", "por qué" para sacar **preguntas comunes**.
3. Revisa la primera página de resultados de Google para robarse la sección de **"Otras personas también preguntan" (PAA)** y **"Búsquedas relacionadas"**.
4. Si tiene conexión a la inteligencia artificial (Groq), le pasa esa lista para **limpiar la basura** y dejar solo lo que sirve para tu país.
5. Luego va a los registros de **Google Trends** y **Google Ads** para ver cuánta gente realmente busca eso y qué tan popular es.
6. Finalmente, agarra toda esa información, la organiza por prioridad (de "Muy alta" a "Muy baja") y te **entrega un reporte en Excel** súper bonito.

Todo esto lo hace simulando ser diferentes personas y navegadores para que Google no se dé cuenta de que es un robot.

---

## 2. 📂 ¿Cómo está organizado el proyecto? (Arquitectura)

Imagínate que el proyecto es una oficina. Cada carpeta y archivo tiene un trabajo específico:

*   **`main.py`**: Es el **Jefe de la oficina**. Es el archivo principal que tú ejecutas. Él no hace el trabajo duro, sino que coordina a los demás.
*   **`config.py`**: Es el **Libro de reglas**. Aquí se guardan las contraseñas, los tiempos de espera, los países y cómo debe comportarse el robot.
*   **`requirements.txt`**: Es la **Lista de compras**. Le dice a la computadora qué herramientas extra necesita descargar para que la oficina funcione.
*   📁 **Carpeta `scraper`**: Son los **Investigadores de campo**. Son los archivos encargados de ir a internet, engañar a Google, extraer la información y procesarla.
*   📁 **Carpeta `exporters`**: Son los **Secretarios**. Agarran la información que trajeron los investigadores y la ponen bonita en un archivo de Excel o JSON.

---

## 3. 🔍 Explicación detallada archivo por archivo

Vamos a entrar a cada oficina a ver qué hacen los empleados (funciones).

### 👔 `main.py` (El Jefe)
Este archivo es lo primero que arranca. Dibuja la interfaz bonita en la pantalla negra (consola) y te hace preguntas.

*   **`mostrar_banner()`**: Dibuja el título bonito del programa cuando lo abres.
*   **`_solicitar_keywords() / _solicitar_modo_busqueda()`**: Son las preguntas que te hace el programa: *"¿Qué quieres buscar?"*, *"¿Una sola palabra o varias?"*.
*   **`_solicitar_contexto_busqueda() / _solicitar_perfil_scrape()`**: Te pregunta para qué país quieres la investigación y qué tan rudo quieres que sea el robot (Perfil Normal o Extremo).
*   **`buscar_keyword()`**: ¡Esta es la función más importante del jefe! Es donde él le da la orden a los investigadores. Les dice: *"Ve y busca el autocompletado"*, luego *"Saca las preguntas"*, luego *"Pásalo por la Inteligencia Artificial"*, y por último *"Busca los datos de Google Ads"*.
*   **Funciones `mostrar_...`** (como `mostrar_sugerencias`): Son las que imprimen las tablitas bonitas en la pantalla negra para que vayas viendo qué encontró.
*   **`menu_exportar()`**: Al final, te pregunta si quieres guardar eso en un Excel o no.

### 📖 `config.py` (El Libro de Reglas)
No tiene "funciones" de acción, sino variables (cajitas donde se guarda información).
*   **Paises e Idiomas (`COUNTRY_CATALOG`)**: Tiene la lista de todos los países de habla hispana y sus códigos.
*   **Disfraces (`USER_AGENTS`)**: Es un armario lleno de disfraces. Contiene identidades falsas (Chrome, Firefox, Mac, Windows). El robot se pone una diferente en cada búsqueda para que Google crea que son personas distintas en computadoras distintas.
*   **Tiempos de espera**: Define cuántos segundos debe esperar el robot entre cada búsqueda para no parecer desesperado y que Google no lo bloquee.
*   **Perfiles (Normal vs Extremo)**: Define que si eliges "Extremo", el robot va a buscar muchísimas más combinaciones de palabras, pero se demorará más.

---

### 🕵️‍♂️ Carpeta `scraper` (Los Investigadores)

#### 1. `google_serp.py` (El Ladrón de la Página de Resultados)
Este es el archivo más complejo. Se encarga de ir a la página principal de Google, buscar tu palabra y robarse los datos sin abrir el navegador.

*   **`_get_random_headers()`**: Va al armario de disfraces (config.py) y se pone uno completo. Imita a la perfección cómo se presenta un navegador real ante Google.
*   **`_crear_sesion()` y `_hacer_request()`**: Es la forma en que toca la puerta de Google. Si Google le da un error (como "estás yendo muy rápido"), esta función tiene la inteligencia de esperar unos segundos, cambiarse el disfraz y volver a intentar.
*   **`_extraer_preguntas_paa_html()`**: Una vez que tiene la página de Google descargada (el código de la página), esta función busca específicamente las cajitas que dicen "Otras personas también preguntan" y saca el texto.
*   **`_extraer_preguntas_paa_autocomplete()`**: Si Google no mostró la cajita de preguntas, esta función usa un plan B: empieza a escribir tu palabra clave junto con "qué", "cómo", "por qué" en la barra de búsqueda para ver qué sugiere Google.
*   **`scrape_google()`**: Es el director de este archivo. Une todo: entra a Google, roba las preguntas de la página, roba las sugerencias y entrega el botín limpio.

#### 2. `autocomplete.py` (El Adivino de la Barra de Búsqueda)
Se encarga exclusivamente de ver qué sugiere la barra de autocompletado de Google.

*   **`_fetch_suggestions()`**: Va a una dirección secreta de Google (un "endpoint") que le devuelve la lista de sugerencias sin tener que cargar toda la página visual de Google.
*   **`get_autocomplete_suggestions()`**: Coge tu palabra clave y empieza a agregarle letras ("palabra a", "palabra b", "palabra c"...) para sacar absolutamente todas las sugerencias posibles que Google tiene guardadas.
*   **`get_question_suggestions()`**: Hace lo mismo, pero agregando palabras como "qué es", "cómo funciona", "ventajas de", etc.

#### 3. `ai_filter.py` (El Filtro Inteligente)
A veces Google entrega resultados que no tienen sentido o que son de otros países. Aquí entra la IA (Groq).

*   **`filtrar_con_ia()`**: Le manda la lista sucia a la Inteligencia Artificial y le dice: *"Mira, estoy buscando esto para Colombia. Borra toda la basura, borra cosas de México o España y devuélveme solo lo que sirva"*.
*   **`generar_bloques_editoriales()`**: Le pide a la IA que, basándose en lo que encontró, se invente posibles títulos, enfoques y subtítulos para que tú puedas escribir un artículo para un blog.

#### 4. `categorizer.py` (El Clasificador Automático)
Acomoda tu palabra clave en una categoría (ej: "Salud", "Deportes").

*   **`_TAXONOMY`**: Es un diccionario gigante que el programa ya tiene aprendido. Sabe que si tu palabra tiene "perro" es de Mascotas, o si tiene "bitcoin" es de Finanzas.
*   **`_puntuar()`**: Le da puntos a tu palabra clave según a qué categoría se parece más.
*   **`auto_categorizar()`**: Simplemente te dice: *"Esta palabra clave pertenece a Negocios y Finanzas"*.

#### 5. `volume_estimator.py` (El Evaluador de Prioridad)
Antes, esta herramienta inventaba cuántas búsquedas al mes tenía una palabra. Ahora es más honesta y calcula un "Puntaje de Prioridad".

*   **`_score_por_posicion()`**: Si una pregunta aparece de primera en Google, le da más puntos que a la que aparece de quinta.
*   **`_categorizar_prioridad()`**: Convierte esos puntos en palabras que entendamos: "Muy Alta", "Alta", "Media", "Baja".
*   **`_obtener_trends_batch()`**: Se conecta a **Google Trends** reales. Le pregunta a Google: *"Del 1 al 100, ¿qué tan popular ha sido esta palabra en los últimos 12 meses?"*.
*   **`estimar_volumenes()`**: Agarra todas las palabras encontradas, les calcula su puntaje, les pega la información de Google Trends y las ordena de la más importante a la menos importante.

#### 6. `google_ads_metrics.py` (El Contador Real)
Si tú tienes una cuenta de Google Ads (donde se paga publicidad), este archivo se conecta ahí.

*   **`enrich_with_google_ads_metrics()`**: Va a tu cuenta de Google Ads y extrae los datos reales, reales y oficiales de cuántas personas buscan algo al mes, cuánto cuesta anunciarse ahí (bid alto y bajo) y qué tanta competencia hay.

#### 7. `utils.py` y `http_cache.py` (Los Ayudantes Generales)
*   **`utils.py`**: Tiene funciones pequeñitas como `limpiar_texto()` (que quita espacios dobles y tildes raras) o `generar_nombre_archivo()` (que le pone la fecha al archivo de Excel para que no se sobreescriba).
*   **`http_cache.py`**: Es la memoria del robot. Si buscaste "perro" hace 5 minutos, y vuelves a buscar "perro", en lugar de ir a Google de nuevo, saca la información de una carpeta temporal (`downloaded_files/cache`) para hacerlo en un segundo y no cansar a Google.

---

### 📝 Carpeta `exporters` (Los Secretarios)

#### 1. `excel_export.py` (El Creador de Excel)
Toma toda la información y la pinta en un Excel.

*   **Variables de Colores (`_DARK`, `_RED`, etc)**: Tiene guardados los códigos de los colores corporativos para pintar el Excel bonito.
*   **`_crear_hoja_resumen()`**: Crea la primera pestaña del Excel. Escribe los títulos propuestos por la IA, el resumen de cuántas palabras encontró y la distribución de prioridades.
*   **`_crear_hoja_datos()`**: Crea las pestañas de abajo (Autocompletado, Preguntas PAA, Relacionadas). Pinta de rojito lo que tiene prioridad "Muy Alta" y de gris lo "Bajo".
*   **`exportar_excel()`**: Es la función que recibe la orden: *"Toma estos datos, crea las hojas usando las funciones de arriba, y guárdalo en la carpeta `outputs`"*.

#### 2. `json_export.py` (Para programadores)
*   **`exportar_json()`**: Hace lo mismo que el Excel, pero lo guarda en un formato de texto especial llamado JSON. A los humanos normales no nos sirve mucho, pero si luego quieres conectar este programa con otra página web o software, el JSON es el idioma que ellos entienden.

---

## 🚀 4. El Viaje de una Palabra (Resumen del flujo)

Para que te quede 100% claro, así es el viaje cuando escribes una palabra en la pantalla negra:

1. El Jefe (`main.py`) te pregunta la palabra. Escribes **"adiestrar perro"**.
2. El Jefe le pregunta al Clasificador (`categorizer.py`) de qué trata esto. Él responde: *"Mascotas / Comportamiento Animal"*.
3. El Jefe llama a los Investigadores:
   - El Adivino (`autocomplete.py`) trae 100 sugerencias ("adiestrar perro para ir al baño", "adiestrar perro no ladrar").
   - El Ladrón (`google_serp.py`) se pone un disfraz, entra a Google, evade bloqueos y trae 15 preguntas reales ("¿Cómo castigar a un perro sin pegarle?").
4. El Jefe le manda toda esa lista sucia al Filtro (`ai_filter.py`). La Inteligencia Artificial borra basura y además inventa títulos para artículos.
5. El Jefe le pasa la lista limpia al Evaluador (`volume_estimator.py`). Él revisa Google Trends, les da puntos y dice: *"La más importante es 'cómo hacer que mi perro haga caca afuera'"*.
6. Si tienes cuenta, el Contador (`google_ads_metrics.py`) añade los números de búsquedas reales al mes.
7. Finalmente, el Jefe le da la orden al Secretario (`excel_export.py`). Él arma un archivo de Excel hermoso, pinta celdas de colores y lo guarda en tu carpeta `outputs`.

¡Y listo! Eso es todo lo que hace el programa bajo el capó. Parecen muchas cosas, pero lo hace en cuestión de segundos.
