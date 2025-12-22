"""
OBSID - Automatizare Bonuri Producție Oblio cu Selenium
========================================================

Script care automatizează crearea bonurilor de producție în Oblio
folosind Selenium WebDriver pentru control complet al browser-ului.

Autor: OBSID
Versiune: 1.0
Data: 2025-11-19
"""

import time
import json
import sys
import os
import re
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import logging
import cloudinary
import cloudinary.uploader
# Import Supabase database functions (migrated from PostgreSQL)
from utils.decanturi_processor import adauga_bon, verificare_bon_exista, get_bonuri_procesate_pentru_comenzi

# Configurare Cloudinary (din environment variables pentru securitate)
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', 'dbecgc8il'),
  api_key = os.getenv('CLOUDINARY_API_KEY'),
  api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automatizare_oblio.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OblioAutomation:
    """Clasa pentru automatizarea bonurilor de producție în Oblio"""

    def __init__(self, use_existing_profile=True, headless=False, log_callback=None, input_callback=None):
        """
        Inițializare automation

        Args:
            use_existing_profile (bool): Folosește profilul Chrome existent (cu sesiune Oblio)
            headless (bool): Rulează în mod headless (fără interfață grafică)
            log_callback (callable): Funcție pentru logging live: log_callback(message, level)
            input_callback (callable): Funcție pentru input interactiv: input_callback(prompt_dict) -> str
        """
        self.driver = None
        self.use_existing_profile = use_existing_profile
        self.headless = headless
        self.log_callback = log_callback
        self.input_callback = input_callback
        self.stop_requested = False # Flag pentru oprire
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

    def stop(self):
        """Oprește execuția automatizării"""
        self._log("🛑 Comandă de oprire primită! Se oprește după pasul curent...", 'warning')
        self.stop_requested = True

    def _check_stop(self):
        """Verifică dacă s-a cerut oprirea și aruncă excepție"""
        if self.stop_requested:
            raise Exception("Execuție oprită manual de utilizator (STOP)")

    def _log(self, message, level='info'):
        """
        Log message prin callback sau logger standard

        Args:
            message (str): Mesajul de logat
            level (str): Nivelul: 'info', 'warning', 'error', 'success'
        """
        # Trimite către callback dacă există
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception as e:
                logger.warning(f"⚠️ Eroare la log_callback: {e}")

        # Loghează și în logger standard
        if level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'success':
            logger.info(message)
        else:
            logger.info(message)

    def _request_input(self, prompt_dict):
        """
        Cere input de la utilizator prin callback sau input() standard

        Args:
            prompt_dict (dict): Dicționar cu 'type' ('email', 'password', '2fa') și 'message'

        Returns:
            str: Input-ul utilizatorului
        """
        if self.input_callback:
            try:
                return self.input_callback(prompt_dict)
            except Exception as e:
                self._log(f"⚠️ Eroare la input_callback: {e}", 'warning')
                return None
        else:
            # Fallback la input() standard
            return input(f"{prompt_dict['message']}: ")


    def interactive_login(self):
        """
        Autentificare interactivă prin callback (suportă 2FA)

        Returns:
            bool: True dacă login reușit
        """
        self._log("🔐 Începere autentificare interactivă...", 'info')

        try:
            # Navighează la pagina de login
            login_url = "https://www.oblio.eu/login/"
            self._log(f"🌐 Navigare la: {login_url}", 'info')
            self.driver.get(login_url)
            time.sleep(2)

            # Verifică dacă suntem deja logați
            if "login" not in self.driver.current_url.lower():
                self._log("✅ Deja autentificat în Oblio!", 'success')
                return True

            # Acceptă cookie consent popup dacă există
            try:
                self._log("🍪 Verificare cookie consent popup...", 'info')
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
                )
                cookie_button.click()
                self._log("✅ Cookie consent acceptat!", 'success')
                time.sleep(1)
            except TimeoutException:
                self._log("ℹ️ Cookie consent nu a apărut (deja acceptat)", 'info')
            except Exception as e:
                self._log(f"⚠️ Eroare la cookie consent: {str(e)[:100]}", 'warning')

            # STEP 1: Cere email
            self._log("📧 Se așteaptă email-ul...", 'info')
            email = self._request_input({
                'type': 'email',
                'message': '📧 Introdu email-ul pentru Oblio'
            })

            if not email:
                raise Exception("Email-ul nu a fost furnizat!")

            self._log(f"✅ Email primit: {email}", 'info')

            # Găsește și completează câmpul de email
            email_input = self.wait_for_element(By.ID, "username", timeout=10)
            if not email_input:
                email_input = self.wait_for_element(By.NAME, "username", timeout=5)
            if not email_input:
                email_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='email']", timeout=5)

            if not email_input:
                raise Exception("Câmpul de email nu a fost găsit!")

            email_input.clear()
            email_input.send_keys(email)
            time.sleep(0.5)

            # STEP 2: Cere parolă
            self._log("🔑 Se așteaptă parola...", 'info')
            password = self._request_input({
                'type': 'password',
                'message': '🔑 Introdu parola pentru Oblio'
            })

            if not password:
                raise Exception("Parola nu a fost furnizată!")

            self._log("✅ Parolă primită", 'info')

            # Găsește și completează câmpul de parolă
            password_input = self.wait_for_element(By.ID, "password", timeout=10)
            if not password_input:
                password_input = self.wait_for_element(By.NAME, "password", timeout=5)
            if not password_input:
                password_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='password']", timeout=5)

            if not password_input:
                raise Exception("Câmpul de parolă nu a fost găsit!")

            password_input.clear()
            password_input.send_keys(password)
            time.sleep(0.5)

            # Găsește și click buton login
            self._log("🖱️ Click pe butonul de login...", 'info')
            login_button = None
            login_selectors = [
                (By.ID, "login-button"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Autentificare')]"),
            ]

            for by, selector in login_selectors:
                try:
                    login_button = self.wait_for_clickable(by, selector, timeout=3)
                    if login_button:
                        break
                except:
                    continue

            if not login_button:
                # Încearcă ENTER
                password_input.send_keys(Keys.ENTER)
            else:
                login_button.click()

            time.sleep(3)

            # Verifică dacă există erori de autentificare
            try:
                error_selectors = [
                    (By.CSS_SELECTOR, ".alert-danger"),
                    (By.CSS_SELECTOR, ".error"),
                    (By.XPATH, "//*[contains(text(), 'incorect')]"),
                    (By.XPATH, "//*[contains(text(), 'greșit')]"),
                    (By.XPATH, "//*[contains(text(), 'invalid')]"),
                ]

                for by, selector in error_selectors:
                    try:
                        error_elem = self.driver.find_element(by, selector)
                        if error_elem.is_displayed():
                            error_text = error_elem.text
                            self._log(f"❌ EROARE AUTENTIFICARE: {error_text}", 'error')
                            self._log("🔄 Email sau parolă incorectă! Rulează din nou automation-ul și introdu credențialele corecte.", 'error')
                            raise Exception(f"Credențiale incorecte: {error_text}")
                    except NoSuchElementException:
                        continue
            except Exception as e:
                if "Credențiale incorecte" in str(e):
                    raise  # Re-raise dacă e eroarea noastră
                # Altfel ignoră - poate nu există elementele de eroare

            # STEP 3: Verifică dacă e nevoie de 2FA
            current_url = self.driver.current_url
            self._log(f"🌐 URL după login: {current_url}", 'info')

            # Caută câmp 2FA
            two_fa_input = None
            try:
                two_fa_selectors = [
                    (By.ID, "sms_code"),  # Oblio folosește acest ID pentru 2FA
                    (By.ID, "two_factor_code"),
                    (By.ID, "2fa_code"),
                    (By.NAME, "code"),
                    (By.CSS_SELECTOR, "input[type='text'][maxlength='6']"),
                    (By.CSS_SELECTOR, "input[placeholder*='code']"),
                ]

                for by, selector in two_fa_selectors:
                    try:
                        two_fa_input = self.driver.find_element(by, selector)
                        if two_fa_input.is_displayed():
                            break
                        else:
                            two_fa_input = None
                    except:
                        continue
            except:
                pass

            # Dacă există câmp 2FA, cere codul
            if two_fa_input:
                self._log("🔢 2FA detectat! Se așteaptă codul...", 'warning')
                two_fa_code = self._request_input({
                    'type': '2fa',
                    'message': '🔢 Introdu codul 2FA (6 cifre)'
                })

                if not two_fa_code:
                    raise Exception("Codul 2FA nu a fost furnizat!")

                self._log("✅ Cod 2FA primit", 'info')

                # Completează codul 2FA
                two_fa_input.clear()
                two_fa_input.send_keys(two_fa_code)
                time.sleep(0.5)

                # Găsește buton submit 2FA
                submit_2fa_button = None
                submit_selectors = [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.ID, "submit_2fa"),
                    (By.XPATH, "//button[contains(text(), 'Verify')]"),
                    (By.XPATH, "//button[contains(text(), 'Verifică')]"),
                ]

                for by, selector in submit_selectors:
                    try:
                        submit_2fa_button = self.wait_for_clickable(by, selector, timeout=3)
                        if submit_2fa_button:
                            break
                    except:
                        continue

                if submit_2fa_button:
                    submit_2fa_button.click()
                else:
                    two_fa_input.send_keys(Keys.ENTER)

                time.sleep(3)

            # STEP 4: Verifică succesul
            current_url = self.driver.current_url
            if "login" not in current_url.lower() and "dashboard" in current_url or "stock" in current_url or "home" in current_url:
                self._log("✅ Autentificare reușită în Oblio!", 'success')
                return True
            elif "login" not in current_url.lower():
                self._log("✅ Autentificare reușită!", 'success')
                return True
            else:
                raise Exception("Login eșuat - încă pe pagina de login")

        except Exception as e:
            self._log(f"❌ Eroare la autentificare: {e}", 'error')
            return False

    def setup_driver(self):
        """Configurare și pornire Chrome WebDriver"""
        self._log("🔧 Configurare Chrome WebDriver...", 'info')

        # Detectează sistemul de operare
        is_linux = platform.system() == 'Linux'
        is_windows = platform.system() == 'Windows'

        logger.info(f"🖥️ Sistem detectat: {platform.system()}")

        chrome_options = Options()

        # Configurare specifică platformei
        if is_linux:
            # Configurare pentru Ubuntu Server (Coolify)
            logger.info("🐧 Configurare pentru Linux/Ubuntu Server...")

            # Pe server, rulează ÎNTOTDEAUNA în headless mode
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1920,1080')

            logger.info("👁️ Mod headless activat (server)")

        elif is_windows:
            # Configurare pentru Windows (local development)
            logger.info("🪟 Configurare pentru Windows...")

            # DEBUGGING MODE: Încearcă să se conecteze la Chrome existent cu remote debugging
            # Pornește Chrome manual cu: chrome.exe --remote-debugging-port=9222
            if self.use_existing_profile:
                try:
                    logger.info("🔍 Încerc să mă conectez la Chrome cu remote debugging (port 9222)...")
                    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                    logger.info("✅ Configurare remote debugging activată")
                    logger.info("📌 IMPORTANT: Asigură-te că Chrome rulează cu --remote-debugging-port=9222")
                except Exception as e:
                    logger.warning(f"⚠️ Nu pot configura remote debugging: {e}")
                    logger.info("📌 Voi porni un Chrome nou cu profil...")
                    
                    # Fallback: folosește profilul Chrome (ca înainte)
                    username = os.environ.get('USERNAME', 'ukfdb')
                    user_data_dir = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"

                    if os.path.exists(user_data_dir):
                        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
                        chrome_options.add_argument("profile-directory=Default")
                        logger.info(f"📂 Folosesc profilul Chrome: {user_data_dir}")
                    else:
                        logger.warning(f"⚠️ Profilul Chrome nu există: {user_data_dir}")

            # NICIODATĂ headless pe Windows pentru debugging
            if self.headless:
                logger.warning("⚠️ Headless dezactivat pe Windows pentru debugging vizual")
                self.headless = False

            # Opțiuni pentru stabilitate (Windows)
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

        # Opțiuni comune pentru ambele platforme
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        # TEMPORAR DEZACTIVAT - cauzează eroare pe unele versiuni Chrome
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent pentru a evita detecția bot
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')

        # Pornire driver
        try:
            if is_linux:
                # Pe Linux, folosește chromedriver din sistem
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

                # Verifică dacă ChromeDriver există
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info(f"✅ Chromium WebDriver pornit cu succes (Linux)! Path: {chromedriver_path}")
                else:
                    # Încearcă fără service explicit (pentru snap pe Ubuntu)
                    logger.warning(f"⚠️ ChromeDriver nu găsit la {chromedriver_path}, încerc autodetectare...")
                    self.driver = webdriver.Chrome(options=chrome_options)
                    logger.info("✅ Chromium WebDriver pornit cu succes (Linux - autodetectat)!")
            else:
                # Pe Windows, folosește chromedriver automat
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ Chrome WebDriver pornit cu succes (Windows)!")

            # Maximize window (doar pe Windows sau dacă nu e headless)
            if not is_linux and not self.headless:
                self.driver.maximize_window()

            return True
        except Exception as e:
            logger.error(f"❌ Eroare la pornirea Chrome: {e}")
            logger.error(f"💡 Asigură-te că: Chromium și ChromeDriver sunt instalate")

            # Log paths pentru debugging
            if is_linux:
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
                chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
                logger.error(f"🔍 ChromeDriver path: {chromedriver_path} (exists: {os.path.exists(chromedriver_path)})")
                logger.error(f"🔍 Chrome binary: {chrome_bin} (exists: {os.path.exists(chrome_bin)})")

            return False

    def wait_for_element(self, by, selector, timeout=5):
        """
        Așteaptă ca un element să fie disponibil

        Args:
            by: Tipul selectorului (By.ID, By.CSS_SELECTOR, etc.)
            selector: Selectorul elementului
            timeout: Timeout în secunde (default 5s - optimizat)

        Returns:
            WebElement sau None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"⚠️ Element {selector} nu a fost găsit după {timeout}s")
            return None

    def wait_for_clickable(self, by, selector, timeout=5):
        """
        Așteaptă ca un element să fie clickable

        Args:
            by: Tipul selectorului
            selector: Selectorul elementului
            timeout: Timeout în secunde (default 5s - optimizat)

        Returns:
            WebElement sau None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"⚠️ Element {selector} nu e clickable după {timeout}s")
            return None

    def wait_for_overlays_gone(self, timeout=10):
        """
        Așteaptă dispariția overlay-urilor comune din Oblio (loading spinners, modals)

        Args:
            timeout: Timeout maxim în secunde

        Returns:
            True dacă overlay-urile au dispărut, False dacă timeout
        """
        overlay_selectors = [
            ".modal-backdrop",           # Bootstrap modal backdrop
            ".loading",                  # Loading spinner generic
            ".spinner",                  # Spinner
            "#loading-overlay",          # Loading overlay explicit
            ".page-loader",              # Page loader
            "[class*='loading']",        # Orice element cu loading în clasă
            ".overlay",                  # Overlay generic
        ]

        try:
            for selector in overlay_selectors:
                try:
                    # Verifică dacă există overlay vizibil
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            # Așteaptă să devină invizibil
                            WebDriverWait(self.driver, timeout).until(
                                EC.invisibility_of_element(overlay)
                            )
                            logger.debug(f"✅ Overlay {selector} a dispărut")
                except:
                    continue
            return True
        except TimeoutException:
            logger.warning(f"⚠️ Overlay încă vizibil după {timeout}s")
            return False

    def safe_click(self, element, retries=3, wait_after=0.5):
        """
        Click sigur pe un element, cu retry și handling pentru overlay-uri interceptate

        Args:
            element: WebElement pe care să se facă click
            retries: Număr de încercări (default 3)
            wait_after: Timp de așteptare după click (default 0.5s)

        Returns:
            True dacă click-ul a reușit, False altfel
        """
        from selenium.webdriver.common.action_chains import ActionChains

        for attempt in range(retries):
            try:
                # Prima dată, așteaptă să dispară overlay-urile
                self.wait_for_overlays_gone(timeout=5)

                # Scroll element în view dacă e necesar
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.3)

                # Încearcă click normal
                element.click()
                time.sleep(wait_after)
                return True

            except Exception as e:
                error_msg = str(e).lower()

                if "intercepted" in error_msg or "not clickable" in error_msg:
                    logger.warning(f"⚠️ Click interceptat (încercare {attempt+1}/{retries}), încerc alternativă...")

                    # Alternativa 1: Click prin JavaScript
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(wait_after)
                        return True
                    except:
                        pass

                    # Alternativa 2: ActionChains
                    try:
                        ActionChains(self.driver).move_to_element(element).click().perform()
                        time.sleep(wait_after)
                        return True
                    except:
                        pass

                    # Alternativa 3: Închide modalele vizibile și reîncearcă
                    try:
                        self._close_blocking_modals()
                        time.sleep(0.5)
                    except:
                        pass
                else:
                    logger.error(f"❌ Eroare la click: {e}")

                time.sleep(0.5)

        logger.error(f"❌ Nu s-a putut face click după {retries} încercări")
        return False

    def _close_blocking_modals(self):
        """Închide orice modal care ar putea bloca interacțiunea"""
        modal_close_selectors = [
            ".modal.show .close",
            ".modal.show [data-dismiss='modal']",
            "#modal-message .ok-message-modal",
            ".modal-backdrop",
        ]

        for selector in modal_close_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        try:
                            el.click()
                            logger.debug(f"✅ Închis modal: {selector}")
                        except:
                            # Încearcă prin JS
                            self.driver.execute_script("arguments[0].click();", el)
            except:
                continue

    def upload_screenshot_to_cloudinary(self, screenshot_path, context="error"):
        """
        Încarcă un screenshot pe Cloudinary și returnează URL-ul

        Args:
            screenshot_path: Calea către screenshot
            context: Context pentru log (ex: "error", "stoc_insuficient", "redirect_fail")

        Returns:
            URL-ul imaginii sau None
        """
        try:
            if not os.path.exists(screenshot_path):
                self._log(f"⚠️ Screenshot nu există: {screenshot_path}", 'warning')
                return None

            # Generează un public_id unic cu timestamp și dată
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(screenshot_path).replace('.png', '')
            public_id = f"obsid_errors/{timestamp}_{filename}"

            self._log(f"☁️ Upload screenshot pe Cloudinary...", 'info')

            # Upload cu folder dinamic bazat pe dată
            response = cloudinary.uploader.upload(
                screenshot_path,
                public_id=public_id,
                resource_type="image",
                overwrite=True,
                tags=[context, datetime.now().strftime("%Y-%m-%d")]
            )

            url = response.get('secure_url')
            if url:
                # Log URL vizibil în roșu pentru atenție
                self._log(f"📸 SCREENSHOT [{context.upper()}]: {url}", 'error')

                # Șterge fișierul local după upload reușit
                try:
                    os.remove(screenshot_path)
                except:
                    pass

                return url
            else:
                self._log("⚠️ Upload Cloudinary reușit dar fără URL", 'warning')
                return None

        except Exception as e:
            self._log(f"⚠️ Eroare upload Cloudinary: {str(e)}", 'warning')
            return None

    def capture_error_screenshot(self, sku, error_type="error"):
        """
        Captură screenshot pentru eroare și upload pe Cloudinary

        Args:
            sku: SKU-ul produsului cu eroare
            error_type: Tipul erorii (error, stoc_insuficient, redirect_fail, click_intercepted)

        Returns:
            URL-ul imaginii sau None
        """
        try:
            # Asigură-te că folderul uploads există
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)

            # Generează nume unic pentru screenshot
            timestamp = int(time.time())
            safe_sku = str(sku).replace('/', '_').replace('\\', '_')[:30]
            screenshot_path = os.path.join(uploads_dir, f"{error_type}_{safe_sku}_{timestamp}.png")

            # Captură screenshot
            self.driver.save_screenshot(screenshot_path)

            # Upload și returnează URL
            return self.upload_screenshot_to_cloudinary(screenshot_path, context=f"{error_type}_{safe_sku}")

        except Exception as e:
            self._log(f"⚠️ Eroare la captura screenshot: {str(e)}", 'warning')
            return None

    def load_cookies_from_json(self, cookies_json):
        """
        Încarcă cookies din JSON în browser pentru sesiune Oblio

        Args:
            cookies_json (str or dict): Cookies în format JSON

        Returns:
            bool: True dacă cookies au fost încărcate cu succes
        """
        logger.info("🍪 Începere încărcare cookies în browser...")
        
        try:
            # Parse cookies dacă e string
            if isinstance(cookies_json, str):
                cookies = json.loads(cookies_json)
            else:
                cookies = cookies_json
            
            # Navighează la domeniul Oblio mai întâi (necesar pentru a seta cookies)
            logger.info("🌐 Navigare la domeniul Oblio pentru a seta cookies...")
            self.driver.get("https://www.oblio.eu")
            time.sleep(1)
            
            # Adaugă fiecare cookie
            logger.info(f"🍪 Încărcare {len(cookies)} cookies...")
            cookies_loaded = 0
            
            for cookie in cookies:
                try:
                    # Selenium necesită doar anumite câmpuri
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.oblio.eu'),
                    }
                    
                    # Adaugă câmpuri opționale dacă există
                    if 'path' in cookie:
                        cookie_dict['path'] = cookie['path']
                    if 'secure' in cookie:
                        cookie_dict['secure'] = cookie['secure']
                    if 'httpOnly' in cookie:
                        cookie_dict['httpOnly'] = cookie['httpOnly']
                    if 'sameSite' in cookie:
                        cookie_dict['sameSite'] = cookie['sameSite']
                    
                    self.driver.add_cookie(cookie_dict)
                    cookies_loaded += 1
                    logger.debug(f"✅ Cookie încărcat: {cookie['name']}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Nu pot încărca cookie {cookie.get('name', 'unknown')}: {e}")
            
            logger.info(f"✅ {cookies_loaded}/{len(cookies)} cookies încărcate cu succes!")
            
            # Refresh pagina pentru a aplica cookies
            logger.info("🔄 Refresh pagină pentru aplicare cookies...")
            self.driver.refresh()
            time.sleep(2)
            
            # Verifică dacă suntem autentificați
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                logger.info("✅ Cookies aplicate cu succes - sesiune activă!")
                return True
            else:
                logger.warning("⚠️ Încă pe pagina de login după aplicare cookies")
                return False
                
        except Exception as e:
            logger.error(f"❌ Eroare la încărcarea cookies: {e}")
            return False

    def wait_for_manual_login(self, timeout=90):
        """
        Așteaptă ca utilizatorul să se logheze manual (inclusiv 2FA)
        
        Args:
            timeout (int): Timeout în secunde pentru login manual
            
        Returns:
            bool: True dacă utilizatorul s-a logat cu succes
        """
        logger.info("👤 Așteaptă login manual...")
        logger.info(f"⏰ Ai {timeout} secunde să te loghezi în Oblio (inclusiv 2FA)")
        logger.info("🌐 Browser-ul va fi deschis - loghează-te acum!")
        
        # Navighează la pagina de login
        login_url = "https://www.oblio.eu/login/"
        logger.info(f"🌐 Navigare la: {login_url}")
        self.driver.get(login_url)
        time.sleep(2)
        
        # Așteaptă ca utilizatorul să se logheze
        start_time = time.time()
        logged_in = False
        
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            
            # Verifică dacă nu mai suntem pe pagina de login
            if "login" not in current_url.lower():
                logger.info(f"✅ Login detectat! URL curent: {current_url}")
                logged_in = True
                break
            
            # Verifică periodic
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            if elapsed % 10 == 0:  # Log la fiecare 10 secunde
                logger.info(f"⏳ Așteaptă login... ({remaining}s rămase)")
            
            time.sleep(1)
        
        if logged_in:
            logger.info("✅ Utilizator autentificat cu succes!")
            return True
        else:
            logger.error(f"❌ Timeout - utilizatorul nu s-a autentificat în {timeout}s")
            return False

    def login_to_oblio(self, email, password):
        """
        Autentificare automată în Oblio (NU funcționează cu 2FA activat!)

        Args:
            email (str): Email-ul utilizatorului Oblio
            password (str): Parola utilizatorului Oblio

        Returns:
            bool: True dacă login reușit, False altfel
        """
        logger.info("🔐 Începere autentificare automată în Oblio...")
        logger.warning("⚠️ ATENȚIE: Această metodă NU funcționează dacă 2FA este activat!")
        logger.warning("💡 Pentru 2FA, folosește metoda wait_for_manual_login()")
        
        try:
            # Navighează la pagina de login
            login_url = "https://www.oblio.eu/login/"
            logger.info(f"🌐 Navigare la: {login_url}")
            self.driver.get(login_url)
            time.sleep(2)
            
            # Verifică dacă suntem deja logați (redirectați către dashboard)
            if "dashboard" in self.driver.current_url or "stock" in self.driver.current_url:
                logger.info("✅ Deja autentificat în Oblio!")
                return True
            
            # Găsește câmpul de email
            logger.info("🔍 Căutare câmp email...")
            email_input = self.wait_for_element(By.ID, "username", timeout=10)
            if not email_input:
                # Încearcă alte selectoare
                email_input = self.wait_for_element(By.NAME, "username", timeout=5)
            if not email_input:
                email_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='email']", timeout=5)
            
            if not email_input:
                raise Exception("Câmpul de email nu a fost găsit!")
            
            logger.info("✅ Câmp email găsit")
            email_input.clear()
            email_input.send_keys(email)
            logger.info(f"⌨️ Email introdus: {email}")
            time.sleep(0.5)
            
            # Găsește câmpul de parolă
            logger.info("🔍 Căutare câmp parolă...")
            password_input = self.wait_for_element(By.ID, "password", timeout=10)
            if not password_input:
                password_input = self.wait_for_element(By.NAME, "password", timeout=5)
            if not password_input:
                password_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='password']", timeout=5)
            
            if not password_input:
                raise Exception("Câmpul de parolă nu a fost găsit!")
            
            logger.info("✅ Câmp parolă găsit")
            password_input.clear()
            password_input.send_keys(password)
            logger.info("⌨️ Parolă introdusă")
            time.sleep(0.5)
            
            # Verifică și închide cookie banner dacă există
            try:
                logger.info("🍪 Verificare cookie banner...")
                cookie_accept_selectors = [
                    (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"),
                    (By.CSS_SELECTOR, ".CybotCookiebotDialogBodyButton"),
                    (By.XPATH, "//button[contains(text(), 'Accept')]"),
                    (By.XPATH, "//button[contains(text(), 'Acceptă')]"),
                ]
                
                for by, selector in cookie_accept_selectors:
                    try:
                        cookie_button = self.driver.find_element(by, selector)
                        if cookie_button.is_displayed():
                            logger.info("🍪 Click pe buton 'Accept Cookies'...")
                            cookie_button.click()
                            time.sleep(1)
                            break
                    except:
                        continue
            except:
                logger.debug("ℹ️ Nu există cookie banner")
            
            # Găsește și apasă butonul de login
            logger.info("🔍 Căutare buton login...")
            login_button = None
            login_selectors = [
                (By.ID, "login-button"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Autentificare')]"),
                (By.CSS_SELECTOR, ".btn-login"),
            ]
            
            for by, selector in login_selectors:
                try:
                    login_button = self.wait_for_clickable(by, selector, timeout=3)
                    if login_button:
                        logger.info(f"✅ Buton login găsit: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                # Încearcă să dai ENTER pe câmpul de parolă
                logger.info("⚠️ Buton login nu găsit, încerc ENTER...")
                password_input.send_keys(Keys.ENTER)
            else:
                logger.info("🖱️ Click pe butonul de login...")
                login_button.click()
            
            # Așteaptă să se încarce pagina după login
            time.sleep(3)
            
            # Verifică dacă login-ul a reușit
            current_url = self.driver.current_url
            logger.info(f"🌐 URL curent după login: {current_url}")

            # ---------------------------------------------------------
            # SUPORT 2FA (Two-Factor Authentication)
            # ---------------------------------------------------------
            if "/tfa" in current_url.lower():
                self._log("🔐 2FA Detectat! Este necesar codul de autentificare.", 'warning')
                
                if self.input_callback:
                    # Cere codul de la utilizator prin WebSocket
                    self._log("⌨️ Aștept codul 2FA de la utilizator...", 'info')
                    code = self.input_callback({
                        'type': '2fa',
                        'message': 'Introduceți codul 2FA (Google Authenticator/Email):'
                    })
                    
                    if code:
                        self._log(f"✅ Cod primit: {code}", 'info')
                        
                        # Găsește câmpul pentru cod
                        code_input = None
                        code_selectors = [
                            (By.NAME, "code"),
                            (By.ID, "code"),
                            (By.CSS_SELECTOR, "input[name='code']"),
                            (By.CSS_SELECTOR, "input[type='text']"), # Risky but fallback
                        ]
                        
                        for by, selector in code_selectors:
                            try:
                                code_input = self.driver.find_element(by, selector)
                                if code_input.is_displayed():
                                    break
                            except:
                                continue
                                
                        if code_input:
                            code_input.clear()
                            code_input.send_keys(code)
                            
                            # Submit
                            code_input.send_keys(Keys.ENTER)
                            time.sleep(3)
                            
                            # Verifică din nou URL-ul
                            current_url = self.driver.current_url
                            if "/tfa" not in current_url.lower() and "login" not in current_url.lower():
                                self._log("✅ Autentificare 2FA reușită!", 'success')
                                return True
                            else:
                                self._log("❌ Cod 2FA incorect sau expirat!", 'error')
                                return False
                        else:
                            self._log("❌ Nu am găsit câmpul pentru codul 2FA!", 'error')
                            return False
                    else:
                        self._log("❌ Nu s-a primit niciun cod 2FA.", 'error')
                        return False
                else:
                    self._log("⚠️ 2FA necesar dar nu există interfață de input. Aștept manual...", 'warning')
                    # Fallback la așteptare manuală
                    return self.wait_for_manual_login(timeout=60)
            
            # Verifică dacă suntem pe dashboard sau stock
            if "dashboard" in current_url or "stock" in current_url or "home" in current_url:
                logger.info("✅ Autentificare reușită în Oblio!")
                return True
            
            # Verifică dacă există mesaj de eroare
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .alert-error")
            if error_elements:
                error_msg = error_elements[0].text
                logger.error(f"❌ Eroare la autentificare: {error_msg}")
                raise Exception(f"Login eșuat: {error_msg}")
            
            # Dacă suntem încă pe pagina de login, probabil e o eroare
            if "login" in current_url:
                raise Exception("Login eșuat - încă pe pagina de login")
            
            logger.warning("⚠️ Nu pot confirma 100% login-ul, dar continui...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Eroare la autentificare: {e}")
            
            # Screenshot pentru debugging - upload la Cloudinary
            try:
                screenshot_url = self.capture_error_screenshot("login", "login_error")
                if screenshot_url:
                    logger.info(f"🖼️ Screenshot eroare login: {screenshot_url}")
            except:
                pass

            return False

    def type_slowly(self, element, text, delay=0.005):
        """
        Tastează text character-by-character (pentru autocomplete)

        Args:
            element: WebElement input
            text: Textul de tastat
            delay: Delay între caractere (secunde) - optimizat pentru viteză
        """
        element.clear()
        for char in text:
            element.send_keys(char)
            if delay > 0:
                time.sleep(delay)
        # logger.debug(f"⌨️ Tastat: {text}")

    def create_production_voucher(self, sku, quantity, oblio_cookies=None, oblio_email=None, oblio_password=None,
                                   nume=None, order_id=None, order_number=None):
        """
        Creează un bon de producție în Oblio

        Args:
            sku (str): Codul SKU al produsului
            quantity (int): Cantitatea
            oblio_cookies (str/dict): Cookies Oblio pentru sesiune (PREFERAT - pe Linux)
            oblio_email (str): Email Oblio (fallback pentru autentificare)
            oblio_password (str): Parolă Oblio (fallback pentru autentificare)
            nume (str): Numele produsului (opțional, pentru salvare în DB)
            order_id (int): ID-ul comenzii din Excel (opțional, pentru tracking)
            order_number (int): Numărul comenzii (opțional, pentru tracking duplicate)

        Returns:
            bool: True dacă succès, False dacă eșec
        """
        # Salvăm parametrii pentru folosire la salvarea în DB
        self._current_voucher_info = {
            'nume': nume or f"Produs {sku}",
            'order_id': order_id,
            'order_number': order_number
        }
        self._log(f"{'='*60}", 'info')
        self._log(f"🎯 Creare bon: SKU={sku}, Cantitate={quantity}", 'info')
        self._log(f"{'='*60}", 'info')

        try:
            # Navighează la pagina de producție
            url = "https://www.oblio.eu/stock/production/"
            
            # Optimizare: Verificăm dacă suntem deja pe pagină pentru a evita reload
            if self.driver.current_url == url:
                self._log(f"ℹ️ Deja pe pagina de producție, skip navigare.", 'info')
                # Resetăm formularul dacă e nevoie (de obicei e gol după save)
            else:
                self._log(f"🌐 Navigare la: {url}", 'info')
                self.driver.get(url)
                # time.sleep(2) # Eliminat sleep fix
            
            # Așteptăm ca elementul principal să fie vizibil
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "pp_name"))
                )
            except:
                self._log("⚠️ Timeout așteptare pagină producție", 'warning')
            
            # Verifică dacă suntem pe pagina de login (nu suntem autentificați)
            if "login" in self.driver.current_url.lower():
                self._log("⚠️ Nu suntem autentificați!", 'warning')

                # PRIORITATE 1: Încearcă cookies (dacă sunt disponibile)
                if oblio_cookies and len(oblio_cookies) > 0:
                    self._log("🍪 Încerc autentificare cu cookies...", 'info')
                    if self.load_cookies_from_json(oblio_cookies):
                        self._log("✅ Autentificare cu cookies reușită!", 'success')
                        # Navighează din nou la pagina de producție
                        self._log(f"🌐 Re-navigare la: {url}", 'info')
                        self.driver.get(url)
                        time.sleep(2)
                    else:
                        self._log("⚠️ Autentificare cu cookies eșuată", 'warning')

                # PRIORITATE 2: Autentificare automată cu email/parolă (dacă sunt disponibile)
                if "login" in self.driver.current_url.lower():
                    if oblio_email and oblio_password:
                        self._log("🔐 Autentificare automată cu email/parolă...", 'info')
                        if not self.login_to_oblio(oblio_email, oblio_password):
                            raise Exception("Autentificare automată eșuată!")
                    elif self.input_callback:
                        # PRIORITATE 3: Login interactiv (dacă avem callback)
                        self._log("🔐 Pornire login interactiv (cu callback)...", 'info')
                        if not self.interactive_login():
                            raise Exception("Login interactiv eșuat!")
                    else:
                        # PRIORITATE 4: Fallback la wait_for_manual_login (fără callback)
                        self._log("👤 Voi aștepta login manual (suportă 2FA)", 'info')
                        if not self.wait_for_manual_login(timeout=90):
                            raise Exception("Login manual eșuat sau timeout!")

                    # După login, navighează la pagina de producție
                    self._log(f"🌐 Navigare la pagina de producție...", 'info')
                    self.driver.get(url)
                    time.sleep(3)  # Așteaptă încărcare pagină

                    # Verifică URL curent
                    current_url = self.driver.current_url
                    self._log(f"📍 URL curent după navigare: {current_url}", 'info')

                    # Dacă nu suntem pe pagina de producție, navighează din nou
                    if "production" not in current_url.lower():
                        self._log(f"⚠️ Nu suntem pe pagina de producție! Re-navighează...", 'warning')
                        self.driver.get(url)
                        time.sleep(3)
                        self._log(f"📍 URL după re-navigare: {self.driver.current_url}", 'info')

            # PASUL 1: Găsește și completează câmpul SKU
            logger.info("🔍 Căutare câmp SKU (#pp_name)...")
            pp_name_input = self.wait_for_element(By.ID, "pp_name", timeout=20)

            if not pp_name_input:
                raise Exception("Element #pp_name nu a fost găsit!")

            logger.info(f"✅ Câmp SKU găsit")

            # Tastează SKU character-by-character pentru autocomplete
            logger.info(f"⌨️ Tastare SKU: {sku}")
            self.type_slowly(pp_name_input, sku, delay=0.01)

            # Trigger autocomplete
            pp_name_input.send_keys(Keys.SPACE)
            pp_name_input.send_keys(Keys.BACKSPACE)
            
            # PASUL 2: Așteaptă și selectează din autocomplete
            logger.info("🔍 Așteptare autocomplete...")
            
            try:
                # Așteaptă explicit lista de autocomplete (max 3 secunde)
                autocomplete_items = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-menu-item"))
                )

                if len(autocomplete_items) > 0:
                    logger.info(f"✅ Autocomplete găsit: {len(autocomplete_items)} rezultate")
                    first_item = autocomplete_items[0]
                    logger.info(f"🖱️ Click pe primul rezultat: {first_item.text[:50]}...")
                    first_item.click()
                    # Așteaptă puțin ca Oblio să populeze câmpurile ascunse (ID produs)
                    time.sleep(0.5)
                else:
                    logger.warning("⚠️ Autocomplete gol, încerc ENTER...")
                    pp_name_input.send_keys(Keys.ENTER)
                    time.sleep(0.5)
            except TimeoutException:
                logger.warning("⚠️ Timeout autocomplete, încerc ENTER...")
                pp_name_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ Eroare autocomplete: {e}, încerc ENTER...")
                pp_name_input.send_keys(Keys.ENTER)
                time.sleep(0.5)

            # PASUL 3: Verifică că produsul a fost selectat
            logger.info("🔍 Verificare selecție produs...")
            time.sleep(1)

            # Verifică dacă a apărut pop-up cu mesaj de eroare/instrucțiuni
            try:
                modal_message = self.driver.find_element(By.CSS_SELECTOR, "#modal-message")
                if modal_message.is_displayed():
                    modal_text = modal_message.text
                    if "Selecteaza produsul" in modal_text or "produsul pentru productie" in modal_text.lower():
                        logger.error(f"❌ Pop-up detectat: Produsul {sku} NU există în Oblio!")
                        # Închide pop-up-ul
                        try:
                            ok_btn = modal_message.find_element(By.CSS_SELECTOR, ".ok-message-modal")
                            ok_btn.click()
                            time.sleep(0.5)
                        except:
                            pass
                        raise Exception(f"Produsul cu SKU '{sku}' NU EXISTĂ în baza de date Oblio! Verifică SKU-ul.")
            except NoSuchElementException:
                pass  # Nu există pop-up, continuăm normal

            try:
                pp_name_id = self.driver.find_element(By.ID, "pp_name_id")
                if pp_name_id.get_attribute("value"):
                    logger.info(f"✅ Produs selectat: ID={pp_name_id.get_attribute('value')}")
                else:
                    raise Exception(f"Produsul cu SKU '{sku}' nu a fost selectat! SKU invalid sau nu există în baza de date Oblio.")
            except NoSuchElementException:
                raise Exception("Element #pp_name_id nu a fost găsit!")

            # PASUL 4: Completează cantitatea
            logger.info(f"🔢 Completare cantitate: {quantity}")
            pp_quantity_input = self.wait_for_element(By.ID, "pp_quantity", timeout=10)

            if not pp_quantity_input:
                raise Exception("Element #pp_quantity nu a fost găsit!")

            # FIX: Șterge COMPLET câmpul înainte de a introduce valoarea
            # clear() uneori nu funcționează, deci folosim Ctrl+A + Delete
            pp_quantity_input.click()
            time.sleep(0.2)
            pp_quantity_input.send_keys(Keys.CONTROL + "a")  # Select all
            time.sleep(0.1)
            pp_quantity_input.send_keys(Keys.DELETE)  # Delete
            time.sleep(0.1)
            pp_quantity_input.send_keys(str(quantity))  # Introduce cantitatea
            time.sleep(0.5) # Așteaptă ca Oblio să calculeze rețeta (optimizat)
            logger.info(f"✅ Cantitate setată: {quantity}")

            # --- VERIFICARE STOC (NOU) ---
            logger.info("🔍 Verificare stoc materii prime...")
            try:
                # Caută input-ul de cantitate consumată (ap_1_quantity2)
                # Acesta apare automat după ce Oblio încarcă rețeta
                consumed_qty_input = self.wait_for_element(By.ID, "ap_1_quantity2", timeout=3)
                
                if consumed_qty_input:
                    consumed_val = float(consumed_qty_input.get_attribute('value') or 0)
                    
                    # Caută span-ul cu stocul (ap_1_name_note)
                    stock_span = self.driver.find_element(By.ID, "ap_1_name_note")
                    stock_text = stock_span.text # Ex: "Stoc: 0.02 buc"
                    
                    # Parsează stocul
                    import re
                    match_stock = re.search(r'Stoc:\s*([\d\.]+)', stock_text)
                    if match_stock:
                        stock_val = float(match_stock.group(1))
                        
                        logger.info(f"📊 Verificare stoc: Necesar={consumed_val}, Disponibil={stock_val}")
                        
                        if consumed_val > stock_val:
                            logger.warning(f"⚠️ STOC INSUFICIENT! Necesar: {consumed_val}, Disponibil: {stock_val}")
                            self._log(f"⚠️ STOC INSUFICIENT pentru {sku}! Necesar: {consumed_val}, Disponibil: {stock_val}. Se sare peste acest bon.", 'warning')
                            # Captură screenshot pentru stoc insuficient
                            self.capture_error_screenshot(sku, "stoc_insuficient")

                            # Închide tab-ul curent sau navighează înapoi pentru a nu bloca procesul
                            # Deoarece suntem pe pagina de creare, putem doar să returnăm False
                            # și să lăsăm bucla principală să continue
                            return False
                    else:
                        logger.warning(f"⚠️ Nu s-a putut parsa stocul din text: '{stock_text}'")
                else:
                    logger.info("ℹ️ Nu s-a găsit input-ul de consum (poate nu există rețetă sau s-a încărcat greu)")
            
            except Exception as e:
                logger.warning(f"⚠️ Eroare la verificarea stocului (non-blocant): {e}")
            # --- END VERIFICARE STOC ---

            # PASUL 5: Click pe butonul de previzualizare/salvare
            logger.info("🔍 Căutare buton salvare...")

            # Încearcă diferite selectoare
            save_button = None
            save_selectors = [
                (By.ID, "invoice_preview_btn"),
                (By.CSS_SELECTOR, "a[onclick*='submit_form_doc']"),
                (By.CSS_SELECTOR, ".btn-submit"),
                (By.XPATH, "//a[contains(text(), 'Previzualizare')]"),
                (By.CSS_SELECTOR, "button[type='submit']")
            ]

            for by, selector in save_selectors:
                try:
                    save_button = self.wait_for_clickable(by, selector, timeout=5)
                    if save_button:
                        logger.info(f"✅ Buton salvare găsit: {selector}")
                        break
                except:
                    continue

            if not save_button:
                raise Exception("Butonul de salvare nu a fost găsit!")

            # DIAGNOSTIC COMPLET: Dump all form fields înainte de click
            logger.info("🔍 DIAGNOSTIC: Verificare TOATE câmpurile formularului...")
            try:
                form_diagnostic = self.driver.execute_script("""
                    var diagnostics = {
                        formFields: {},
                        requiredEmpty: [],
                        validationErrors: [],
                        consoleErrors: []
                    };

                    // Toate inputurile din form
                    var inputs = document.querySelectorAll('input, select, textarea');
                    inputs.forEach(function(input) {
                        var id = input.id || input.name || 'unnamed';
                        var value = input.value || '';
                        var required = input.required || input.classList.contains('required');
                        var visible = input.offsetParent !== null;

                        diagnostics.formFields[id] = {
                            value: value,
                            type: input.type || input.tagName,
                            required: required,
                            visible: visible
                        };

                        // Check required fields
                        if (required && visible && !value) {
                            diagnostics.requiredEmpty.push(id);
                        }
                    });

                    // Caută mesaje de validare vizibile
                    var errorMessages = document.querySelectorAll('.error, .invalid-feedback, .text-danger, .alert-danger');
                    errorMessages.forEach(function(msg) {
                        if (msg.offsetParent !== null && msg.textContent.trim()) {
                            diagnostics.validationErrors.push(msg.textContent.trim());
                        }
                    });

                    return diagnostics;
                """)

                logger.info("📊 FORM FIELDS:")
                for field_id, field_info in form_diagnostic.get('formFields', {}).items():
                    if field_info.get('visible', False) and (field_info.get('value') or field_info.get('required')):
                        logger.info(f"  • {field_id}: {field_info.get('value', 'EMPTY')} (required: {field_info.get('required', False)})")

                if form_diagnostic.get('requiredEmpty'):
                    logger.warning(f"⚠️ CÂMPURI OBLIGATORII GOALE: {', '.join(form_diagnostic['requiredEmpty'])}")

                if form_diagnostic.get('validationErrors'):
                    logger.error(f"❌ ERORI VALIDARE: {', '.join(form_diagnostic['validationErrors'])}")

            except Exception as e:
                logger.warning(f"⚠️ Eroare diagnostic form: {e}")

            # Încearcă să închidă orice modal care ar putea bloca butonul
            try:
                logger.info("🔍 Verificare modal-uri care ar putea bloca...")
                modal_close_selectors = [
                    (By.CSS_SELECTOR, "#modal-message .ok-message-modal"),
                    (By.CSS_SELECTOR, "#modal-message .message-modal-close"),
                    (By.CSS_SELECTOR, ".modal.show .btn[data-dismiss='modal']"),
                    (By.CSS_SELECTOR, ".modal.show button[type='button']"),
                ]

                for by, selector in modal_close_selectors:
                    try:
                        modal_button = self.driver.find_element(by, selector)
                        if modal_button.is_displayed():
                            logger.info(f"✅ Modal găsit, închid: {selector}")
                            modal_button.click()
                            time.sleep(1)
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"ℹ️ Nu există modal de închis: {e}")

            # Scroll la buton pentru a fi sigur că e vizibil
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(0.5)
                logger.info("✅ Scroll la butonul de salvare")
            except:
                pass

            # Click salvare (Previzualizare) - FORȚAT prin JavaScript
            logger.info("🖱️ Click buton salvare (prin JavaScript pentru bypass validare UI)...")

            # Încearcă direct JavaScript click pentru bypass event handlers
            try:
                # Folosește JavaScript direct pe onclick handler
                click_result = self.driver.execute_script("""
                    var btn = arguments[0];

                    // Capturează onclick handler
                    var onclickAttr = btn.getAttribute('onclick');
                    console.log('Onclick handler:', onclickAttr);

                    // Execută direct funcția din onclick
                    if (onclickAttr && onclickAttr.includes('submit_form_doc')) {
                        // Extrage numele formului din onclick
                        var match = onclickAttr.match(/submit_form_doc\\('([^']+)'\\)/);
                        if (match && match[1]) {
                            var formName = match[1];
                            console.log('Form name:', formName);

                            // Găsește form-ul
                            var form = document.querySelector('form[name="' + formName + '"]') ||
                                      document.querySelector('form#' + formName) ||
                                      document.querySelector('form');

                            if (form) {
                                console.log('Form găsit, submit...');
                                // Submit direct
                                form.submit();
                                return 'FORM_SUBMITTED_DIRECT';
                            } else {
                                console.log('Form NU găsit!');
                                return 'FORM_NOT_FOUND';
                            }
                        }
                    }

                    // Fallback: click normal
                    btn.click();
                    return 'CLICKED_NORMAL';
                """, save_button)

                logger.info(f"✅ Click executat: {click_result}")
                time.sleep(2)

            except Exception as e:
                logger.warning(f"⚠️ JavaScript click eșuat: {e}")
                # Ultimate fallback: click normal
                try:
                    save_button.click()
                    time.sleep(1)
                except Exception as e2:
                    logger.error(f"❌ Click normal EȘUAT: {e2}")

            # DEBUG: Verifică JavaScript errors
            try:
                js_errors = self.driver.execute_script(
                    "return window.jsErrors || [];"
                )
                if js_errors:
                    logger.warning(f"⚠️ JavaScript errors găsite: {js_errors}")
            except:
                pass

            # DEBUG: Screenshot după click pentru debugging (upload Cloudinary)
            try:
                screenshot_url = self.capture_error_screenshot(sku, "after_click")
                if screenshot_url:
                    logger.info(f"🖼️ Screenshot după click: {screenshot_url}")
            except:
                pass

            # PASUL 6: Verifică dacă am fost redirectat la pagina de preview
            logger.info("🔍 Verificare redirect la pagina de preview...")
            time.sleep(3)  # Mărit de la 1.5s la 3s pentru a aștepta redirect

            current_url = self.driver.current_url
            logger.info(f"📍 URL curent după submit: {current_url}")

            success = False
            production_id = None

            # Verifică dacă am fost redirectat la preview_production
            if "/stock/preview_production/" in current_url:
                # Extragem ID-ul bonului din URL
                import re
                match = re.search(r'/preview_production/(\d+)', current_url)
                if match:
                    production_id = match.group(1)
                    logger.info(f"✅ REDIRECT LA PREVIEW! ID producție: {production_id}")

                    # PASUL 7: Click pe butonul "Lanseaza in Productie"
                    logger.info("🔍 Căutare buton 'Lanseaza in Productie'...")
                    launch_button = None

                    # Încearcă mai multe selectoare pentru butonul de lansare
                    launch_selectors = [
                        (By.CSS_SELECTOR, f"a.btn.btn-warning.issue-btn[href*='production_save/{production_id}']"),
                        (By.XPATH, f"//a[contains(@href, 'production_save/{production_id}')]"),
                        (By.XPATH, "//a[contains(text(), 'Lanseaza in Productie')]"),
                        (By.CSS_SELECTOR, "a.issue-btn"),
                    ]

                    for by, selector in launch_selectors:
                        try:
                            launch_button = self.wait_for_clickable(by, selector, timeout=5)
                            if launch_button:
                                logger.info(f"✅ Buton 'Lanseaza in Productie' găsit: {selector}")
                                break
                        except:
                            continue

                    if not launch_button:
                        raise Exception("Butonul 'Lanseaza in Productie' nu a fost găsit!")

                    logger.info("🖱️ Click pe 'Lanseaza in Productie'...")
                    launch_button.click()
                    time.sleep(0.5) # Optimizat: 1.5s → 0.5s

                    # PASUL 8: Click pe butonul OK din popup modal
                    logger.info("🔍 Căutare buton OK în popup modal...")
                    ok_button = None

                    ok_selectors = [
                        (By.CSS_SELECTOR, "button.btn.btn-warning.ok-message-modal"),
                        (By.CSS_SELECTOR, ".ok-message-modal"),
                        (By.XPATH, "//button[contains(@class, 'ok-message-modal')]"),
                        (By.CSS_SELECTOR, "#modal-message .btn-warning"),
                    ]

                    for by, selector in ok_selectors:
                        try:
                            ok_button = self.wait_for_clickable(by, selector, timeout=2)
                            if ok_button:
                                logger.info(f"✅ Buton OK găsit: {selector}")
                                break
                        except:
                            continue

                    if ok_button:
                        logger.info("🖱️ Click pe butonul OK din popup...")
                        ok_button.click()
                        time.sleep(0.5) # Optimizat: 1s → 0.5s
                    else:
                        logger.warning("⚠️ Butonul OK nu a fost găsit (poate nu a apărut popup-ul)")

                    # PASUL 9: Click pe butonul "Finalizeaza Productia"
                    logger.info("🔍 Căutare buton 'Finalizeaza Productia'...")
                    finalize_button = None

                    finalize_selectors = [
                        (By.CSS_SELECTOR, f"a.btn.btn-warning[href*='production_complete/{production_id}']"),
                        (By.XPATH, f"//a[contains(@href, 'production_complete/{production_id}')]"),
                        (By.XPATH, "//a[contains(text(), 'Finalizeaza Productia')]"),
                        (By.CSS_SELECTOR, "a[href*='production_complete']"),
                    ]

                    for by, selector in finalize_selectors:
                        try:
                            finalize_button = self.wait_for_clickable(by, selector, timeout=2)
                            if finalize_button:
                                logger.info(f"✅ Buton 'Finalizeaza Productia' găsit: {selector}")
                                break
                        except:
                            continue

                    if not finalize_button:
                        raise Exception("Butonul 'Finalizeaza Productia' nu a fost găsit!")

                    logger.info("🖱️ Click pe 'Finalizeaza Productia'...")
                    finalize_button.click()
                    time.sleep(1) # Optimizat: 2s → 1s

                    # PASUL 10: Handler pentru popup-ul de confirmare preț
                    # "Pretul de vanzare este mai mic decat costul de achizitie. Continuati?"
                    logger.info("🔍 Verificare popup confirmare preț...")
                    try:
                        # Așteaptă puțin pentru a permite popup-ului să apară
                        time.sleep(0.5)

                        # Căutăm butonul "DA" din popup-ul de confirmare preț
                        price_confirm_selectors = [
                            (By.CSS_SELECTOR, "button.ok-confirm-modal1"),
                            (By.CSS_SELECTOR, ".ok-confirm-modal1"),
                            (By.XPATH, "//button[contains(@class, 'ok-confirm-modal1')]"),
                            (By.XPATH, "//button[contains(text(), 'DA')]"),
                        ]

                        price_confirm_button = None
                        for by, selector in price_confirm_selectors:
                            try:
                                price_confirm_button = WebDriverWait(self.driver, 2).until(
                                    EC.element_to_be_clickable((by, selector))
                                )
                                if price_confirm_button and price_confirm_button.is_displayed():
                                    logger.info(f"✅ Popup confirmare preț detectat! Selector: {selector}")
                                    break
                            except:
                                continue

                        if price_confirm_button and price_confirm_button.is_displayed():
                            logger.info("🖱️ Click pe butonul 'DA' din popup-ul de confirmare preț...")
                            price_confirm_button.click()
                            time.sleep(1)
                            logger.info("✅ Popup confirmare preț acceptat!")
                        else:
                            logger.info("ℹ️ Popup confirmare preț nu a apărut (preț OK)")

                    except TimeoutException:
                        logger.info("ℹ️ Popup confirmare preț nu a apărut (timeout)")
                    except Exception as e:
                        logger.warning(f"⚠️ Eroare la handler popup confirmare preț: {e}")

                    # PASUL 11: Verificare finalizare în raportul de producție
                    logger.info("🔍 Verificare finalizare în raportul de producție...")
                    success = True

            # Metodă 2: Dacă nu am fost redirectat, verificăm în raportul de producție
            if not success:
                # Verificăm dacă există un mesaj de eroare pe pagină
                try:
                    error_msg = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger, .error-message, .text-danger")
                    if error_msg.is_displayed():
                        error_text = error_msg.text.strip()
                        logger.error(f"❌ EROARE OBLIO DETECTATĂ: {error_text}")
                        raise Exception(f"Eroare Oblio: {error_text}")
                except NoSuchElementException:
                    pass

                logger.info("🔍 Navigare la raportul de producție pentru verificare...")
                self.driver.get("https://www.oblio.eu/report/production")
                time.sleep(3)

                # Căutăm un bon cu data de azi și SKU-ul nostru
                from datetime import datetime
                today = datetime.now().strftime("%d.%m.%Y")
                logger.info(f"🔍 Căutare bon cu data {today} și SKU {sku}...")

                try:
                    # Căutăm în tabel un rând care conține data de azi
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "#content-table tbody tr.table_row")
                    logger.info(f"📊 Găsite {len(rows)} bonuri în raport")

                    for row in rows[:10]:  # Verificăm primele 10 bonuri (cele mai recente)
                        try:
                            # Verificăm data
                            date_elem = row.find_element(By.CSS_SELECTOR, ".text-muted")
                            date_text = date_elem.text.strip()

                            if today in date_text:
                                logger.info(f"🔍 Găsit bon cu data de azi: {date_text}")

                                # Verificăm SKU-ul (există în text sau în link)
                                row_text = row.text.lower()
                                sku_lower = sku.lower()

                                # Căutăm SKU-ul în textul rândului
                                if sku_lower in row_text or sku.replace("-", " ").lower() in row_text:
                                    # Extragem numărul bonului
                                    bon_link = row.find_element(By.CSS_SELECTOR, "a.font-bold")
                                    bon_number = bon_link.text.strip()

                                    logger.info(f"✅ GĂSIT BON NOU! {bon_number} din {date_text}")
                                    logger.info(f"✅ Conține SKU: {sku}")

                                    # Extragem ID-ul din link
                                    bon_href = bon_link.get_attribute('href')
                                    match = re.search(r'/preview_production/(\d+)', bon_href)
                                    if match:
                                        production_id = match.group(1)
                                        logger.info(f"✅ ID producție: {production_id}")

                                    success = True
                                    break
                        except Exception as e:
                            logger.debug(f"⏭️ Rând ignorat: {e}")
                            continue

                    if not success:
                        logger.warning(f"⚠️ NU s-a găsit niciun bon nou cu data {today} și SKU {sku}")

                except Exception as e:
                    logger.error(f"❌ Eroare la verificarea raportului: {e}")

            # Rezultat final
            if success:
                msg = f"🎉 BON DE PRODUCȚIE FINALIZAT CU SUCCES! SKU={sku}, Cantitate={quantity}"
                if production_id:
                    msg += f", ID={production_id}"
                    msg += f"\n   📋 Link: https://www.oblio.eu/stock/preview_production/{production_id}"
                self._log(msg, 'success')
                self.stats['success'] += 1

                # Salvare în DB cu order tracking
                try:
                    voucher_info = getattr(self, '_current_voucher_info', {})
                    nume = voucher_info.get('nume', f"Produs {sku}")
                    order_id = voucher_info.get('order_id')
                    order_number = voucher_info.get('order_number')

                    adauga_bon(sku, nume, quantity, order_id, order_number)
                    if order_number:
                        self._log(f"💾 Salvat în DB: {sku} comanda #{order_number}", 'info')
                    else:
                        self._log(f"💾 Salvat în DB: {sku}", 'info')
                except Exception as e:
                    self._log(f"⚠️ Eroare salvare DB: {e}", 'warning')

                return True
            else:
                self._log(f"❌ BONUL NU A FOST FINALIZAT! SKU={sku} - Eroare la finalizarea producției", 'error')
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'sku': sku,
                    'quantity': quantity,
                    'error': 'Bon nu a fost finalizat - eroare la unul din pașii de finalizare'
                })
                return False

        except Exception as e:
            self._log(f"❌ EROARE la crearea bonului: {e}", 'error')
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'sku': sku,
                'quantity': quantity,
                'error': str(e)
            })

            # Screenshot pentru debugging - upload la Cloudinary cu URL în log
            try:
                screenshot_url = self.capture_error_screenshot(sku, "voucher_error")
                if screenshot_url:
                    self._log(f"🖼️ Screenshot eroare: {screenshot_url}", 'error')
            except:
                pass

            return False

    def create_transfer_note(self, products_list):
        """
        Creează o Notă de Transfer pentru o listă de produse
        Transferă din 'Materiale consumabile' în 'Marfuri'

        Args:
            products_list (list): Lista de produse [{'sku': '...', 'cantitate': ...}]

        Returns:
            bool: True dacă transferul a reușit, False altfel
        """
        if not products_list:
            self._log("⚠️ Nu există produse pentru transfer!", 'warning')
            return False

        self._log(f"🚚 START TRANSFER GESTIUNE: {len(products_list)} produse", 'info')
        self._log(f"📍 Din 'Materiale consumabile' -> 'Marfuri'", 'info')

        try:
            # Navigare la pagina de transfer
            url = "https://www.oblio.eu/stock/transfer/"
            self._log(f"🌐 Navigare la: {url}", 'info')
            self.driver.get(url)
            time.sleep(3)

            # PASUL 1: Selectare Gestiune Sursă (Materiale consumabile)
            self._log("🔍 Selectare gestiune sursă: Materiale consumabile...", 'info')
            
            try:
                from selenium.webdriver.support.ui import Select
                gestiune_select = Select(self.wait_for_element(By.ID, "gestiune1"))
                gestiune_select.select_by_value("237258") # Materiale consumabile
                self._log("✅ Gestiune sursă selectată: Materiale consumabile (237258)", 'info')
                time.sleep(1)
                
                # Gestiunea Destinație este implicit "Marfuri" (237255), nu o mai selectăm explicit
                
            except Exception as e:
                raise Exception(f"Nu s-a putut selecta gestiunea: {e}")

            # PASUL 2: Confirmare Popup "OK, am inteles!"
            self._log("🔍 Căutare popup confirmare...", 'info')
            try:
                ok_button = self.wait_for_clickable(By.CSS_SELECTOR, ".ok-message-modal", timeout=5)
                if ok_button:
                    self._log("✅ Popup găsit, click OK...", 'info')
                    ok_button.click()
                    time.sleep(1.5)
            except:
                self._log("ℹ️ Popup-ul nu a apărut sau a fost deja închis", 'info')

            # PASUL 3: Adăugare produse în listă
            for i, prod in enumerate(products_list, 1):
                sku = prod.get('sku')
                quantity = prod.get('cantitate', 1)
                
                self._log(f"➕ Adăugare produs {i}/{len(products_list)}: SKU={sku}, Qty={quantity}", 'info')

                # --- VERIFICARE POPUP (NOU) ---
                # Verificăm dacă a rămas un popup deschis de la produsul anterior
                try:
                    confirm_btn = self.wait_for_clickable(By.CSS_SELECTOR, ".ok-confirm-modal", timeout=1)
                    if confirm_btn and confirm_btn.is_displayed():
                        self._log("⚠️ Popup rămas deschis detectat. Click DA...", 'warning')
                        try:
                            confirm_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", confirm_btn)
                        time.sleep(1.5)
                except:
                    pass
                
                # Așteptăm să dispară orice modal backdrop
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-backdrop"))
                    )
                except:
                    pass # Ignorăm timeout, poate nu există backdrop
                # --- END VERIFICARE POPUP ---

                # 3.1 Introducere SKU
                name_input = self.wait_for_element(By.ID, "ap_name1")
                if not name_input:
                    raise Exception("Câmpul de căutare produs nu a fost găsit!")
                
                # Asigură-te că elementul este vizibil și interactabil
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
                time.sleep(0.5)
                
                # Așteaptă ca elementul să fie interactabil
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "ap_name1")))
                except:
                    self._log("⚠️ Timeout așteptare input SKU interactabil", 'warning')

                name_input.clear()
                self.type_slowly(name_input, sku, delay=0.03) # Puțin mai lent pentru stabilitate
                name_input.send_keys(Keys.SPACE)
                name_input.send_keys(Keys.BACKSPACE)
                
                # 3.2 Selectare din autocomplete (Robust)
                product_selected = False
                for attempt in range(3):
                    try:
                        # Așteaptă explicit lista de autocomplete
                        autocomplete_items = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-menu-item"))
                        )
                        
                        if len(autocomplete_items) > 0:
                            # Așteaptă ca primul element să fie clickable
                            first_item = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable(autocomplete_items[0])
                            )
                            first_item.click()
                            
                            # Verifică dacă s-a populat un hidden field (ex: ap_id_1 sau similar)
                            # Sau așteaptă dispariția autocomplete-ului
                            try:
                                WebDriverWait(self.driver, 2).until(
                                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui-menu-item"))
                                )
                            except: pass
                            
                            time.sleep(1.0) # Așteaptă popularea câmpurilor
                            product_selected = True
                            break
                        else:
                            self._log(f"⚠️ Autocomplete gol pentru {sku} (încercare {attempt+1})", 'warning')
                            time.sleep(1)
                            
                    except StaleElementReferenceException:
                        self._log(f"⚠️ Stale element la selectare produs {sku}, reîncerc...", 'warning')
                        continue
                    except Exception as e:
                        self._log(f"⚠️ Eroare selectare produs {sku}: {e}", 'warning')
                        break
                
                if not product_selected:
                    self._log(f"❌ Nu s-a putut selecta produsul {sku}!", 'error')
                    # Putem încerca un ENTER ca ultimă soluție
                    name_input.send_keys(Keys.ENTER)
                    time.sleep(1)

                # 3.3 Setare Cantitate
                qty_input = self.wait_for_element(By.ID, "ap_quantity")
                # Asigură-te că elementul este vizibil
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", qty_input)
                
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "ap_quantity")))
                    qty_input.click()
                except:
                    self.driver.execute_script("arguments[0].click();", qty_input)
                    
                time.sleep(0.2)
                qty_input.send_keys(Keys.CONTROL + "a")
                qty_input.send_keys(Keys.DELETE)
                qty_input.send_keys(str(quantity))
                
                # 3.4 Setare Preț (OBLIGATORIU pentru transfer)
                # Așteptăm puțin să vedem dacă Oblio completează prețul
                time.sleep(1.0)
                try:
                    price_input = self.driver.find_element(By.ID, "ap_price_2")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", price_input)
                    
                    # Verificăm dacă are valoare
                    current_val = price_input.get_attribute("value")
                    
                    # Dacă e gol sau 0, mai așteptăm puțin
                    if not current_val or current_val.strip() == "" or current_val == "0" or current_val == "0.00":
                        time.sleep(1.0)
                        current_val = price_input.get_attribute("value")
                    
                    # Verificăm din nou și setăm default 19.99 dacă e necesar
                    should_set_price = False
                    if not current_val:
                        should_set_price = True
                    else:
                        try:
                            if float(current_val) == 0:
                                should_set_price = True
                        except:
                            should_set_price = True

                    if should_set_price:
                        self._log("⚠️ Preț necompletat sau 0. Setez valoarea standard 19.99...", 'warning')
                        try:
                            price_input.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", price_input)
                            
                        price_input.send_keys(Keys.CONTROL + "a")
                        price_input.send_keys(Keys.DELETE)
                        price_input.send_keys("19.99")
                    else:
                        self._log(f"ℹ️ Preț preluat automat: {current_val}", 'info')
                        
                except Exception as e:
                    self._log(f"⚠️ Eroare la setarea prețului: {e}", 'warning')

                # 3.5 Click Adaugă
                add_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn-add-product-on-doc")
                # Scroll la buton pentru a evita suprapunerea
                self.driver.execute_script("arguments[0].scrollIntoView(true);", add_btn)
                time.sleep(0.5)
                
                # Folosim DOAR execute_script pentru a evita dublarea click-urilor
                self.driver.execute_script("arguments[0].click();", add_btn)
                    
                self._log(f"✅ Produs {sku} adăugat în listă", 'info')
                
                # Așteptăm ca input-ul să se golească (semn că a fost adăugat)
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda d: d.find_element(By.ID, "ap_name1").get_attribute("value") == ""
                    )
                    self._log("✅ Input golit - produs adăugat cu succes.", 'info')
                except:
                    self._log("⚠️ Input-ul nu s-a golit. Posibilă eroare la adăugare sau popup.", 'warning')

                # --- VERIFICARE POPUP CONFIRMARE PREȚ (NOU) ---
                # Uneori apare un popup care întreabă dacă vrem să modificăm prețul
                try:
                    # Căutăm butonul "DA" din popup (.ok-confirm-modal)
                    # Mărit timeout la 3 secunde pentru a fi siguri
                    confirm_btn = self.wait_for_clickable(By.CSS_SELECTOR, ".ok-confirm-modal", timeout=3)
                    if confirm_btn:
                        self._log("⚠️ Popup confirmare preț detectat. Click DA...", 'warning')
                        try:
                            confirm_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", confirm_btn)
                        
                        # Așteptăm să dispară popup-ul
                        time.sleep(1.5)
                        try:
                            WebDriverWait(self.driver, 2).until(
                                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ok-confirm-modal"))
                            )
                        except:
                            pass
                except:
                    # Popup-ul nu a apărut, continuăm
                    pass
                # --- END VERIFICARE POPUP ---
                
                # Așteaptă ca rândul să fie procesat și input-ul să fie golit/resetat
                # Verificăm dacă input-ul de nume este gol sau așteptăm puțin mai mult
                time.sleep(2) 


            # PASUL 4: Previzualizare Transfer
            self._log("🔍 Finalizare: Click Previzualizare Transfer...", 'info')
            
            # Încearcă să închidă orice modal care ar putea bloca butonul (ex: popup preț rămas)
            try:
                modal_close_selectors = [
                    (By.CSS_SELECTOR, ".ok-confirm-modal"),
                    (By.CSS_SELECTOR, "#modal-message .ok-message-modal"),
                    (By.CSS_SELECTOR, ".modal.show .btn[data-dismiss='modal']"),
                ]
                for by, selector in modal_close_selectors:
                    try:
                        modal_button = self.driver.find_element(by, selector)
                        if modal_button.is_displayed():
                            self._log(f"⚠️ Modal blocant găsit, închid: {selector}", 'warning')
                            try:
                                modal_button.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", modal_button)
                            time.sleep(1)
                    except:
                        continue
            except:
                pass

            # Căutare buton salvare (mai multe variante)
            preview_btn = None
            save_selectors = [
                (By.ID, "invoice_preview_btn"),
                (By.CSS_SELECTOR, "a[onclick*='submit_form_doc']"),
                (By.XPATH, "//a[contains(text(), 'Previzualizare')]"),
                (By.CSS_SELECTOR, ".btn-submit")
            ]

            for by, selector in save_selectors:
                try:
                    preview_btn = self.wait_for_clickable(by, selector, timeout=3)
                    if preview_btn:
                        break
                except:
                    continue
            
            if not preview_btn:
                # Fallback: încearcă să găsească formularul și să-i dea submit direct
                self._log("⚠️ Buton previzualizare negăsit, încerc submit direct pe form...", 'warning')
                self.driver.execute_script("submit_form_doc();")
            else:
                # Scroll și Click
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", preview_btn)
                    time.sleep(0.5)
                    
                    # Click robust (încearcă să execute funcția din onclick direct)
                    self.driver.execute_script("""
                        var btn = arguments[0];
                        var onclickAttr = btn.getAttribute('onclick');
                        if (onclickAttr && onclickAttr.includes('submit_form_doc')) {
                            submit_form_doc(); // Execută funcția globală Oblio
                        } else {
                            btn.click();
                        }
                    """, preview_btn)
                except Exception as e:
                    self._log(f"⚠️ Eroare click previzualizare: {e}", 'warning')
                    self.driver.execute_script("submit_form_doc();")

            # --- VERIFICARE POST-SUBMIT (POPUP-URI SAU REDIRECT) ---
            # Așteptăm redirect sau popup
            max_retries = 5
            for i in range(max_retries):
                time.sleep(1)
                
                # 1. Verificăm dacă a apărut un popup de confirmare (ex: preț modificat)
                try:
                    confirm_btn = self.driver.find_element(By.CSS_SELECTOR, ".ok-confirm-modal")
                    if confirm_btn.is_displayed():
                        self._log("⚠️ Popup confirmare detectat DUPĂ submit. Click DA...", 'warning')
                        try:
                            confirm_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", confirm_btn)
                        time.sleep(2) # Așteptăm să se proceseze
                        continue # Mai verificăm o dată
                except:
                    pass

                # 2. Verificăm dacă a apărut un mesaj de eroare (modal)
                try:
                    error_modal = self.driver.find_element(By.CSS_SELECTOR, "#modal-message")
                    if error_modal.is_displayed():
                        error_text = error_modal.text
                        self._log(f"❌ EROARE afișată în modal: {error_text}", 'error')

                        # SCREENSHOT 1: Cu eroarea - upload Cloudinary cu URL în log
                        try:
                            screenshot_url = self.capture_error_screenshot("transfer", "error_modal")
                            if screenshot_url:
                                self._log(f"🖼️ Screenshot eroare modal: {screenshot_url}", 'error')
                        except:
                            pass

                        # Încercăm să închidem modalul
                        try:
                            ok_btn = error_modal.find_element(By.CSS_SELECTOR, ".ok-message-modal")
                            ok_btn.click()
                            time.sleep(1)
                        except:
                            pass

                        # SCREENSHOT 2: Produsele de sus (pentru debug stoc) - upload Cloudinary
                        try:
                            self.driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(1)
                            screenshot_url2 = self.capture_error_screenshot("transfer", "products_debug")
                            if screenshot_url2:
                                self._log(f"🖼️ Screenshot produse debug: {screenshot_url2}", 'info')
                        except:
                            pass
                except:
                    pass

                # 3. Verificăm dacă s-a făcut redirect
                if "preview_transfer" in self.driver.current_url:
                    break
            # --- END VERIFICARE POST-SUBMIT ---
            
            # Așteptare redirect
            time.sleep(3)
            
            # Verificare URL
            if "/stock/preview_transfer/" not in self.driver.current_url:
                self._log("⚠️ Redirect întârziat, mai încerc o dată submit...", 'warning')
                self.driver.execute_script("submit_form_doc();")
                time.sleep(3)

            if "/stock/preview_transfer/" in self.driver.current_url:
                self._log("✅ Redirectat la previzualizare transfer", 'info')
                
                # PASUL 5: Emite Nota Transfer
                self._log("🔍 Căutare buton 'Emite Nota transfer'...", 'info')
                issue_btn = self.wait_for_clickable(By.CSS_SELECTOR, ".issue-btn")
                
                if issue_btn:
                    issue_btn.click()
                    self._log("🖱️ Click 'Emite Nota transfer'", 'info')
                    time.sleep(3)
                    self._log("🎉 TRANSFER FINALIZAT CU SUCCES!", 'success')
                    return True
                else:
                    raise Exception("Butonul de emitere nu a fost găsit!")
            else:
                # DIAGNOSTIC: De ce nu s-a făcut redirectarea?
                self._log("❌ Redirect eșuat. Caut erori pe pagină...", 'error')
                
                # 1. Caută mesaje de eroare standard
                try:
                    error_elems = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .text-danger, .error-message, .invalid-feedback, .error")
                    found_errors = False
                    for elem in error_elems:
                        if elem.is_displayed() and elem.text.strip():
                            self._log(f"❌ EROARE PE PAGINĂ: {elem.text.strip()}", 'error')
                            found_errors = True
                    
                    if not found_errors:
                        self._log("ℹ️ Nu am găsit mesaje de eroare explicite pe pagină.", 'warning')
                except:
                    pass

                raise Exception("Nu s-a făcut redirectarea la pagina de previzualizare!")

        except Exception as e:
            self._log(f"❌ EROARE TRANSFER: {e}", 'error')

            # Screenshot pentru debugging - upload la Cloudinary cu URL în log
            try:
                screenshot_url = self.capture_error_screenshot("transfer", "transfer_error")
                if screenshot_url:
                    self._log(f"🖼️ Screenshot eroare transfer: {screenshot_url}", 'error')
            except:
                pass

            return False

    def create_production_vouchers_batch(self, batch_list, oblio_cookies=None, oblio_email=None, oblio_password=None):
        """
        Creează bonuri de producție în batch (tab-uri paralele)
        
        Args:
            batch_list (list): Listă de dict-uri {'sku': '...', 'cantitate': ...}
            
        Returns:
            list: Listă de rezultate [{'sku': '...', 'success': True/False, 'message': '...'}]
        """
        results = []
        tabs = []
        main_window = self.driver.current_window_handle
        
        # 0. Verificare Login (PRE-CHECK)
        # Verificăm login-ul pe fereastra principală înainte de a deschide tab-uri
        url_prod = "https://www.oblio.eu/stock/production/"
        self._log(f"Verificare login pe main window... Navigare la {url_prod}", 'info')
        self.driver.get(url_prod)
        
        # Așteaptă să se stabilizeze URL-ul (redirect la login sau load la production)
        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: "login" in d.current_url.lower() or "production" in d.current_url.lower()
            )
        except:
            pass # Continuăm verificarea
            
        time.sleep(1) # Extra safety
        
        if "login" in self.driver.current_url.lower():
            self._log("🔐 Login necesar înainte de batch...", 'warning')
            if oblio_cookies:
                self.load_cookies_from_json(oblio_cookies)
                self.driver.get(url_prod)
            elif oblio_email and oblio_password:
                self.login_to_oblio(oblio_email, oblio_password)
                self.driver.get(url_prod)
            elif self.input_callback:
                self.interactive_login()
                self.driver.get(url_prod)
            else:
                self.wait_for_manual_login()
                self.driver.get(url_prod)
                
        # Verificăm din nou dacă suntem logați
        # Așteptăm explicit elementul #pp_name care confirmă că suntem pe pagina de producție
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "pp_name"))
            )
            self._log("✅ Login confirmat. Începem procesarea batch...", 'success')
        except TimeoutException:
             self._log("❌ Login eșuat sau pagina nu s-a încărcat! Nu pot începe batch-ul.", 'error')
             # Captură screenshot pentru login eșuat
             self.capture_error_screenshot("batch", "login_failed")
             return [{'sku': b.get('sku'), 'success': False, 'message': 'Login failed - Page not loaded'} for b in batch_list]

        self._log(f"🚀 START BATCH: {len(batch_list)} bonuri în paralel...", 'info')
        
        # 1. Deschide tab-uri și navighează (PRE-LOAD)
        for i, item in enumerate(batch_list):
            sku = item.get('sku')
            qty = item.get('cantitate', 1)
            nume = item.get('nume', f"Produs {sku}")
            order_ids = item.get('order_ids', [])
            order_numbers = item.get('order_numbers', [])

            self._log(f"🌐 [Tab {i+1}] Deschidere tab pentru {sku}...", 'info')

            # Deschide tab nou
            self.driver.execute_script("window.open('about:blank', '_blank');")

            # Switch la noul tab (ultimul deschis)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            tab_handle = self.driver.current_window_handle

            # Navighează la producție
            self.driver.get(url_prod)

            tabs.append({
                'handle': tab_handle,
                'sku': sku,
                'qty': qty,
                'nume': nume,
                'order_ids': order_ids,
                'order_numbers': order_numbers,
                'index': i
            })

        # 2. Completează formularele (FILL)
        self._log("📝 [BATCH] Completare formulare...", 'info')
        for tab in tabs:
            try:
                self.driver.switch_to.window(tab['handle'])
                sku = tab['sku']
                qty = tab['qty']
                
                self._log(f"📝 [Tab {tab['index']+1}] Completare {sku}...", 'info')
                
                # Verifică dacă suntem pe pagina corectă
                if "production" not in self.driver.current_url:
                    self.driver.get("https://www.oblio.eu/stock/production/")
                
                # --- LOGICA DE COMPLETARE (Copiată și adaptată din create_production_voucher) ---
                # SKU
                pp_name_input = self.wait_for_element(By.ID, "pp_name", timeout=10)
                if not pp_name_input:
                    raise Exception("Input SKU negăsit")
                    
                pp_name_input.clear()
                self.type_slowly(pp_name_input, sku, delay=0.01)
                pp_name_input.send_keys(Keys.SPACE)
                pp_name_input.send_keys(Keys.BACKSPACE)
                
                # Autocomplete
                try:
                    autocomplete_items = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-menu-item"))
                    )
                    if len(autocomplete_items) > 0:
                        first_item = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable(autocomplete_items[0])
                        )
                        first_item.click()
                    else:
                        pp_name_input.send_keys(Keys.ENTER)
                except:
                    pp_name_input.send_keys(Keys.ENTER)
                
                # Cantitate
                pp_quantity_input = self.wait_for_element(By.ID, "pp_quantity", timeout=5)
                if pp_quantity_input:
                    pp_quantity_input.click()
                    pp_quantity_input.send_keys(Keys.CONTROL + "a")
                    pp_quantity_input.send_keys(Keys.DELETE)
                    pp_quantity_input.send_keys(str(qty))
                
                # --- VERIFICARE STOC (BATCH) ---
                time.sleep(1.0) # Așteaptă calculare rețetă
                try:
                    # Caută input-ul de cantitate consumată (ap_1_quantity2)
                    consumed_qty_input = self.wait_for_element(By.ID, "ap_1_quantity2", timeout=2)
                    
                    if consumed_qty_input:
                        consumed_val = float(consumed_qty_input.get_attribute('value') or 0)
                        
                        # Caută span-ul cu stocul (ap_1_name_note)
                        stock_span = self.driver.find_element(By.ID, "ap_1_name_note")
                        stock_text = stock_span.text # Ex: "Stoc: 0.02 buc"
                        
                        # Parsează stocul
                        import re
                        match_stock = re.search(r'Stoc:\s*([\d\.]+)', stock_text)
                        if match_stock:
                            stock_val = float(match_stock.group(1))
                            
                            if consumed_val > stock_val:
                                self._log(f"⚠️ [Tab {tab['index']+1}] STOC INSUFICIENT pentru {sku}! Necesar: {consumed_val}, Disponibil: {stock_val}", 'warning')
                                # Captură screenshot pentru stoc insuficient
                                self.capture_error_screenshot(sku, "stoc_insuficient")
                                tab['status'] = 'skipped'
                                tab['error'] = f"Stoc insuficient (Necesar: {consumed_val}, Disponibil: {stock_val})"
                                continue # Skip la următorul tab
                except Exception as e:
                    self._log(f"⚠️ [Tab {tab['index']+1}] Eroare verificare stoc: {e}", 'warning')
                # --- END VERIFICARE STOC ---
                
                tab['status'] = 'filled'
                
            except Exception as e:
                self._log(f"❌ [Tab {tab['index']+1}] Eroare la completare: {e}", 'error')
                # Captură screenshot pentru eroare completare
                self.capture_error_screenshot(tab.get('sku', 'unknown'), "completare_error")
                tab['status'] = 'error'
                tab['error'] = str(e)

        # 3. Salvare și Finalizare (SUBMIT)
        self._log("💾 [BATCH] Salvare și finalizare...", 'info')
        for tab in tabs:
            # Dacă statusul nu e 'filled', înseamnă că a fost eroare sau skip (stoc insuficient)
            if tab.get('status') != 'filled':
                msg = tab.get('error', 'Unknown error')
                results.append({'sku': tab['sku'], 'success': False, 'message': msg})
                
                # Închidem tab-ul dacă există
                try:
                    self.driver.switch_to.window(tab['handle'])
                    self.driver.close()
                except: pass
                continue
                
            try:
                self.driver.switch_to.window(tab['handle'])
                sku = tab['sku']
                self._log(f"💾 [Tab {tab['index']+1}] Salvare {sku}...", 'info')
                
                # Click Salvare
                save_button = self.wait_for_clickable(By.ID, "invoice_preview_btn", timeout=5)
                if not save_button:
                    # Fallback selectors
                    save_button = self.driver.find_element(By.CSS_SELECTOR, ".btn-submit")
                
                # Click JS
                self.driver.execute_script("arguments[0].click();", save_button)
                
                # Așteaptă redirect (mai mult timp pentru siguranță)
                try:
                    WebDriverWait(self.driver, 10).until(EC.url_contains("/preview_production/"))
                except TimeoutException:
                    self._log(f"⚠️ Timeout redirect după salvare {sku}. Verific erori...", 'warning')

                # Verifică redirect
                current_url = self.driver.current_url
                if "/stock/preview_production/" in current_url:
                    # Extrage ID-ul din URL pentru a construi selectori mai preciși
                    import re
                    match = re.search(r'/preview_production/(\d+)', current_url)
                    prod_id = match.group(1) if match else ""
                    
                    # Lansează
                    launch_btn = None
                    launch_selectors = [
                        (By.CSS_SELECTOR, "a.issue-btn"),
                        (By.XPATH, "//a[contains(text(), 'Lanseaza in Productie')]"),
                        (By.CSS_SELECTOR, f"a[href*='production_save/{prod_id}']")
                    ]
                    
                    for by, sel in launch_selectors:
                        try:
                            launch_btn = self.wait_for_clickable(by, sel, timeout=5)
                            if launch_btn: break
                        except: continue

                    if launch_btn:
                        # Folosește safe_click pentru a evita interceptarea de overlay-uri
                        if not self.safe_click(launch_btn, retries=3, wait_after=1.0):
                            raise Exception("Nu s-a putut face click pe butonul Lansare (overlay intercept)")

                        # Confirmă Popup
                        ok_btn = self.wait_for_clickable(By.CSS_SELECTOR, ".ok-message-modal", timeout=3)
                        if ok_btn:
                            self.safe_click(ok_btn, retries=2, wait_after=1.0)

                        # Finalizează
                        finalize_btn = None
                        finalize_selectors = [
                            (By.XPATH, "//a[contains(text(), 'Finalizeaza Productia')]"),
                            (By.CSS_SELECTOR, f"a[href*='production_complete/{prod_id}']")
                        ]

                        for by, sel in finalize_selectors:
                            try:
                                finalize_btn = self.wait_for_clickable(by, sel, timeout=5)
                                if finalize_btn: break
                            except: continue

                        if finalize_btn:
                            if not self.safe_click(finalize_btn, retries=3, wait_after=2.0):
                                raise Exception("Nu s-a putut face click pe butonul Finalizare (overlay intercept)")

                            results.append({'sku': sku, 'success': True, 'message': 'Bon creat cu succes'})
                            self.stats['success'] += 1

                            # Salvare în DB - pentru FIECARE comandă din order_numbers
                            try:
                                nume = tab.get('nume', f"Produs {sku}")
                                order_ids = tab.get('order_ids', [])
                                order_numbers = tab.get('order_numbers', [])

                                if order_numbers:
                                    # Salvăm câte o înregistrare pentru fiecare comandă
                                    for idx, order_num in enumerate(order_numbers):
                                        order_id = order_ids[idx] if idx < len(order_ids) else None
                                        adauga_bon(sku, nume, 1, order_id, order_num)
                                        self._log(f"💾 Salvat în DB: {sku} comanda #{order_num}", 'info')
                                else:
                                    # Fallback fără order tracking
                                    adauga_bon(sku, nume, qty)
                                    self._log(f"💾 Salvat în DB: {sku} (fără order tracking)", 'info')
                            except Exception as e:
                                self._log(f"⚠️ Eroare salvare DB: {e}", 'warning')
                        else:
                            raise Exception("Buton Finalizare negăsit")
                    else:
                        raise Exception("Buton Lansare negăsit")
                else:
                    # Fallback: Verifică dacă a rămas pe pagină cu eroare
                    try:
                        err = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger")
                        raise Exception(f"Eroare Oblio: {err.text}")
                    except:
                        raise Exception(f"Nu s-a făcut redirect la preview. URL curent: {current_url}")
                    
            except Exception as e:
                error_msg = str(e)
                self._log(f"❌ [Tab {tab['index']+1}] Eroare la salvare: {error_msg}", 'error')

                # Captură screenshot pentru eroare salvare/redirect
                error_type = "redirect_fail" if "redirect" in error_msg.lower() else "salvare_error"
                if "click" in error_msg.lower() or "intercept" in error_msg.lower():
                    error_type = "click_intercepted"
                self.capture_error_screenshot(tab['sku'], error_type)

                results.append({'sku': tab['sku'], 'success': False, 'message': error_msg})
                self.stats['failed'] += 1
            finally:
                self.driver.close()

        # Revino la fereastra principală (dacă mai există, altfel switch la ultima rămasă)
        try:
            self.driver.switch_to.window(main_window)
        except:
            if len(self.driver.window_handles) > 0:
                self.driver.switch_to.window(self.driver.window_handles[0])

        return results

    def process_bonuri(self, bonuri, oblio_cookies=None, oblio_email=None, oblio_password=None):
        """
        Procesează o listă de bonuri

        Args:
            bonuri (list): Lista de dicționare cu 'sku' și 'cantitate'
            oblio_cookies (str/dict): Cookies Oblio pentru sesiune (PREFERAT)
            oblio_email (str): Email Oblio (fallback pentru autentificare)
            oblio_password (str): Parolă Oblio (fallback pentru autentificare)

        Returns:
            dict: Statistici procesare
        """
        self._log(f"🚀 START PROCESARE: {len(bonuri)} bonuri", 'info')
        self._log(f"{'='*60}", 'info')

        self.stats['total'] = len(bonuri)

        for i, bon in enumerate(bonuri, 1):
            # Verifică dacă s-a cerut oprirea
            self._check_stop()

            sku = bon.get('sku')
            cantitate = bon.get('cantitate', 1)

            self._log(f"📦 Bon {i}/{len(bonuri)}", 'info')

            success = self.create_production_voucher(sku, cantitate, oblio_cookies, oblio_email, oblio_password)

            if success:
                self._log(f"✅ Bon {i}/{len(bonuri)} - SUCCESS", 'success')
            else:
                self._log(f"❌ Bon {i}/{len(bonuri)} - FAILED", 'error')

            # Pauză între bonuri
            if i < len(bonuri):
                # self._log(f"⏳ Pauză 2 secunde înainte de următorul bon...", 'info')
                time.sleep(0.1) # Optimizat: pauză minimă

        # Raport final
        self._log(f"{'='*60}", 'info')
        self._log(f"📊 RAPORT FINAL", 'info')
        self._log(f"{'='*60}", 'info')
        self._log(f"Total bonuri: {self.stats['total']}", 'info')
        self._log(f"✅ Succese: {self.stats['success']}", 'success')
        self._log(f"❌ Eșecuri: {self.stats['failed']}", 'error' if self.stats['failed'] > 0 else 'info')

        if self.stats['failed'] > 0:
            self._log(f"❌ Bonuri eșuate:", 'error')
            for error in self.stats['errors']:
                self._log(f"  - SKU: {error['sku']}, Eroare: {error['error']}", 'error')

        self._log(f"{'='*60}", 'info')

        return self.stats

    def close(self):
        """Închide browser-ul"""
        if self.driver:
            logger.info("🚪 Închidere browser...")
            try:
                self.driver.quit()
                logger.info("✅ Browser închis")
            except:
                pass

    def get_todays_processed_texts(self):
        """
        Returnează o listă cu textul complet al rândurilor procesate astăzi.
        Navighează prin pagini până găsește o dată diferită de azi.
        """
        processed_texts = []
        try:
            self._log("🔍 Verificare istoric producție (pentru a evita duplicate)...", 'info')
            self.driver.get("https://www.oblio.eu/report/production")
            time.sleep(2)
            
            from datetime import datetime
            today = datetime.now().strftime("%d.%m.%Y")
            
            page = 1
            max_pages = 10 # Limită de siguranță pentru a nu bloca scriptul
            
            while page <= max_pages:
                # Așteaptă încărcarea tabelului
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#content-table tbody tr.table_row"))
                    )
                except:
                    self._log("ℹ️ Tabelul de raport pare gol sau nu s-a încărcat.", 'info')
                    break

                rows = self.driver.find_elements(By.CSS_SELECTOR, "#content-table tbody tr.table_row")
                if not rows:
                    break
                
                found_today = False
                stop_search = False
                
                self._log(f"📄 Pagina {page}: Analizez {len(rows)} rânduri...", 'info')

                for row in rows:
                    try:
                        text = row.text
                        # Verificăm data
                        if today in text:
                            processed_texts.append(text)
                            found_today = True
                        else:
                            # Dacă găsim o dată care NU e azi, verificăm dacă e mai veche
                            # Regex pentru dată DD.MM.YYYY
                            match_date = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
                            if match_date:
                                date_str = match_date.group(0)
                                if date_str != today:
                                    # Presupunem sortare descrescătoare, deci ne putem opri
                                    stop_search = True
                                    # break # Nu dăm break imediat, poate sunt amestecate? De obicei sunt sortate.
                    except:
                        continue
                
                if stop_search:
                    self._log("⏹️ Am ajuns la bonuri din zilele anterioare. Mă opresc.", 'info')
                    break
                    
                # Navigare pagina următoare
                try:
                    # Căutăm butonul Next activ
                    next_li = self.driver.find_element(By.CSS_SELECTOR, "ul.pagination li.next")
                    if "disabled" in next_li.get_attribute("class"):
                        break # Ultima pagină
                        
                    next_link = next_li.find_element(By.TAG_NAME, "a")
                    self.driver.execute_script("arguments[0].click();", next_link)
                    time.sleep(2)
                    page += 1
                except Exception as e:
                    # self._log(f"ℹ️ Nu mai există pagini următoare ({e})", 'info')
                    break
            
            self._log(f"✅ Găsite {len(processed_texts)} bonuri procesate astăzi.", 'info')
            return processed_texts
            
        except Exception as e:
            self._log(f"⚠️ Eroare la citirea istoricului: {e}", 'warning')
            return []

    def login_if_needed(self, email=None, password=None):
        """Asigură autentificarea în Oblio"""
        try:
            self.driver.get("https://www.oblio.eu/stock/production/")
            time.sleep(2)
            
            # Verifică dacă suntem pe pagina de login
            if "login" in self.driver.current_url.lower():
                self._log("🔐 Autentificare necesară pentru verificare...", 'info')
                
                if email and password:
                    # Verificăm dacă metoda login_to_oblio există (ar trebui)
                    if hasattr(self, 'login_to_oblio'):
                        self.login_to_oblio(email, password)
                    else:
                        # Fallback la interactive dacă nu avem metoda (dar ar trebui să fie)
                        self.interactive_login()
                elif self.input_callback:
                    self.interactive_login()
                else:
                    self._log("⚠️ Nu am credențiale pentru login automat!", 'warning')
                    return False
                    
            # Verificare finală
            if "login" not in self.driver.current_url.lower():
                return True
            return False
            
        except Exception as e:
            self._log(f"❌ Eroare la login check: {e}", 'error')
            return False

def main():
    """Funcție main pentru rulare standalone"""

    # Exemplu listă bonuri (în producție, acestea vor veni de la Flask)
    bonuri_test = [
        {'sku': '1567943248-3', 'cantitate': 1},
        {'sku': '5673194590-3', 'cantitate': 1},
        {'sku': '6291106063717-3', 'cantitate': 1},
        {'sku': '6291106063742-3', 'cantitate': 1}
    ]

    # Inițializare automation
    automation = OblioAutomation(
        use_existing_profile=True,  # Folosește profilul Chrome cu sesiune Oblio
        headless=False  # Rulează cu interfață grafică (pentru debugging)
    )

    try:
        # Setup driver
        if not automation.setup_driver():
            logger.error("❌ Nu s-a putut porni Chrome WebDriver!")
            return

        # Așteaptă utilizatorul să verifice că e logat în Oblio (dacă e nevoie)
        logger.info("\n⚠️ IMPORTANT: Verifică că ești logat în Oblio!")
        logger.info("Browser-ul Chrome s-a deschis. Dacă nu ești logat, loghează-te acum.")
        logger.info("Apasă ENTER pentru a continua automatizarea...")
        input()

        # Procesează bonurile
        stats = automation.process_bonuri(bonuri_test)

        logger.info("\n🎉 AUTOMATIZARE FINALIZATĂ!")
        logger.info(f"Succese: {stats['success']}/{stats['total']}")

    except KeyboardInterrupt:
        logger.info("\n⚠️ Automatizare oprită de utilizator")
    except Exception as e:
        logger.error(f"\n❌ Eroare critică: {e}")
    finally:
        # Închide browser
        automation.close()


if __name__ == "__main__":
    main()
