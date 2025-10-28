# SGDI Backend

Sistema de Gestión Documental Integrado - Backend API

## Descripción

Este proyecto es el backend de la aplicación SGDI (Sistema de Gestión Documental Integrado), desarrollado con FastAPI y PostgreSQL.

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

## Configuración

1. Clona el repositorio y navega al directorio del proyecto:
```bash
cd sgdi-backend
```

2. Copia el archivo de variables de entorno:
```bash
cp env.template .env
```

3. Edita el archivo `.env` con tus configuraciones específicas:
```bash
# Edita las variables según tus necesidades
nano .env
```

## Variables de Entorno

### Base de Datos
- `POSTGRES_USER`: Usuario de PostgreSQL
- `POSTGRES_PASSWORD`: Contraseña de PostgreSQL
- `POSTGRES_DB`: Nombre de la base de datos
- `POSTGRES_PORT`: Puerto de PostgreSQL
- `POSTGRES_HOST`: Host de PostgreSQL

### JWT
- `JWT_SECRET_KEY`: Clave secreta para JWT (cambiar en producción)
- `JWT_ALGORITHM`: Algoritmo de JWT (HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Tiempo de expiración del token de acceso
- `REFRESH_TOKEN_EXPIRE_DAYS`: Tiempo de expiración del token de refresco

### Almacenamiento
- `STORAGE_PATH`: Ruta para almacenamiento de archivos
- `BACKUP_PATH`: Ruta para backups
- `MAX_UPLOAD_SIZE_MB`: Tamaño máximo de subida en MB
- `ALLOWED_MIME_TYPES`: Tipos MIME permitidos

## Ejecución con Docker

1. Construye y ejecuta los contenedores:
```bash
docker-compose up --build
```

2. La API estará disponible en: http://localhost:8000
3. Documentación OpenAPI: http://localhost:8000/docs
4. pgAdmin: http://localhost:5050

## Ejecución Local (Desarrollo)

1. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Asegúrate de tener PostgreSQL corriendo localmente o configura las variables de entorno para apuntar a tu base de datos.

4. Ejecuta la aplicación:
```bash
uvicorn app.main:app --reload
```

## Migraciones de Base de Datos

Para crear y ejecutar migraciones con Alembic:

```bash
# Crear una nueva migración
alembic revision --autogenerate -m "Descripción de la migración"

# Ejecutar migraciones
alembic upgrade head
```

## Estructura del Proyecto

```
sgdi-backend/
├── app/
│   ├── main.py              # Punto de entrada de la aplicación
│   ├── core/                # Configuraciones core
│   │   ├── config.py        # Configuración general
│   │   ├── security.py      # Utilidades de seguridad
│   │   └── logging.py       # Configuración de logging
│   ├── db/                  # Configuración de base de datos
│   │   ├── base.py          # Base de modelos SQLAlchemy
│   │   ├── session.py       # Sesión de base de datos
│   │   └── alembic_env.py   # Configuración de Alembic
│   ├── models/              # Modelos de base de datos
│   ├── schemas/             # Esquemas Pydantic
│   ├── routes/              # Definición de rutas/endpoints
│   ├── services/            # Lógica de negocio
│   ├── utils/               # Utilidades
│   └── audit/               # Sistema de auditoría
├── migrations/              # Migraciones de Alembic
├── tests/                   # Tests
├── Dockerfile               # Docker image
├── docker-compose.yml       # Configuración de Docker Compose
├── requirements.txt         # Dependencias Python
├── .env.example            # Variables de entorno de ejemplo
└── README.md               # Este archivo
```

## Testing

Para ejecutar los tests:

```bash
pytest
```

## Contribución

1. Crea una rama para tu feature: `git checkout -b feature/nueva-funcionalidad`
2. Realiza tus cambios y commits
3. Ejecuta los tests
4. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT.
