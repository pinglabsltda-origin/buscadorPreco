@echo off
echo ============================================
echo  Compilando Pesquisa de Produtos para Windows
echo ============================================
echo.

echo [1/4] Criando ambiente virtual...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Instalando dependencias...
pip install -r requirements.txt

echo [3/4] Instalando navegador do Playwright...
playwright install chromium

echo [4/4] Gerando executavel .exe ...
pyinstaller --noconsole --onefile --name "PesquisaProdutos" --icon=NONE app.py

echo.
echo ============================================
echo  PRONTO! O executavel esta em: dist\PesquisaProdutos.exe
echo ============================================
pause
