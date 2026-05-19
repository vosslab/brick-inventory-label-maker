"""FastAPI app for brick inventory label maker."""

import os

# PIP3 modules
import fastapi
import fastapi.staticfiles
import fastapi.middleware.cors

# local repo modules
import backend.config
import backend.static_mount
import backend.routes.health
import backend.routes.labels
import backend.routes.cache


#============================================
def create_app() -> fastapi.FastAPI:
	"""
	Create and configure FastAPI app.
	Boots successfully even without BrickLink credentials.
	"""
	api_app = fastapi.FastAPI(
		title='Brick Inventory Label Maker',
		description='Generate print-ready PDF labels for LEGO minifigs and sets',
		version='0.1.0',
	)

	# CORS only for localhost
	api_app.add_middleware(
		fastapi.middleware.cors.CORSMiddleware,
		allow_origins=['http://127.0.0.1', 'http://localhost'],
		allow_credentials=True,
		allow_methods=['*'],
		allow_headers=['*'],
	)

	# Register routes
	api_app.include_router(backend.routes.health.router)
	api_app.include_router(backend.routes.labels.router)
	api_app.include_router(backend.routes.cache.router)

	# Mount frontend static files if available
	frontend_dist = backend.static_mount.get_frontend_dist_path()
	if frontend_dist and os.path.isdir(frontend_dist):
		api_app.mount('/', fastapi.staticfiles.StaticFiles(directory=frontend_dist, html=True), name='frontend')

	return api_app


#============================================
# Module-level app for uvicorn
app = create_app()
