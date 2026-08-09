import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import csv
import urllib.parse
import time
import random
import webbrowser
import os
import sys
import platform
import shutil
import re
import subprocess
import socket
from datetime import datetime

# Certifique-se de instalar as bibliotecas:
# pip install playwright
# playwright install
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def human_delay(min_s=0.5, max_s=2.0):
    """Pausa aleatória simulando tempo de leitura/pensamento humano."""
    time.sleep(random.uniform(min_s, max_s))


def human_type(page, selector, text, min_delay=50, max_delay=180):
    """Digita texto caractere por caractere com velocidade humana irregular."""
    el = page.locator(selector)
    el.click()
    human_delay(0.3, 0.8)
    for char in text:
        el.press_sequentially(char, delay=random.randint(min_delay, max_delay))
        # Pequena chance de uma pausa maior (como se pensasse)
        if random.random() < 0.08:
            human_delay(0.3, 0.9)


def human_scroll(page, times=4):
    """Rola a página de forma irregular, como um humano lendo."""
    for i in range(times):
        scroll_amount = random.randint(250, 700)
        page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        human_delay(0.8, 2.5)
        # Às vezes rola um pouco pra cima (releitura)
        if random.random() < 0.2:
            page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
            human_delay(0.5, 1.2)


def human_mouse_move(page):
    """Move o mouse aleatoriamente pela página, simulando exploração visual."""
    vp = page.viewport_size
    if not vp:
        return
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, max(101, vp["width"] - 100))
        y = random.randint(100, max(101, vp["height"] - 200))
        page.mouse.move(x, y, steps=random.randint(5, 20))
        human_delay(0.2, 0.7)


def get_chrome_profile_path():
    """Detecta o caminho do perfil do Chrome/Chromium de acordo com o SO."""
    sistema = platform.system()
    home = os.path.expanduser("~")

    if sistema == "Windows":
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Chromium", "User Data"),
        ]
    elif sistema == "Darwin":  # macOS
        paths = [
            os.path.join(home, "Library", "Application Support", "Google", "Chrome"),
            os.path.join(home, "Library", "Application Support", "Chromium"),
        ]
    else:  # Linux
        paths = [
            os.path.join(home, ".config", "google-chrome"),
            os.path.join(home, ".config", "chromium"),
        ]

    for p in paths:
        if os.path.isdir(p):
            return p
    return None


def get_temp_profile_path():
    """Cria/usa uma cópia temporária do perfil do Chrome para não conflitar com o Chrome aberto, preservando logins."""
    # Diretório persistente local do projeto para salvar os logins
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chrome_profile_temp")
    os.makedirs(temp_dir, exist_ok=True)

    original = get_chrome_profile_path()
    if original and not os.path.exists(os.path.join(temp_dir, "Default")):
        # Copiar apenas os arquivos essenciais na primeira vez
        essential_files = ["Default", "Local State", "Profile 1"]
        for item in essential_files:
            src = os.path.join(original, item)
            dst = os.path.join(temp_dir, item)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                except Exception:
                    pass
    return temp_dir


class EcommerceScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pesquisa de Produtos Online")
        self.root.geometry("1000x700")
        self.root.minsize(800, 550)

        # Configuração de Estilo
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Variáveis
        self.is_running = False
        self.scraped_data = []

        self._build_ui()

    def _build_ui(self):
        # Header / Título
        header_frame = tk.Frame(self.root, bg="#1E1E2E")
        header_frame.pack(fill=tk.X, ipadx=15, ipady=15)

        title_lbl = tk.Label(
            header_frame,
            text="🔍 Pesquisa Inteligente de Produtos",
            font=("Segoe UI", 16, "bold"),
            fg="#F5E0DC",
            bg="#1E1E2E"
        )
        title_lbl.pack(anchor="w", padx=15)

        subtitle_lbl = tk.Label(
            header_frame,
            text="Simula navegação humana real para pesquisar produtos com segurança.",
            font=("Segoe UI", 9),
            fg="#CDD6F4",
            bg="#1E1E2E"
        )
        subtitle_lbl.pack(anchor="w", padx=15)

        # Configurações do Target / URL
        config_frame = ttk.LabelFrame(self.root, text=" Configurações de Pesquisa ", padding=12)
        config_frame.pack(fill=tk.X, padx=15, pady=10)

        # Campo Termo de Busca
        ttk.Label(config_frame, text="O que você procura?", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.search_entry = ttk.Entry(config_frame, font=("Segoe UI", 10))
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        self.search_entry.insert(0, "bicicleta")

        # Campo Padrão de URL
        ttk.Label(config_frame, text="Modelo de URL ({query} = busca):").grid(row=1, column=0, sticky="w", pady=5)
        self.url_pattern_entry = ttk.Entry(config_frame, font=("Segoe UI", 9))
        self.url_pattern_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        self.url_pattern_entry.insert(0, "https://www.google.com/search?q=site:tiktok.com/view/product+{query}")

        # Presets rápidos
        ttk.Label(config_frame, text="Atalhos:").grid(row=2, column=0, sticky="w", pady=5)
        preset_frame = ttk.Frame(config_frame)
        preset_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=5)

        ttk.Button(preset_frame, text="TikTok Shop", command=lambda: self._set_preset("https://www.google.com/search?q=site:tiktok.com/view/product+{query}")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Mercado Livre", command=lambda: self._set_preset("https://lista.mercadolivre.com.br/{query}")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Amazon Brasil", command=lambda: self._set_preset("https://www.amazon.com.br/s?k={query}")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Shopee", command=lambda: self._set_preset("https://shopee.com.br/search?keyword={query}")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Shein", command=lambda: self._set_preset("https://br.shein.com/pdsearch/{query}/")).pack(side=tk.LEFT, padx=2)

        # Opções
        options_frame = ttk.Frame(config_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)

        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Modo Invisível (Headless)", variable=self.headless_var).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(options_frame, text="Limite de itens:").pack(side=tk.LEFT)
        self.limit_spinbox = ttk.Spinbox(options_frame, from_=5, to=100, width=5)
        self.limit_spinbox.pack(side=tk.LEFT, padx=(5, 15))
        self.limit_spinbox.set(15)

        config_frame.columnconfigure(1, weight=1)

        # Botões de Ação
        btn_frame = ttk.Frame(self.root, padding=(15, 0))
        btn_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(btn_frame, text="🚀 Iniciar Pesquisa", command=self.start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(btn_frame, text="⏹️ Parar", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.login_btn = ttk.Button(btn_frame, text="🔑 Fazer Login no Navegador", command=self.open_login_browser)
        self.login_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.export_csv_btn = ttk.Button(btn_frame, text="💾 Exportar CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.export_json_btn = ttk.Button(btn_frame, text="💾 Exportar JSON", command=self.export_json, state=tk.DISABLED)
        self.export_json_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.dashboard_btn = ttk.Button(btn_frame, text="📊 Gerar Dashboard", command=self.export_dashboard, state=tk.DISABLED)
        self.dashboard_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Tabela de Resultados
        table_frame = ttk.LabelFrame(self.root, text=" Resultados Encontrados ", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        columns = ("pos", "title", "price", "link")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("pos", text="#")
        self.tree.heading("title", text="Título / Produto")
        self.tree.heading("price", text="Preço / Destaque")
        self.tree.heading("link", text="Link do Produto / Página")

        self.tree.column("pos", width=40, anchor="center")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("price", width=120, anchor="center")
        self.tree.column("link", width=350, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Barra de Status
        self.status_var = tk.StringVar(value="Pronto. Configure e clique em Iniciar.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w", padding=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def open_login_browser(self):
        """Abre o navegador visível (e independente) habilitando a porta de debug."""
        self.status_var.set("Abrindo navegador para login... Pode deixá-lo aberto.")
        
        def run_login():
            try:
                sistema = platform.system()
                profile_path = get_temp_profile_path()
                cmd = []
                # Flag para habilitar o controle do Playwright no navegador existente
                # Passamos o user-data-dir para forçar uma nova instância isolada que suporte a porta 9222
                flags = ["--remote-debugging-port=9222", f"--user-data-dir={profile_path}", "https://www.google.com"]
                
                if sistema == "Windows":
                    cmd = ["start", "chrome"] + flags
                    subprocess.run(" ".join(cmd), shell=True)
                elif sistema == "Darwin":
                    cmd = ["open", "-a", "Google Chrome", "--args"] + flags
                    subprocess.Popen(cmd)
                else: # Linux
                    # Tenta os executáveis comuns
                    chrome_bin = shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
                    if chrome_bin:
                        cmd = [chrome_bin] + flags
                        # stdout e stderr pra DEVNULL para não travar
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        messagebox.showerror("Erro", "Chrome/Chromium não encontrado no sistema.")
                        
                self.root.after(0, lambda: self.status_var.set("Navegador aberto. Faça o login e pode Iniciar a Pesquisa."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Erro ao abrir navegador: {e}"))
        
        threading.Thread(target=run_login, daemon=True).start()

    def _set_preset(self, url_pattern):
        self.url_pattern_entry.delete(0, tk.END)
        self.url_pattern_entry.insert(0, url_pattern)

    def start_scraping(self):
        if not PLAYWRIGHT_AVAILABLE:
            messagebox.showerror(
                "Biblioteca Faltando",
                "A biblioteca 'playwright' não está instalada.\n\n"
                "Instale rodando no terminal:\npip install playwright\nplaywright install"
            )
            return

        query = self.search_entry.get().strip()
        url_pattern = self.url_pattern_entry.get().strip()

        if not query:
            messagebox.showwarning("Aviso", "Por favor, digite o que você quer pesquisar.")
            return
        if "{query}" not in url_pattern:
            messagebox.showwarning("Aviso", "O modelo de URL precisa conter o marcador {query}.")
            return

        # Limpa dados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.scraped_data.clear()

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_csv_btn.config(state=tk.DISABLED)
        self.export_json_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._run_scraper, args=(query, url_pattern), daemon=True).start()

    def stop_scraping(self):
        self.is_running = False
        self.status_var.set("Interrupção solicitada pelo usuário...")

    def _run_scraper(self, query, url_pattern):
        encoded_query = urllib.parse.quote(query)
        target_url = url_pattern.replace("{query}", encoded_query)
        limit = int(self.limit_spinbox.get())
        headless = self.headless_var.get()

        self.status_var.set("Abrindo navegador como um usuário normal...")

        try:
            with sync_playwright() as p:
                # Verifica se a porta 9222 está aberta (navegador já aberto pelo botão de login)
                cdp_port_open = False
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(('127.0.0.1', 9222)) == 0:
                        cdp_port_open = True

                if cdp_port_open:
                    self.status_var.set("Conectando ao navegador já aberto...")
                    browser_or_context = p.chromium.connect_over_cdp("http://localhost:9222")
                    context = browser_or_context.contexts[0] if browser_or_context.contexts else browser_or_context
                    is_connected = True
                else:
                    is_connected = False
                    profile_path = get_temp_profile_path()
                    if profile_path:
                        self.status_var.set("Abrindo Chrome com seu perfil...")
                        context = p.chromium.launch_persistent_context(
                            profile_path,
                            channel="chrome",
                            headless=headless,
                            locale="pt-BR",
                            timezone_id="America/Sao_Paulo",
                            color_scheme="light",
                            args=[
                                "--disable-blink-features=AutomationControlled",
                                "--disable-infobars",
                            ],
                        )
                    else:
                        self.status_var.set("Perfil não encontrado, executando em modo limpo...")
                        context = p.chromium.launch_persistent_context(
                            "",
                            channel="chrome",
                            headless=headless,
                            locale="pt-BR",
                            timezone_id="America/Sao_Paulo",
                            color_scheme="light",
                        )

                if is_connected:
                    # Se conectou a um Chrome aberto, abre apenas uma nova guia
                    page = context.new_page()
                else:
                    page = context.pages[0] if context.pages else context.new_page()

                # ── FASE 1: Abrir página inicial (como um humano abrindo o navegador) ──
                self.status_var.set("Navegando até a página de busca...")

                # Se for Google, vai primeiro ao google.com e depois pesquisa
                if "google.com" in target_url:
                    page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
                    human_delay(1.5, 3.5)

                    # Aceitar cookies se aparecer
                    try:
                        accept_btn = page.locator("button:has-text('Aceitar'), button:has-text('Accept'), button#L2AGLb")
                        if accept_btn.count() > 0:
                            human_delay(0.8, 1.5)
                            accept_btn.first.click()
                            human_delay(1.0, 2.0)
                    except Exception:
                        pass

                    # Mover mouse pela página (exploração visual)
                    human_mouse_move(page)
                    human_delay(0.5, 1.5)

                    # Digitar a busca caractere por caractere
                    self.status_var.set(f"Digitando pesquisa: {query}...")
                    search_text = target_url.split("q=")[1] if "q=" in target_url else query
                    search_text = urllib.parse.unquote(search_text)
                    human_type(page, 'textarea[name="q"], input[name="q"]', search_text)
                    human_delay(0.5, 1.5)

                    # Pressionar Enter (como um humano)
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("domcontentloaded")
                    human_delay(2.0, 4.0)
                else:
                    # Para outros sites, navega direto mas com delay inicial
                    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    human_delay(2.0, 4.0)

                    # Aceitar cookies genéricos
                    try:
                        cookie_btns = page.locator("button:has-text('Aceitar'), button:has-text('Accept'), button:has-text('OK'), button:has-text('Concordo')")
                        if cookie_btns.count() > 0:
                            human_delay(1.0, 2.0)
                            cookie_btns.first.click()
                            human_delay(0.8, 1.5)
                    except Exception:
                        pass

                # ── FASE 2: Explorar a página como humano ──
                self.status_var.set("Lendo a página de resultados...")
                human_mouse_move(page)
                human_delay(1.0, 2.5)

                # Rolagem natural para carregar conteúdo
                human_scroll(page, times=random.randint(3, 6))
                # Volta ao topo
                page.evaluate("window.scrollTo(0, 0)")
                human_delay(1.0, 2.0)

                self.status_var.set("Coletando informações dos produtos...")

                results = []

                # ── FASE 3: Extração adaptativa com delays humanos ──
                if "google.com" in target_url:
                    elements = page.query_selector_all("div.g, div[data-header-feature]")
                    for elem in elements:
                        if len(results) >= limit or not self.is_running:
                            break

                        title_el = elem.query_selector("h3")
                        link_el = elem.query_selector("a")
                        snippet_el = elem.query_selector("div.VwiC3b, div.mB123b")

                        if title_el and link_el:
                            title = title_el.inner_text().strip()
                            link = link_el.get_attribute("href")
                            price = snippet_el.inner_text().strip()[:40] if snippet_el else "Consulte no site"

                            if link and link.startswith("http"):
                                results.append({"title": title, "price": price, "link": link})
                                # Pausa entre leituras de cada resultado
                                human_delay(0.2, 0.6)

                elif "mercadolivre.com" in target_url:
                    items = page.query_selector_all("li.ui-search-layout__item")
                    for elem in items:
                        if len(results) >= limit or not self.is_running:
                            break

                        # Título: h3.poly-component__title-wrapper > a.poly-component__title
                        title_el = elem.query_selector("a.poly-component__title")
                        if not title_el:
                            title_el = elem.query_selector("h2.ui-search-item__title")

                        # Preço: div.poly-price__current span.andes-money-amount__fraction
                        price_el = elem.query_selector("div.poly-price__current span.andes-money-amount__fraction")
                        if not price_el:
                            price_el = elem.query_selector("span.andes-money-amount__fraction")

                        # Link: mesmo <a> do título
                        link = title_el.get_attribute("href") if title_el else ""
                        title = title_el.inner_text().strip() if title_el else "Sem título"
                        price = f"R$ {price_el.inner_text().strip()}" if price_el else "N/A"

                        if link:
                            results.append({"title": title, "price": price, "link": link})
                            human_delay(0.2, 0.5)

                elif "shein.com" in target_url:
                    # Extrator específico da Shein
                    # Esperar mais tempo pois a Shein carrega via JS
                    human_delay(2.0, 4.0)
                    human_scroll(page, times=random.randint(4, 7))
                    page.evaluate("window.scrollTo(0, 0)")
                    human_delay(1.0, 2.0)

                    items = page.query_selector_all("div.product-card__goods-title-container")
                    for elem in items:
                        if len(results) >= limit or not self.is_running:
                            break

                        # Título: a.goods-title-link[aria-label]
                        link_el = elem.query_selector("a.goods-title-link")
                        if not link_el:
                            continue

                        title = link_el.get_attribute("aria-label") or link_el.inner_text().strip()
                        href = link_el.get_attribute("href") or ""

                        if href and href.startswith("/"):
                            href = "https://br.shein.com" + href

                        # Preço: buscar no card pai
                        card = elem.evaluate_handle("el => el.closest('.product-list__item') || el.parentElement.parentElement")
                        price = "N/A"
                        try:
                            price_el = card.query_selector("p.product-item__camecase-wrap span")
                            if price_el:
                                price = price_el.inner_text().strip()
                            else:
                                # Fallback: data-price do link
                                data_price = link_el.get_attribute("data-price")
                                if data_price:
                                    price = f"R${data_price}"
                        except Exception:
                            data_price = link_el.get_attribute("data-price")
                            if data_price:
                                price = f"R${data_price}"

                        if href and title:
                            # Limpar título (remover textos de desconto que ficam misturados)
                            title = title.replace("\n", " ").strip()
                            results.append({"title": title, "price": price, "link": href})
                            human_delay(0.2, 0.5)

                elif "amazon.com" in target_url:
                    # Extrator específico da Amazon usando seletores reais
                    items = page.query_selector_all("div.s-result-item[data-component-type='s-search-result']")
                    for elem in items:
                        if len(results) >= limit or not self.is_running:
                            break

                        # Título: div[data-cy="title-recipe"] > a > h2 > span
                        title_container = elem.query_selector('div[data-cy="title-recipe"]')
                        if not title_container:
                            continue

                        title_el = title_container.query_selector("h2 span")
                        link_el = title_container.query_selector("a.a-link-normal")

                        title = title_el.inner_text().strip() if title_el else "Sem título"
                        link = link_el.get_attribute("href") if link_el else ""

                        # Montar link completo
                        if link and link.startswith("/"):
                            link = "https://www.amazon.com.br" + link

                        # Preço: span.a-price[data-a-size="xl"] > span.a-offscreen
                        price_el = elem.query_selector('span.a-price[data-a-size="xl"] span.a-offscreen')
                        if price_el:
                            price = price_el.inner_text().strip()
                        else:
                            # Fallback: qualquer span.a-price span.a-offscreen
                            price_fallback = elem.query_selector("span.a-price span.a-offscreen")
                            price = price_fallback.inner_text().strip() if price_fallback else "N/A"

                        if link:
                            results.append({"title": title, "price": price, "link": link})
                            human_delay(0.2, 0.5)

                elif "shopee" in target_url:
                    # Extrator específico da Shopee
                    # Shopee é SPA pesado, precisa esperar bastante
                    human_delay(3.0, 5.0)
                    human_scroll(page, times=random.randint(4, 8))
                    page.evaluate("window.scrollTo(0, 0)")
                    human_delay(1.0, 2.0)

                    # Cada produto é um card com link <a> que contém título e preço
                    cards = page.query_selector_all("a[data-sqe='link']")
                    if not cards or len(cards) == 0:
                        # Fallback: tentar pegar pelo container de lista
                        cards = page.query_selector_all("li.shopee-search-item-result__item a")

                    for card in cards:
                        if len(results) >= limit or not self.is_running:
                            break

                        # Título: div com line-clamp-2
                        title_el = card.query_selector("div.line-clamp-2")
                        if not title_el:
                            title_el = card.query_selector("div.whitespace-normal")
                        if not title_el:
                            continue

                        title = title_el.inner_text().strip()

                        # Preço promocional: span.text-base dentro do container text-shopee-primary
                        price = "N/A"
                        price_container = card.query_selector("div.text-shopee-primary")
                        if price_container:
                            price_val = price_container.query_selector("span.text-base\\/5")
                            if price_val:
                                price = f"R$ {price_val.inner_text().strip()}"
                            else:
                                # Fallback: pegar todo texto do container de preço
                                all_spans = price_container.query_selector_all("span.truncate")
                                if all_spans:
                                    price = price_container.inner_text().strip().split("\n")[0]

                        # Link
                        href = card.get_attribute("href") or ""
                        if href and href.startswith("/"):
                            href = "https://shopee.com.br" + href

                        if href and title:
                            results.append({"title": title, "price": price, "link": href})
                            human_delay(0.2, 0.5)

                else:
                    # Extrator genérico
                    links = page.query_selector_all("a")
                    seen_links = set()
                    for l in links:
                        if len(results) >= limit or not self.is_running:
                            break
                        text = l.inner_text().strip()
                        href = l.get_attribute("href")

                        if href and text and len(text) > 8 and href not in seen_links:
                            if href.startswith("/"):
                                base_domain = "/".join(target_url.split("/")[:3])
                                href = base_domain + href
                            seen_links.add(href)
                            results.append({"title": text.replace("\n", " "), "price": "Ver no link", "link": href})
                            human_delay(0.1, 0.3)

                self.scraped_data = results
                self.root.after(0, self._populate_table)

                # ── FASE 4: Fechar como humano ──
                self.status_var.set("Finalizando navegação...")
                human_delay(1.0, 3.0)
                human_mouse_move(page)
                human_delay(0.5, 1.0)

                if is_connected:
                    page.close()
                    try:
                        browser_or_context.close()
                    except Exception:
                        pass
                else:
                    context.close()

        except Exception as e:
            self.status_var.set(f"Erro ao extrair: {str(e)}")
            messagebox.showerror("Erro na Execução", f"Ocorreu um erro durante a pesquisa:\n{str(e)}")
        finally:
            self.root.after(0, self._finish_scraping)

    def _populate_table(self):
        for idx, item in enumerate(self.scraped_data, 1):
            self.tree.insert("", tk.END, values=(idx, item["title"], item["price"], item["link"]))

    def _finish_scraping(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        if self.scraped_data:
            self.export_csv_btn.config(state=tk.NORMAL)
            self.export_json_btn.config(state=tk.NORMAL)
            self.dashboard_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Concluído! {len(self.scraped_data)} itens encontrados.")
        else:
            self.status_var.set("Pesquisa finalizada, mas nenhum item foi retornado.")

    def export_csv(self):
        if not self.scraped_data:
            return
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV File", "*.csv")])
        if filename:
            try:
                with open(filename, mode="w", newline="", encoding="utf-8-sig") as file:
                    writer = csv.DictWriter(file, fieldnames=["title", "price", "link"])
                    writer.writeheader()
                    writer.writerows(self.scraped_data)
                messagebox.showinfo("Sucesso", f"Dados salvos com sucesso em:\n{filename}")
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", str(e))

    def export_json(self):
        if not self.scraped_data:
            return
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON File", "*.json")])
        if filename:
            try:
                with open(filename, mode="w", encoding="utf-8") as file:
                    json.dump(self.scraped_data, file, ensure_ascii=False, indent=4)
                messagebox.showinfo("Sucesso", f"Dados salvos com sucesso em:\n{filename}")
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", str(e))

    def _parse_price(self, price_str):
        """Extrai valor numérico de uma string de preço."""
        if not price_str or price_str in ["N/A", "Consulte no site", "Ver no link"]:
            return None
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        cleaned = cleaned.replace('.', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return None

    def export_dashboard(self):
        if not self.scraped_data:
            return

        query = self.search_entry.get().strip() or "Pesquisa"
        now = datetime.now().strftime("%d/%m/%Y às %H:%M")

        prices = []
        for item in self.scraped_data:
            p = self._parse_price(item.get("price", ""))
            if p and p > 0:
                prices.append(p)

        total_items = len(self.scraped_data)
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        table_rows = ""
        chart_labels = []
        chart_values = []
        for idx, item in enumerate(self.scraped_data, 1):
            title = item.get("title", "Sem título")[:80]
            price = item.get("price", "N/A")
            link = item.get("link", "#")
            p_val = self._parse_price(price)
            table_rows += f'''
            <tr>
                <td>{idx}</td>
                <td><a href="{link}" target="_blank">{title}</a></td>
                <td class="price">{price}</td>
            </tr>'''
            if p_val and len(chart_labels) < 20:
                short = title[:30] + "..." if len(title) > 30 else title
                chart_labels.append(short)
                chart_values.append(p_val)

        labels_js = json.dumps(chart_labels, ensure_ascii=False)
        values_js = json.dumps(chart_values)

        html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - {query}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter',sans-serif; background:#0f0f1a; color:#e0e0e0; min-height:100vh; }}
.header {{ background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460); padding:40px 50px; border-bottom:1px solid rgba(255,255,255,0.05); }}
.header h1 {{ font-size:28px; font-weight:700; background:linear-gradient(90deg,#e2e8f0,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:6px; }}
.header p {{ color:#64748b; font-size:14px; }}
.container {{ max-width:1400px; margin:0 auto; padding:30px 50px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:20px; margin-bottom:35px; }}
.stat-card {{ background:linear-gradient(145deg,#1a1a2e,#1e1e35); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:28px; transition:transform .2s,box-shadow .2s; }}
.stat-card:hover {{ transform:translateY(-4px); box-shadow:0 8px 30px rgba(0,0,0,0.3); }}
.stat-card .label {{ font-size:12px; text-transform:uppercase; letter-spacing:1.5px; color:#64748b; margin-bottom:10px; }}
.stat-card .value {{ font-size:32px; font-weight:700; }}
.stat-card:nth-child(1) .value {{ color:#60a5fa; }}
.stat-card:nth-child(2) .value {{ color:#34d399; }}
.stat-card:nth-child(3) .value {{ color:#fbbf24; }}
.stat-card:nth-child(4) .value {{ color:#f472b6; }}
.section {{ background:linear-gradient(145deg,#1a1a2e,#1e1e35); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:30px; margin-bottom:35px; }}
.section h2 {{ font-size:18px; font-weight:600; color:#cbd5e1; margin-bottom:20px; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; padding:14px 16px; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#64748b; border-bottom:1px solid rgba(255,255,255,0.08); }}
td {{ padding:14px 16px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:14px; }}
td a {{ color:#93c5fd; text-decoration:none; transition:color .2s; }}
td a:hover {{ color:#60a5fa; text-decoration:underline; }}
td.price {{ color:#34d399; font-weight:600; white-space:nowrap; }}
tr:hover {{ background:rgba(255,255,255,0.02); }}
.footer {{ text-align:center; padding:30px; color:#475569; font-size:12px; }}
</style>
</head>
<body>
<div class="header">
    <h1>📊 Dashboard: {query}</h1>
    <p>Gerado em {now} &mdash; {total_items} produtos encontrados</p>
</div>
<div class="container">
    <div class="stats-grid">
        <div class="stat-card"><div class="label">Total de Produtos</div><div class="value">{total_items}</div></div>
        <div class="stat-card"><div class="label">Preço Médio</div><div class="value">R$ {avg_price:,.2f}</div></div>
        <div class="stat-card"><div class="label">Menor Preço</div><div class="value">R$ {min_price:,.2f}</div></div>
        <div class="stat-card"><div class="label">Maior Preço</div><div class="value">R$ {max_price:,.2f}</div></div>
    </div>
    <div class="section">
        <h2>Comparativo de Preços</h2>
        <canvas id="priceChart" height="100"></canvas>
    </div>
    <div class="section">
        <h2>Todos os Produtos</h2>
        <table>
            <thead><tr><th>#</th><th>Produto</th><th>Preço</th></tr></thead>
            <tbody>{table_rows}
            </tbody>
        </table>
    </div>
</div>
<div class="footer">Pesquisa Inteligente de Produtos &mdash; Dashboard gerado automaticamente</div>
<script>
const ctx = document.getElementById('priceChart').getContext('2d');
new Chart(ctx, {{
    type:'bar',
    data:{{
        labels:{labels_js},
        datasets:[{{
            label:'Preço (R$)',
            data:{values_js},
            backgroundColor:'rgba(96,165,250,0.6)',
            borderColor:'rgba(96,165,250,1)',
            borderWidth:1,
            borderRadius:6,
            hoverBackgroundColor:'rgba(96,165,250,0.85)'
        }}]
    }},
    options:{{
        responsive:true,
        plugins:{{
            legend:{{display:false}},
            tooltip:{{
                backgroundColor:'#1e293b',
                callbacks:{{
                    label:function(c){{return 'R$ '+c.raw.toLocaleString('pt-BR',{{minimumFractionDigits:2}});}}
                }}
            }}
        }},
        scales:{{
            y:{{beginAtZero:true, ticks:{{color:'#64748b',callback:function(v){{return 'R$ '+v.toLocaleString('pt-BR');}}}}, grid:{{color:'rgba(255,255,255,0.04)'}}}},
            x:{{ticks:{{color:'#64748b',maxRotation:45}}, grid:{{display:false}}}}
        }}
    }}
}});
</script>
</body>
</html>'''

        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML File", "*.html")],
            initialfile=f"dashboard_{query.replace(' ', '_')}.html"
        )
        if filename:
            try:
                with open(filename, mode="w", encoding="utf-8") as f:
                    f.write(html)
                webbrowser.open("file://" + os.path.abspath(filename))
                messagebox.showinfo("Sucesso", f"Dashboard salvo e aberto!\n{filename}")
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = EcommerceScraperApp(root)
    root.mainloop()