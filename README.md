# MCP Game Design Notes 🎮🔌

Un servidor MCP de solo lectura para consultar notas locales de diseño de videojuegos. Permite preguntar a un asistente por mecánicas, tutoriales o exploración y recuperar el archivo y la línea de origen.

Creado el **23 de octubre de 2026**. Usa el SDK oficial de MCP para Python, fijado a **mcp 2.3.0**. Requiere **Python 3.11+**.

## Instalación y prueba real

```bash
git clone https://github.com/alvaroalcalaa/mcp-game-design-notes.git
cd mcp-game-design-notes
python -m venv .venv
```

Activa el entorno: `source .venv/bin/activate` en macOS/Linux o `.venv\Scripts\activate` en Windows (cmd). Después:

```bash
python -m pip install -r requirements.txt
python -m unittest -v
python smoke.py
```

`smoke.py` inicia el servidor como **subproceso stdio**, negocia MCP con el cliente del SDK, descubre las tres herramientas y ejecuta listado, búsqueda y lectura. Su resultado incluye `"read_ok": true`.

No necesita clave API ni un modelo para estas pruebas. La instalación descarga el SDK y sus dependencias de PyPI.

## Herramientas

| Herramienta | Entrada | Resultado |
|---|---|---|
| `list_notes` | Ninguna | Rutas relativas y tamaños de las notas disponibles |
| `search_notes` | `query`, `limit` opcional (1–20) | Coincidencias por palabras con archivo, línea y fragmento |
| `read_note` | `path` exacto del listado | Texto completo de una nota y hash SHA-256 |

Ejemplo de argumentos para búsqueda:

```json
{"query": "resistencia", "limit": 5}
```

La demo devuelve coincidencias de `combat.md`, incluida la regla de que la esquiva consume 20 puntos de resistencia. Los tres documentos de Bruma son material ficticio original.

## Conectarlo a un host MCP

Ejemplo de configuración para un host que acepte `mcpServers` y procesos stdio; sustituye las rutas por las de tu equipo:

```json
{
  "mcpServers": {
    "game-design-notes": {
      "command": "/RUTA/AL/PROYECTO/.venv/bin/python",
      "args": [
        "/RUTA/AL/PROYECTO/server.py",
        "--notes",
        "/RUTA/AL/PROYECTO/example_notes"
      ]
    }
  }
}
```

En Windows, utiliza la ruta a `.venv/Scripts/python.exe` con barras `/` o barras invertidas escapadas en JSON. El formato concreto del archivo depende del host.

Con el servidor configurado, una petición útil sería: «Busca las notas sobre resistencia y resume las reglas citando archivo y línea».

También puedes iniciar `python server.py --notes ./example_notes` directamente: espera mensajes MCP por stdin, por lo que no muestra un chat ni un menú. El proyecto usa únicamente stdio y no abre un puerto HTTP.

## Carpeta e instantánea de lectura

Al arrancar, el operador elige la carpeta con `--notes`. Se cargan los archivos Markdown UTF-8 en una instantánea de memoria. Los clientes consultan claves de esa instantánea; sus argumentos nunca se usan para abrir nuevas rutas.

- Omite archivos/directorios ocultos y enlaces simbólicos de archivos y subdirectorios.
- Rechaza una raíz que sea enlace simbólico.
- Máximo 200 notas, 64 KiB por nota, 2 MiB de texto total y 2000 entradas recorridas.
- Si se supera un límite o una nota no es UTF-8, el arranque falla explícitamente.
- Los fragmentos de búsqueda se limitan a 240 caracteres e indican si están cortados.
- Modificar notas requiere reiniciar el servidor para actualizar la instantánea.

Las herramientas no escriben ni ejecutan comandos. Las notas se comparten con el **host MCP que conectes**, que podría enviarlas a su proveedor de modelos según su configuración. El servidor no llama a un proveedor por su cuenta. Selecciona solo notas que quieras poner a disposición de ese host.

## Límites y validación

La búsqueda compara palabras literales sin distinguir mayúsculas; no usa embeddings, no comprende sinónimos y no elimina acentos. Las coincidencias no prueban que una afirmación sea verdadera. Las notas se marcan como contenido no fiable: sus instrucciones no deben sustituir las del usuario. Esto no garantiza inmunidad a prompt injection.

El aislamiento por instantánea y las comprobaciones de rutas están pensados para una carpeta local controlada por el operador. No es una sandbox del sistema operativo ni protege contra modificaciones hostiles concurrentes durante la carga, hard links o montajes especiales. No apuntes a directorios de terceros que cambien mientras arranca.

Pruebas incluidas: búsqueda con líneas, lectura, límites de consulta y tamaño, rutas desconocidas y traversal, enlaces simbólicos, UTF-8, instantánea, protocolo en memoria y subproceso stdio real. No se ha probado una sesión con un modelo de IA ni una aplicación de escritorio concreta.

## Referencias oficiales consultadas

- [SDK oficial](https://github.com/modelcontextprotocol/python-sdk)
- [Ejecución del servidor](https://py.sdk.modelcontextprotocol.io/run/)
- [Transportes del cliente](https://py.sdk.modelcontextprotocol.io/client/transports/)

La dependencia directa está fijada para reproducir la API usada; las dependencias transitivas se resuelven al instalar.
