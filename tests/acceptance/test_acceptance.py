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
def fixture_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


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
    browser.get(base_url)
    assert "Gestor de Tareas" in browser.title
    version = browser.find_element(By.ID, "app-version")
    _wait(browser).until(lambda _: version.text not in ("...", "sin conexión", ""))


def test_crear_completar_y_eliminar_tarea(browser, base_url):
    title = f"Selenium {uuid.uuid4().hex[:6]}"
    browser.get(base_url)

    item = _create_task(browser, title)
    assert "Prioridad Alta" in item.text

    _click(browser, title, "toggle-btn")
    _wait(browser).until(lambda b: "done" in _item(b, title).get_attribute("class"))

    _click(browser, title, "delete-btn")
    _wait(browser).until(
        EC.text_to_be_present_in_element((By.ID, "message"), "Tarea eliminada")
    )
    assert not browser.find_elements(By.XPATH, f"//span[text()='{title}']")


def test_filtro_por_estado(browser, base_url):
    title = f"Filtro {uuid.uuid4().hex[:6]}"
    browser.get(base_url)
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
    browser.get(base_url)
    browser.find_element(By.ID, "title").send_keys("   ")
    browser.find_element(By.ID, "submit-btn").click()
    message = browser.find_element(By.ID, "message")
    _wait(browser).until(lambda _: "error" in message.get_attribute("class"))
