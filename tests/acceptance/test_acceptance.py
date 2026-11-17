"""Pruebas de aceptación con Selenium: el usuario usa la app en un navegador real.

Validan el flujo completo Frontend (Nginx) -> API (FastAPI) -> PostgreSQL.
"""

import uuid

import pytest
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

pytestmark = pytest.mark.acceptance
WAIT = 15


@pytest.fixture(name="browser")
def fixture_browser(base_url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    # Desde Chrome 154 "Always Use Secure Connections" viene activo y muestra
    # una advertencia antes de abrir sitios públicos por HTTP (como el ALB del
    # Learner Lab, que no tiene HTTPS). Se desactiva solo en el Chrome de pruebas.
    options.add_argument(f"--unsafely-treat-insecure-origin-as-secure={base_url}")
    options.add_argument(
        "--disable-features=HttpsUpgrades,HttpsFirstBalancedModeAutoEnable,"
        "HttpsFirstModeV2ForTypicallySecureUsers,HttpsFirstModeIncognito"
    )
    options.add_experimental_option(
        "prefs",
        {
            "https_only_mode_enabled": False,
            "https_first_balanced_mode_enabled": False,
        },
    )
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def _open(browser, url):
    """Abre la app. Si Chrome aún muestra la advertencia de HTTP, la acepta."""
    browser.get(url)
    proceed = browser.find_elements(By.ID, "proceed-button")
    if proceed:
        proceed[0].click()
    WebDriverWait(browser, WAIT).until(
        EC.presence_of_element_located((By.ID, "task-form"))
    )


def _wait(browser):
    # La lista se vuelve a dibujar tras cada acción: si un elemento queda
    # "stale" (viejo), la espera lo ignora y lo vuelve a buscar.
    return WebDriverWait(
        browser, WAIT, ignored_exceptions=[StaleElementReferenceException]
    )


def _click(browser, title, button_class):
    """Hace clic en un botón de la tarea, reintentando si la lista se redibujó."""

    def click(b):
        _item(b, title).find_element(By.CLASS_NAME, button_class).click()
        return True

    _wait(browser).until(click)


def _item(browser, title):
    xpath = f"//li[contains(@class,'task')][.//span[text()='{title}']]"
    return _wait(browser).until(EC.presence_of_element_located((By.XPATH, xpath)))


def _select_option(browser, select_id, text):
    """Elige una opción de un <select> cuando ya está cargada."""

    def select(b):
        Select(b.find_element(By.ID, select_id)).select_by_visible_text(text)
        return True

    _wait(browser).until(select)


def _create_task(browser, title, priority="Alta"):
    browser.find_element(By.ID, "title").send_keys(title)
    browser.find_element(By.ID, "description").send_keys("Creada por Selenium")
    Select(browser.find_element(By.ID, "priority")).select_by_visible_text(priority)
    browser.find_element(By.ID, "submit-btn").click()
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Tarea creada")
    )
    return _item(browser, title)


def test_pagina_carga_con_version(browser, base_url):
    _open(browser, base_url)
    assert "Gestor de Tareas" in browser.title
    version = browser.find_element(By.ID, "app-version")
    _wait(browser).until(lambda _: version.text not in ("...", "sin conexión", ""))


def test_crear_completar_y_eliminar_tarea(browser, base_url):
    title = f"Selenium {uuid.uuid4().hex[:6]}"
    _open(browser, base_url)

    item = _create_task(browser, title)
    assert "Prioridad Alta" in item.text

    _click(browser, title, "toggle-btn")
    _wait(browser).until(lambda b: "done" in _item(b, title).get_attribute("class"))

    _click(browser, title, "delete-btn")
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Tarea eliminada")
    )
    _wait(browser).until(
        lambda b: not b.find_elements(By.XPATH, f"//span[text()='{title}']")
    )


def test_filtro_por_estado(browser, base_url):
    title = f"Filtro {uuid.uuid4().hex[:6]}"
    _open(browser, base_url)
    _create_task(browser, title, priority="Baja")

    Select(browser.find_element(By.ID, "filter-status")).select_by_value("done")
    _wait(browser).until(
        EC.invisibility_of_element_located((By.XPATH, f"//span[text()='{title}']"))
    )

    Select(browser.find_element(By.ID, "filter-status")).select_by_value("pending")
    _click(browser, title, "delete-btn")
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Tarea eliminada")
    )


def test_titulo_vacio_muestra_error(browser, base_url):
    _open(browser, base_url)
    browser.find_element(By.ID, "title").send_keys("   ")
    browser.find_element(By.ID, "submit-btn").click()
    message = browser.find_element(By.ID, "message")
    _wait(browser).until(lambda _: "error" in message.get_attribute("class"))


def test_proyectos_crear_asignar_filtrar_y_eliminar(browser, base_url):
    project = f"Proyecto {uuid.uuid4().hex[:6]}"
    title = f"Con proyecto {uuid.uuid4().hex[:6]}"
    _open(browser, base_url)

    # Crear el proyecto
    browser.find_element(By.ID, "project-name").send_keys(project)
    browser.find_element(By.ID, "project-btn").click()
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Proyecto creado")
    )
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "project-list"), f"{project} (0)")
    )

    # Crear una tarea dentro del proyecto
    _select_option(browser, "project", project)
    item = _create_task(browser, title)
    assert project in item.text
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "project-list"), f"{project} (1)")
    )

    # Filtrar por el proyecto: solo aparece su tarea
    Select(browser.find_element(By.ID, "filter-project")).select_by_visible_text(
        project
    )
    _wait(browser).until(
        lambda b: [e.text for e in b.find_elements(By.CLASS_NAME, "task-title")]
        == [title]
    )

    # Eliminar el proyecto: la tarea se conserva sin proyecto
    chip_xpath = f"//li[contains(@class,'project-chip')][contains(., '{project}')]"
    browser.find_element(By.XPATH, chip_xpath).find_element(
        By.CLASS_NAME, "project-delete-btn"
    ).click()
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Proyecto eliminado")
    )
    _click(browser, title, "delete-btn")
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Tarea eliminada")
    )
