"""Appium driver setup and generic interactions (app-agnostic)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    APPIUM_SERVER_URL,
    DEVICE_CONFIG,
    ELEMENT_WAIT,
    EXPLICIT_WAIT,
    IMPLICIT_WAIT,
    LOG_FILE,
    LOG_LEVEL,
)

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class AppDriver:
    """Appium wrapper for common driver lifecycle and interaction helpers."""

    def __init__(self) -> None:
        self.driver: webdriver.Remote | None = None
        self.wait: WebDriverWait | None = None

    def start_driver(self) -> bool:
        """Start Appium Remote driver with UiAutomator2 options."""
        logger.info("Starting Appium driver with device config: %s", DEVICE_CONFIG)
        try:
            options = UiAutomator2Options()
            options.platform_name = DEVICE_CONFIG["platformName"]
            options.platform_version = DEVICE_CONFIG["platformVersion"]
            options.device_name = DEVICE_CONFIG["deviceName"]
            options.udid = DEVICE_CONFIG["udid"]
            options.automation_name = DEVICE_CONFIG["automationName"]
            options.app_package = DEVICE_CONFIG["appPackage"]
            options.app_activity = DEVICE_CONFIG["appActivity"]
            options.no_reset = DEVICE_CONFIG["noReset"]
            options.full_reset = DEVICE_CONFIG["fullReset"]
            options.set_capability("autoGrantPermissions", True)
            options.set_capability("newCommandTimeout", 300)

            self.driver = webdriver.Remote(command_executor=APPIUM_SERVER_URL, options=options)
            self.driver.implicitly_wait(IMPLICIT_WAIT)
            self.wait = WebDriverWait(self.driver, EXPLICIT_WAIT)
            logger.info("Appium driver started successfully.")
            return True
        except Exception:
            logger.exception("Failed to start Appium driver.")
            raise

    def stop_driver(self) -> None:
        """Stop the Appium driver if active."""
        if self.driver is None:
            return
        try:
            self.driver.quit()
            logger.info("Appium driver stopped.")
        except Exception:
            logger.exception("Error while stopping Appium driver.")

    def find_element_safe(
        self, locator: str, by: str = AppiumBy.XPATH, timeout: int = ELEMENT_WAIT
    ):
        """Return element if found before timeout, else None."""
        if self.driver is None:
            logger.debug("find_element_safe called with no active driver.")
            return None
        try:
            local_wait = WebDriverWait(self.driver, timeout)
            return local_wait.until(EC.presence_of_element_located((by, locator)))
        except TimeoutException:
            logger.debug("Timed out finding element by %s: %s", by, locator)
            return None
        except Exception:
            logger.debug("Unexpected error finding element by %s: %s", by, locator, exc_info=True)
            return None

    def find_element_with_fallbacks(
        self, locator_list: list[str], by: str = AppiumBy.XPATH, timeout: int = ELEMENT_WAIT
    ):
        """Try locators in order and return the first matching element."""
        for locator in locator_list:
            element = self.find_element_safe(locator=locator, by=by, timeout=timeout)
            if element is not None:
                return element
        return None

    def click_element(
        self, locator: str, by: str = AppiumBy.XPATH, timeout: int = ELEMENT_WAIT
    ) -> bool:
        """Click element if found, returning True on success."""
        element = self.find_element_safe(locator=locator, by=by, timeout=timeout)
        if element is None:
            return False
        try:
            element.click()
            return True
        except Exception:
            logger.debug("Failed clicking locator: %s", locator, exc_info=True)
            return False

    def click_with_fallbacks(
        self, locator_list: list[str], by: str = AppiumBy.XPATH, timeout: int = ELEMENT_WAIT
    ) -> bool:
        """Try clicking via fallback locators in order."""
        for locator in locator_list:
            if self.click_element(locator=locator, by=by, timeout=timeout):
                return True
        return False

    def get_text(
        self, locator: str, by: str = AppiumBy.XPATH, timeout: int = ELEMENT_WAIT
    ) -> str | None:
        """Get text from a located element, else None."""
        element = self.find_element_safe(locator=locator, by=by, timeout=timeout)
        if element is None:
            return None
        for _ in range(3):
            try:
                return element.text
            except StaleElementReferenceException:
                logger.debug("Stale element while reading locator text: %s", locator)
                element = self.find_element_safe(locator=locator, by=by, timeout=timeout)
                if element is None:
                    return None
            except Exception:
                logger.debug("Failed reading text for locator: %s", locator, exc_info=True)
                return None
        return None

    def get_all_text_on_screen(self, max_retries: int = 3) -> str:
        """Returns all visible TextView text on screen with stale retries."""
        if self.driver is None:
            return ""
        for attempt in range(max_retries):
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
                texts: list[str] = []
                for el in elements:
                    try:
                        t = el.text
                        if t and t.strip():
                            texts.append(t.strip())
                    except StaleElementReferenceException:
                        continue
                return " ".join(texts).lower()
            except StaleElementReferenceException:
                time.sleep(0.5)
                continue
            except Exception as exc:
                logger.warning("get_all_text_on_screen attempt %s failed: %s", attempt + 1, exc)
                time.sleep(0.5)
        logger.error("get_all_text_on_screen exhausted retries, returning empty")
        return ""

    def wait_for_any(
        self, locator_list: list[str], by: str = AppiumBy.XPATH, timeout: int = EXPLICIT_WAIT
    ) -> bool:
        """Wait until any locator is present."""
        if self.driver is None:
            return False
        try:
            local_wait = WebDriverWait(self.driver, timeout)
            local_wait.until(lambda drv: self._any_locator_present(drv, locator_list, by))
            return True
        except TimeoutException:
            return False
        except Exception:
            logger.exception("wait_for_any failed.")
            return False

    @staticmethod
    def _any_locator_present(drv, locator_list: list[str], by: str) -> bool:
        for locator in locator_list:
            try:
                if drv.find_elements(by, locator):
                    return True
            except StaleElementReferenceException:
                continue
        return False

    def take_screenshot(self, filename: str) -> bool:
        """Save screenshot and return success."""
        if self.driver is None:
            logger.error("Cannot take screenshot: driver is not initialized.")
            return False
        try:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(filename)
            logger.info("Saved screenshot: %s", filename)
            return True
        except Exception:
            logger.exception("Failed to save screenshot: %s", filename)
            return False

    def get_page_source(self) -> str:
        """Return current page XML source."""
        if self.driver is None:
            logger.error("Cannot get page source: driver is not initialized.")
            return ""
        try:
            return self.driver.page_source
        except Exception:
            logger.exception("Failed to get page source.")
            return ""

    def dump_ui_to_file(self, filepath: str) -> bool:
        """Dump page source XML to disk."""
        try:
            source = self.get_page_source()
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text(source, encoding="utf-8")
            logger.info("Dumped UI XML to: %s", filepath)
            return True
        except Exception:
            logger.exception("Failed writing UI dump to file: %s", filepath)
            return False
