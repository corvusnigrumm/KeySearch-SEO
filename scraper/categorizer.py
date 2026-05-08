"""
Clasificador automático de keywords en categorías y subcategorías editoriales.

Usa una taxonomía española embebida y un sistema de puntuación por coincidencia
de palabras clave para asignar la categoría y subcategoría más probable.

No requiere ningún input del usuario — se invoca automáticamente con la
keyword principal de cada búsqueda.
"""
import re
import unicodedata


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomía embebida
# ─────────────────────────────────────────────────────────────────────────────

_TAXONOMY: list[dict] = [
    {
        "categoria": "Mascotas y Animales",
        "keywords": [
            "perro", "perra", "cachorro", "canino", "can", "gato", "gata", "gatito",
            "felino", "mascota", "veterinario", "veterinaria", "animal", "animales",
            "hamster", "conejo", "pajaro", "loro", "pez", "tortuga", "iguana",
            "reptil", "acuario", "pecera", "jaula", "correa", "collar", "pienso",
            "alimento para perro", "alimento para gato", "desparasitar", "vacuna perro",
            "pulgas", "garrapatas", "rabia", "moquillo", "parvo", "leishmaniasis",
        ],
        "subcategorias": [
            ("Salud Canina", ["perro", "perra", "cachorro", "canino", "can", "diarrea perro",
                              "vomito perro", "moquillo", "parvo", "vacuna perro", "pulgas perro"]),
            ("Salud Felina", ["gato", "gata", "gatito", "felino", "leucemia felina", "toxoplasmosis"]),
            ("Veterinaria", ["veterinario", "veterinaria", "clinica veterinaria", "desparasitar",
                             "vacuna", "consulta veterinaria", "cirugia animal"]),
            ("Nutrición Animal", ["pienso", "alimento para", "comida para perro", "comida para gato",
                                  "dieta", "snack animal", "premio mascota"]),
            ("Comportamiento Animal", ["adiestramiento", "entrenamiento perro", "obediencia",
                                       "agresividad", "ansiedad perro", "fobia"]),
            ("Otras mascotas", ["hamster", "conejo", "pajaro", "loro", "pez", "tortuga",
                                "iguana", "reptil", "acuario", "pecera"]),
        ],
    },
    {
        "categoria": "Salud y Bienestar",
        "keywords": [
            "salud", "enfermedad", "sintoma", "sintomas", "dolor", "fiebre", "tos",
            "medicina", "medicamento", "farmaco", "tratamiento", "remedio", "cura",
            "medico", "doctor", "hospital", "clinica", "consulta medica", "diagnostico",
            "operacion", "cirugia", "embarazo", "bebe", "lactancia", "anticonceptivo",
            "presion arterial", "diabetes", "cancer", "covid", "vacuna", "vitamina",
            "suplemento", "dieta", "adelgazar", "bajar de peso", "obesidad", "ansiedad",
            "depresion", "estres", "insomnio", "meditacion", "yoga", "psicologia",
            "terapia", "salud mental", "alcoholismo", "drogadiccion",
        ],
        "subcategorias": [
            ("Enfermedades", ["enfermedad", "sintoma", "diagnostico", "cancer", "diabetes",
                              "presion arterial", "covid", "infeccion", "virus", "bacteria"]),
            ("Medicamentos", ["medicamento", "farmaco", "medicina", "remedio", "pastilla",
                              "antibiotico", "analgesico", "antiinflamatorio", "dosis"]),
            ("Nutrición y Dietas", ["dieta", "adelgazar", "bajar de peso", "obesidad", "vitamina",
                                    "suplemento", "proteina", "calorias", "ayuno"]),
            ("Salud Mental", ["ansiedad", "depresion", "estres", "insomnio", "psicologia",
                              "terapia", "salud mental", "burnout", "fobia", "trauma"]),
            ("Bienestar y Fitness", ["yoga", "meditacion", "ejercicio", "fitness", "bienestar",
                                     "relajacion", "mindfulness", "respiracion"]),
            ("Maternidad y Pediatría", ["embarazo", "bebe", "lactancia", "recien nacido",
                                        "pediatria", "parto", "fertilidad", "anticonceptivo"]),
        ],
    },
    {
        "categoria": "Tecnología y Digital",
        "keywords": [
            "app", "aplicacion", "software", "programa", "hardware", "computadora", "ordenador",
            "pc", "laptop", "portatil", "movil", "celular", "smartphone", "tablet", "ipad",
            "android", "ios", "iphone", "samsung", "windows", "mac", "linux", "internet",
            "wifi", "red", "router", "servidor", "nube", "cloud", "inteligencia artificial",
            "ia", "chatgpt", "machine learning", "automatizacion", "programacion", "codigo",
            "python", "javascript", "html", "css", "web", "pagina web", "sitio web",
            "seo", "marketing digital", "redes sociales", "facebook", "instagram", "tiktok",
            "youtube", "twitter", "linkedin", "whatsapp", "telegram", "discord",
            "videojuego", "consola", "playstation", "xbox", "nintendo",
        ],
        "subcategorias": [
            ("Inteligencia Artificial", ["inteligencia artificial", "ia", "chatgpt", "machine learning",
                                         "deep learning", "automatizacion", "bot", "algoritmo"]),
            ("Desarrollo y Programación", ["programacion", "codigo", "python", "javascript", "html",
                                           "css", "software", "desarrollo web", "api", "base de datos"]),
            ("Dispositivos y Hardware", ["computadora", "laptop", "movil", "celular", "tablet",
                                         "iphone", "samsung", "android", "ios", "hardware", "pc"]),
            ("Redes Sociales", ["facebook", "instagram", "tiktok", "youtube", "twitter", "linkedin",
                                "whatsapp", "telegram", "discord", "red social", "influencer"]),
            ("Videojuegos", ["videojuego", "consola", "playstation", "xbox", "nintendo", "gaming",
                             "gamer", "juego online", "steam", "esports"]),
            ("SEO y Marketing Digital", ["seo", "marketing digital", "posicionamiento web",
                                         "google ads", "sem", "contenido digital", "email marketing"]),
            ("Aplicaciones y Software", ["app", "aplicacion", "programa", "windows", "mac",
                                         "linux", "nube", "cloud", "saas", "servicio online"]),
        ],
    },
    {
        "categoria": "Negocios y Finanzas",
        "keywords": [
            "negocio", "empresa", "emprendimiento", "emprender", "startup", "pyme",
            "inversion", "invertir", "bolsa", "acciones", "criptomoneda", "bitcoin",
            "finanzas", "dinero", "ahorro", "credito", "prestamo", "hipoteca", "banco",
            "tarjeta de credito", "deuda", "presupuesto", "impuesto", "contabilidad",
            "factura", "declaracion de renta", "marketing", "publicidad", "ventas",
            "cliente", "estrategia", "liderazgo", "gestion", "administracion",
            "franquicia", "exportar", "importar", "comercio", "freelance", "consultor",
        ],
        "subcategorias": [
            ("Emprendimiento", ["negocio", "empresa", "emprendimiento", "startup", "pyme",
                                "franquicia", "emprender", "idea de negocio", "plan de negocio"]),
            ("Inversión y Bolsa", ["inversion", "invertir", "bolsa", "acciones", "fondos",
                                   "criptomoneda", "bitcoin", "ethereum", "mercado financiero"]),
            ("Finanzas Personales", ["ahorro", "presupuesto", "deuda", "credito", "prestamo",
                                     "hipoteca", "tarjeta de credito", "finanzas personales"]),
            ("Contabilidad e Impuestos", ["contabilidad", "impuesto", "factura", "declaracion de renta",
                                          "iva", "tributario", "dian", "hacienda", "sat"]),
            ("Marketing y Ventas", ["marketing", "publicidad", "ventas", "cliente", "estrategia",
                                    "marca", "branding", "conversion", "lead", "embudo de ventas"]),
            ("Comercio Internacional", ["exportar", "importar", "comercio", "aduana", "arancel",
                                        "logistica", "cadena de suministro", "distribucion"]),
        ],
    },
    {
        "categoria": "Educación",
        "keywords": [
            "educacion", "aprendizaje", "estudiar", "curso", "carrera", "universidad",
            "colegio", "escuela", "bachillerato", "primaria", "secundaria", "grado",
            "maestria", "doctorado", "posgrado", "beca", "idioma", "ingles", "frances",
            "aleman", "portugues", "certificacion", "diploma", "titulo", "examen",
            "tesis", "investigacion", "lectura", "escritura", "matematicas", "ciencias",
            "historia", "geografia", "filosofia", "literatura", "arte", "musica",
            "educacion online", "e-learning", "plataforma educativa", "mooc",
        ],
        "subcategorias": [
            ("Idiomas", ["idioma", "ingles", "frances", "aleman", "portugues", "mandarin",
                         "aprender idioma", "bilingue", "toefl", "ielts", "traduccion"]),
            ("Formación Online", ["curso online", "e-learning", "plataforma educativa", "mooc",
                                  "udemy", "coursera", "certificacion online", "educacion virtual"]),
            ("Universidades y Carreras", ["universidad", "carrera", "grado", "licenciatura",
                                           "maestria", "doctorado", "posgrado", "beca universitaria"]),
            ("Educación Escolar", ["colegio", "escuela", "bachillerato", "primaria", "secundaria",
                                    "tarea", "deberes", "matematicas", "ciencias", "historia"]),
            ("Pruebas y Exámenes", ["examen", "prueba", "icfes", "psu", "selectividad", "toefl",
                                    "ielts", "gmat", "gre", "certificacion", "titulo"]),
        ],
    },
    {
        "categoria": "Hogar y Familia",
        "keywords": [
            "hogar", "casa", "decoracion", "muebles", "habitacion", "cocina", "bano",
            "sala", "comedor", "jardin", "terraza", "limpieza", "orden", "organizacion",
            "familia", "pareja", "matrimonio", "divorcio", "hijos", "crianza", "educacion hijos",
            "bebe", "embarazo", "guarderia", "colegio", "juguetes", "ropa infantil",
            "electrodomestico", "lavadora", "nevera", "microondas", "aspiradora",
            "reparacion", "plomeria", "electricidad", "pintura casa",
        ],
        "subcategorias": [
            ("Decoración e Interiorismo", ["decoracion", "muebles", "habitacion", "sala", "comedor",
                                            "interiorismo", "estilo", "minimalista", "vintage"]),
            ("Limpieza y Organización", ["limpieza", "orden", "organizacion", "desinfectar",
                                          "limpiar", "productos de limpieza", "konmari"]),
            ("Familia y Crianza", ["familia", "pareja", "matrimonio", "hijos", "crianza",
                                    "educacion hijos", "divorcio", "convivencia"]),
            ("Jardín y Plantas", ["jardin", "planta", "terraza", "balcon", "jardineria",
                                   "semilla", "riego", "fertilizante", "poda"]),
            ("Electrodomésticos y Reparaciones", ["electrodomestico", "lavadora", "nevera",
                                                   "reparacion", "plomeria", "electricidad"]),
        ],
    },
    {
        "categoria": "Alimentación y Recetas",
        "keywords": [
            "receta", "cocinar", "comida", "alimento", "ingrediente", "gastronomia",
            "restaurante", "chef", "cocina", "bebida", "refresco", "jugo", "cafe",
            "te", "cerveza", "vino", "postre", "pastel", "torta", "pan", "pizza",
            "pasta", "arroz", "carne", "pollo", "pescado", "mariscos", "vegano",
            "vegetariano", "sin gluten", "lactosa", "organico", "natural", "dieta",
        ],
        "subcategorias": [
            ("Recetas", ["receta", "cocinar", "preparar", "ingrediente", "paso a paso",
                         "como hacer", "facil rapido", "en casa"]),
            ("Restaurantes y Gastronomía", ["restaurante", "chef", "gastronomia", "cocina gourmet",
                                             "maridaje", "cata", "critica gastronomica"]),
            ("Bebidas", ["bebida", "refresco", "jugo", "cafe", "te", "cerveza", "vino",
                         "coctail", "smoothie", "limonada", "infusion"]),
            ("Alimentación Especial", ["vegano", "vegetariano", "sin gluten", "lactosa",
                                       "organico", "natural", "keto", "paleo", "ayuno"]),
            ("Panadería y Repostería", ["pan", "pastel", "torta", "galleta", "muffin",
                                         "reposteria", "panaderia", "dulce", "postre"]),
        ],
    },
    {
        "categoria": "Viajes y Turismo",
        "keywords": [
            "viaje", "viajar", "turismo", "turista", "destino", "hotel", "hostal",
            "airbnb", "vuelo", "aerolinea", "avion", "aeropuerto", "crucero",
            "tour", "excursion", "guia turistica", "pasaporte", "visa", "documentos viaje",
            "playa", "montana", "selva", "ciudad", "cultural", "mochilero", "viaje barato",
            "viaje de luna de miel", "viaje en familia", "viaje solo", "road trip",
        ],
        "subcategorias": [
            ("Destinos", ["destino", "playa", "montana", "selva", "ciudad", "cultural",
                           "caribe", "europa", "asia", "america latina"]),
            ("Alojamiento", ["hotel", "hostal", "airbnb", "resort", "glamping", "camping",
                              "apartamento turistico", "reserva hotel"]),
            ("Transporte", ["vuelo", "aerolinea", "avion", "aeropuerto", "crucero", "tren",
                             "autobús", "transfer", "alquiler coche", "road trip"]),
            ("Documentación y Visas", ["pasaporte", "visa", "documentos viaje", "tramite viaje",
                                        "seguro de viaje", "requisitos entrada"]),
            ("Presupuesto y Consejos", ["viaje barato", "presupuesto viaje", "ahorrar viaje",
                                         "mochilero", "tips viaje", "consejos viajero"]),
        ],
    },
    {
        "categoria": "Deportes y Actividad Física",
        "keywords": [
            "deporte", "futbol", "baloncesto", "tenis", "natacion", "atletismo", "ciclismo",
            "boxeo", "artes marciales", "yoga", "pilates", "gimnasio", "entrenamiento",
            "ejercicio", "rutina", "fitness", "crossfit", "running", "correr", "maraton",
            "liga", "campeonato", "partido", "equipo", "jugador", "arbitro", "gol",
            "olimpicos", "mundial", "champions", "formula 1", "motociclismo",
        ],
        "subcategorias": [
            ("Fútbol", ["futbol", "gol", "liga", "partido", "equipo", "jugador", "arbitro",
                         "mundial", "champions", "premier", "laliga"]),
            ("Fitness y Entrenamiento", ["gimnasio", "entrenamiento", "ejercicio", "rutina",
                                          "fitness", "crossfit", "pesas", "cardio", "musculacion"]),
            ("Running y Atletismo", ["running", "correr", "maraton", "atletismo", "trail",
                                      "carrera popular", "entrenamiento corredor"]),
            ("Deportes de Agua", ["natacion", "surf", "buceo", "kayak", "remo", "polo acuatico",
                                   "snorkel", "vela"]),
            ("Deportes de Combate", ["boxeo", "artes marciales", "ufc", "judo", "karate",
                                      "taekwondo", "muay thai", "wrestling"]),
            ("Motor y Aventura", ["formula 1", "motociclismo", "moto", "rally", "ciclismo",
                                   "mtb", "escalada", "montañismo", "paracaidismo"]),
        ],
    },
    {
        "categoria": "Moda y Belleza",
        "keywords": [
            "moda", "ropa", "vestido", "pantalon", "camisa", "zapato", "bolso", "accesorio",
            "tendencia", "fashion", "outfit", "look", "estilo", "marca", "diseñador",
            "belleza", "maquillaje", "labial", "mascara", "base", "cuidado de la piel",
            "crema", "serum", "hidratante", "protector solar", "acne", "arrugas",
            "cabello", "pelo", "corte de pelo", "tintura", "shampoo", "acondicionador",
            "fragancia", "perfume", "colonia", "uñas", "manicura", "pedicura",
        ],
        "subcategorias": [
            ("Ropa y Moda", ["ropa", "vestido", "pantalon", "camisa", "zapato", "outfit",
                              "look", "tendencia", "fashion", "talla", "coleccion"]),
            ("Maquillaje", ["maquillaje", "labial", "mascara", "base", "sombra", "delineador",
                             "blush", "contorno", "highlighter", "paleta"]),
            ("Cuidado de la Piel", ["cuidado de la piel", "crema", "serum", "hidratante",
                                     "protector solar", "acne", "arrugas", "rutina de piel"]),
            ("Cabello", ["cabello", "pelo", "corte de pelo", "tintura", "shampoo",
                          "acondicionador", "mascarilla cabello", "tratamiento capilar"]),
            ("Fragancias y Accesorios", ["fragancia", "perfume", "colonia", "uñas",
                                          "manicura", "pedicura", "joyeria", "bolso"]),
        ],
    },
    {
        "categoria": "Entretenimiento",
        "keywords": [
            "pelicula", "serie", "netflix", "amazon prime", "disney plus", "streaming",
            "actor", "actriz", "director", "cine", "teatro", "concierto", "musica",
            "cancion", "artista", "album", "spotify", "youtube music", "podcast",
            "libro", "novela", "manga", "comic", "anime", "podcast", "radio",
            "television", "programa tv", "reality", "documental", "comedia", "drama",
        ],
        "subcategorias": [
            ("Cine y Series", ["pelicula", "serie", "netflix", "amazon prime", "disney plus",
                                "actor", "actriz", "director", "streaming", "temporada"]),
            ("Música", ["musica", "cancion", "artista", "album", "spotify", "youtube music",
                         "concierto", "festival", "banda", "cantante"]),
            ("Libros y Literatura", ["libro", "novela", "autor", "editorial", "bestseller",
                                      "leer", "lectura", "manga", "comic", "saga"]),
            ("Anime y Manga", ["anime", "manga", "otaku", "shonen", "seinen", "cosplay",
                                "personaje anime", "temporada anime"]),
            ("Podcasts y Radio", ["podcast", "radio", "locutor", "episodio", "escuchar",
                                   "programa", "entrevista"]),
        ],
    },
    {
        "categoria": "Legal y Trámites",
        "keywords": [
            "tramite", "documento", "cedula", "pasaporte", "visa", "migracion", "inmigración",
            "residencia", "nacionalidad", "ciudadania", "contrato", "demanda", "abogado",
            "ley", "derechos", "obligaciones", "multa", "impuesto", "declaracion",
            "herencia", "testamento", "divorcio legal", "custodia", "pension alimenticia",
            "registro civil", "notaria", "escritura", "poder notarial",
        ],
        "subcategorias": [
            ("Inmigración y Visas", ["visa", "migracion", "inmigracion", "residencia",
                                      "nacionalidad", "ciudadania", "permiso de trabajo"]),
            ("Trámites Civiles", ["cedula", "pasaporte", "registro civil", "notaria",
                                   "escritura", "poder notarial", "tramite", "certificado"]),
            ("Derecho Familiar", ["divorcio", "custodia", "pension alimenticia", "herencia",
                                   "testamento", "matrimonio", "adopcion"]),
            ("Impuestos y Fiscal", ["impuesto", "declaracion", "dian", "hacienda", "sat",
                                     "iva", "renta", "tributario", "multa fiscal"]),
            ("Asesoría Legal", ["abogado", "ley", "derechos", "contrato", "demanda",
                                 "accion legal", "representacion legal", "bufete"]),
        ],
    },
    {
        "categoria": "Inmobiliaria",
        "keywords": [
            "apartamento", "casa", "arriendo", "alquiler", "comprar casa", "vender casa",
            "propiedad", "inmueble", "finca raiz", "real estate", "constructora",
            "urbanizacion", "condominio", "estrato", "metro cuadrado", "precio vivienda",
            "hipoteca", "credito hipotecario", "financiacion vivienda", "subsidio vivienda",
            "arrendador", "arrendatario", "contrato arriendo", "deposito garantia",
        ],
        "subcategorias": [
            ("Compra de Vivienda", ["comprar casa", "comprar apartamento", "precio vivienda",
                                     "hipoteca", "credito hipotecario", "financiacion vivienda"]),
            ("Arriendo", ["arriendo", "alquiler", "arrendar", "arrendador", "arrendatario",
                           "contrato arriendo", "deposito garantia", "canon"]),
            ("Inversión Inmobiliaria", ["inversion inmobiliaria", "finca raiz", "real estate",
                                         "rentabilidad", "plusvalia", "valorizar"]),
            ("Construcción y Reformas", ["construir", "reforma", "remodelacion", "constructor",
                                          "arquitecto", "ingenieria civil", "materiales"]),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Motor de clasificación
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    """Normaliza a minúsculas sin tildes para comparación robusta."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _puntuar(keyword_norm: str, palabras_clave: list[str]) -> float:
    """
    Devuelve un score como numero de coincidencias ponderadas.

    - Coincidencia exacta vale 3 puntos.
    - Subcadena (con limites de palabra) vale 1 punto.

    Se devuelve la suma cruda para evitar que listas grandes penalicen el score.
    Un score >= 0.5 se considera coincidencia valida (equivale a al menos 1 hit parcial).
    """
    hits = 0.0
    for pk in palabras_clave:
        pk_norm = _normalizar(pk)
        if pk_norm == keyword_norm:
            hits += 3
        else:
            # Buscar como palabra completa (permitiendo plurales basicos s/es)
            pattern = r'\b' + re.escape(pk_norm) + r'(s|es)?\b'
            if re.search(pattern, keyword_norm):
                hits += 1
            # Tambien buscar si la keyword analizada esta dentro de la palabra clave de la taxonomia
            elif re.search(r'\b' + re.escape(keyword_norm) + r'(s|es)?\b', pk_norm):
                hits += 1
    return hits


def auto_categorizar(keyword: str) -> tuple[str, str]:
    """
    Clasifica automáticamente una keyword en categoría y subcategoría.

    Args:
        keyword: Palabra clave principal de la búsqueda.

    Returns:
        Tupla (categoria, subcategoria). Si no hay coincidencia clara,
        devuelve ("General", "General").
    """
    if not keyword or not keyword.strip():
        return "General", "General"

    kw_norm = _normalizar(keyword)

    # ── Paso 1: Encontrar la mejor categoría ─────────────────────────────
    mejor_cat = None
    mejor_cat_score = 0.0

    for entrada in _TAXONOMY:
        score = _puntuar(kw_norm, entrada["keywords"])
        if score > mejor_cat_score:
            mejor_cat_score = score
            mejor_cat = entrada

    if mejor_cat is None or mejor_cat_score < 0.5:
        return "General", "General"

    categoria = mejor_cat["categoria"]

    # ── Paso 2: Encontrar la mejor subcategoría dentro de la categoría ───
    mejor_sub = None
    mejor_sub_score = 0.0

    for nombre_sub, palabras_sub in mejor_cat.get("subcategorias", []):
        score = _puntuar(kw_norm, palabras_sub)
        if score > mejor_sub_score:
            mejor_sub_score = score
            mejor_sub = nombre_sub

    subcategoria = mejor_sub if mejor_sub and mejor_sub_score >= 0.5 else "General"

    return categoria, subcategoria
