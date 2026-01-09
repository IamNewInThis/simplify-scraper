# Simplify Scraper

Motor de scraping para extracción de datos de e-commerce.

## 📋 Descripción

Este servicio se encarga de navegar sitios web de retailers, extraer información de productos (precios, stock, catálogos) y enviarla al servicio de IA para normalización.

## 🏗️ Estructura del Proyecto

```
simplify-scraper/
├── scrapers/              # Scrapers específicos por retailer
├── tasks/                 # Tareas de Celery
├── utils/                 # Funciones auxiliares
├── venv/                  # Entorno virtual (no se versiona)
├── requirements.txt       # Dependencias de Python
├── .env.example          # Ejemplo de variables de entorno
└── README.md             # Este archivo
```

## 🛠️ Tecnologías

- **Playwright** - Automatización de navegadores
- **BeautifulSoup4** - Parsing de HTML
- **Celery** - Sistema de colas de tareas
- **Redis** - Message broker
- **Pandas** - Procesamiento de datos

## ⚙️ Instalación

### 1. Crear y activar entorno virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Instalar navegadores de Playwright

```bash
playwright install
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

## 🚀 Uso

### Activar entorno virtual

Siempre que trabajes en este proyecto, activa primero el entorno virtual:

```bash
source venv/bin/activate
```

Para desactivar:

```bash
deactivate
```

##  Gestión de Dependencias

### Congelar versiones instaladas

Después de instalar nuevas librerías, congela las versiones exactas:

```bash
pip freeze > requirements.txt
```

### Instalar una nueva librería

```bash
# Activar entorno virtual primero
source venv/bin/activate

# Instalar librería
pip install nombre-libreria

# Congelar versiones actualizadas
pip freeze > requirements.txt
```

## �📝 Próximos Pasos

- Implementar scraper base
- Crear scrapers específicos por retailer
- Configurar tareas de Celery
- Implementar sistema de reintentos
- Añadir logging y monitoreo

## 🔗 Servicios Relacionados

- [simplify-api](../simplify-api/) - Backend FastAPI
- [simplify-ai-service](../simplify-ai-service/) - Servicio de normalización con IA
- [simplify-frontend](../simplify-frontend/) - Interfaz de usuario
