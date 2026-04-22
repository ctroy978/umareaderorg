import importlib

from fastapi.responses import RedirectResponse
from nicegui import app as nicegui_app, ui

# Import pages to register their @ui.page routes
importlib.import_module('app.pages.login')
importlib.import_module('app.pages.dashboard')
importlib.import_module('app.pages.welcome')
importlib.import_module('app.pages.placement')
importlib.import_module('app.pages.placement_result')
importlib.import_module('app.pages.session')
importlib.import_module('app.pages.teacher')

from utils.config import STORAGE_SECRET, DB_PATH
import app.db as _db

_db.configure(DB_PATH)
_db.get_conn()  # initialize schema at startup


@nicegui_app.get('/')
async def root():
    return RedirectResponse('/login')


def main():
    ui.run(title='uMaRead', storage_secret=STORAGE_SECRET, port=8080, reload=False)


if __name__ == '__main__':
    main()
