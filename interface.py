import customtkinter as ctk
import threading
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def mostrar_loading(funcao_background):
    """
    A função_background agora deve aceitar um argumento de callback
    para atualizar a porcentagem.
    """
    root = ctk.CTk()
    
    path_icone = resource_path("merco.ico")
    try:
        root.after(200, lambda: root.iconbitmap(path_icone))
    except:
        pass 
    
    root.title("Mercosistem - Backup")
    root.geometry("400x180")
    root.resizable(False, False)

    # Variável que controla o texto da porcentagem na tela
    texto_porcentagem = ctk.StringVar(value="Preparando... 0%")

    def fechar_janela():
        # Apenas esconde a janela, o processo continua no fundo
        root.withdraw() 

    root.protocol("WM_DELETE_WINDOW", fechar_janela)

    # Label de Título
    label = ctk.CTkLabel(
        root, 
        text="Backup Mercosistem em andamento", 
        font=("Roboto", 15, "bold")
    )
    label.pack(pady=(20, 5))

    # --- BARRA DE PROGRESSO DETERMINADA ---
    # mode="determinate" permite que a gente defina o valor exato
    barra = ctk.CTkProgressBar(root, orientation="horizontal", mode="determinate", width=320)
    barra.set(0) # Inicia em 0%
    barra.pack(pady=10)

    # Label que mostra a porcentagem (ex: 45%)
    label_pct = ctk.CTkLabel(
        root, 
        textvariable=texto_porcentagem, 
        font=("Roboto", 12)
    )
    label_pct.pack()

    # =================================================================
    # FUNÇÃO DE ATUALIZAÇÃO (CALLBACK)
    # =================================================================
    def atualizar_progresso(valor_decimal):
        """
        valor_decimal: float entre 0.0 e 1.0
        """
        # Converte 0.1 para "10%"
        pct = int(valor_decimal * 100)
        
        # O .after(0, ...) garante que a interface atualize de forma segura
        root.after(0, lambda: barra.set(valor_decimal))
        root.after(0, lambda: texto_porcentagem.set(f"Progresso: {pct}%"))

    # =================================================================
    # GERENCIAMENTO DE THREADS
    # =================================================================
    
    # Passamos a função 'atualizar_progresso' para dentro do seu rodar_backup
    t = threading.Thread(target=funcao_background, args=(atualizar_progresso,))
    t.daemon = False 
    t.start()

    def checar_thread():
        if t.is_alive():
            root.after(500, checar_thread)
        else:
            root.quit() 
            root.destroy()

    checar_thread()
    root.mainloop()